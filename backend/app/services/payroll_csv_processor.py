"""
Serviço REFATORADO para processar CSVs de folha de pagamento
VERSÃO SIMPLIFICADA - apenas colunas essenciais conforme mapeamento RH
"""
import os
import time
import calendar
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.employee import Employee
from app.models.payroll import PayrollPeriod, PayrollData
from app.models.user import User
from app.utils.parsers import (
    parse_br_number,
    parse_br_date,
    detect_payroll_type,
    extract_employee_code,
    normalize_cpf,
    normalize_phone,
    CSV_COLUMN_MAPPING
)


class PayrollCSVProcessor:
    """
    Processa arquivos CSV de folha de pagamento
    
    VERSÃO SIMPLIFICADA - captura APENAS as colunas especificadas:
    - Salário Mensal
    - Total Proventos / Descontos / Líquido
    - Gratificações, Periculosidade, Insalubridade
    - Horas Extras (DSR, HE50%, HE100%, Adicional Noturno)
    - Encargos (INSS, IRRF, FGTS)
    - Atestados e Faltas
    - Empréstimos e Adiantamentos
    """
    
    def __init__(self, db: Session, user_id: Optional[int] = None):
        self.db = db
        self.user_id = user_id
        self.errors = []
        self.warnings = []
        self.stats = {
            'total_rows': 0,
            'processed': 0,
            'skipped': 0,
            'errors': 0,
            'new_employees': 0,
            'updated_payrolls': 0
        }

    def _get_number(self, row: pd.Series, keys: List[str], default: float = 0.0) -> float:
        """Tenta extrair um número do CSV usando múltiplas variações de chave."""
        for key in keys:
            if key in row and row[key] not in [None, '', 'nan'] and not pd.isna(row[key]):
                try:
                    return parse_br_number(row[key])
                except Exception:
                    continue
        return default
    
    def process_csv_file(
        self, 
        file_path: str, 
        division_code: str = '0060',
        auto_create_employees: bool = False
    ) -> Dict[str, Any]:
        """Processa arquivo CSV de folha de pagamento"""
        start_time = time.time()
        
        # Armazenar division_code como atributo da classe
        self.division = division_code
        
        try:
            # 1. Validar arquivo
            if not os.path.exists(file_path):
                return self._error_response(f"Arquivo não encontrado: {file_path}")
            
            # 2. Detectar tipo de arquivo
            filename = os.path.basename(file_path)
            file_info = detect_payroll_type(filename)
            
            if not file_info['matched']:
                return self._error_response(f"Tipo de arquivo não reconhecido: {filename}")
            
            print(f"📄 Processando {file_info['tipo']} - {file_info['mes']}/{file_info['ano']} (empresa {division_code})")
            
            # 3. Ler CSV
            df = self._read_csv(file_path)
            if df is None:
                return self._error_response("Erro ao ler arquivo CSV")
            
            self.stats['total_rows'] = len(df)
            print(f"📊 Total de linhas: {len(df)}")
            
            # 4. Criar/buscar período
            period = self._get_or_create_period(
                year=int(file_info['ano']),
                month=int(file_info['mes']),
                period_type=file_info['tipo']
            )
            
            if not period:
                return self._error_response("Erro ao criar período de folha")
            
            print(f"📅 Período: {period.period_name} (ID: {period.id})")
            
            # 5. Processar cada linha do CSV
            for idx, row in df.iterrows():
                try:
                    self._process_employee_payroll(
                        row=row,
                        period_id=period.id,
                        upload_filename=filename,
                        division_code=division_code,
                        auto_create_employees=auto_create_employees
                    )
                except Exception as e:
                    self.stats['errors'] += 1
                    self.errors.append({
                        'row': idx + 1,
                        'error': str(e)
                    })
                    print(f"❌ Erro na linha {idx + 1}: {e}")
            
            # 6. Commit se tudo ok
            try:
                self.db.commit()
                print(f"✅ Processamento concluído: {self.stats['processed']} registros")
                
                # 7. Invalidar cache de indicadores
                self._invalidate_indicators_cache()
                
                # 8. Log de processamento (com commit separado)
                self._create_processing_log(
                    period_id=period.id,
                    filename=filename,
                    file_path=file_path,
                    status='completed',
                    processing_time=time.time() - start_time
                )
                self.db.commit()  # Commit do log
                
                return {
                    'success': True,
                    'period_id': period.id,
                    'period_name': period.period_name,
                    'stats': self.stats,
                    'errors': self.errors,
                    'warnings': self.warnings
                }
                
            except Exception as e:
                self.db.rollback()
                raise e
                
        except Exception as e:
            self.db.rollback()
            print(f"❌ Erro crítico: {e}")
            
            # Tentar criar log de erro
            try:
                self._create_processing_log(
                    period_id=None,
                    filename=filename if 'filename' in locals() else os.path.basename(file_path),
                    file_path=file_path,
                    status='failed',
                    error_message=str(e),
                    processing_time=time.time() - start_time
                )
                self.db.commit()  # Commit do log de erro
            except Exception as log_error:
                print(f"⚠️ Erro ao criar log de erro: {log_error}")
            
            return self._error_response(f"Erro crítico: {str(e)}")
    
    def _read_csv(self, file_path: str) -> Optional[pd.DataFrame]:
        """Lê CSV com encoding correto"""
        encodings = ['latin-1', 'utf-8', 'cp1252']
        
        for encoding in encodings:
            try:
                df = pd.read_csv(
                    file_path,
                    delimiter=';',
                    encoding=encoding,
                    on_bad_lines='skip',
                    dtype=str
                )
                print(f"✅ CSV lido com encoding: {encoding}")
                return df
            except Exception as e:
                continue
        
        return None
    
    def _get_or_create_period(
        self, 
        year: int, 
        month: int, 
        period_type: str
    ) -> Optional[PayrollPeriod]:
        """Busca ou cria período de folha"""
        type_names = {
            'mensal': f'{self._get_month_name(month)} {year}',
            '13_adiantamento': f'13º Adiantamento - {self._get_month_name(month)[:3]}/{year}',
            '13_integral': f'13º Integral - {self._get_month_name(month)[:3]}/{year}',
            'complementar': f'Folha Complementar {month}/{year}',
            'adiantamento_salario': f'Adiantamento Salarial {month}/{year}'
        }
        
        period_name = type_names.get(period_type, f'Folha {month}/{year}')
        
        # Buscar existente considerando empresa também
        period = self.db.query(PayrollPeriod).filter(
            and_(
                PayrollPeriod.year == year,
                PayrollPeriod.month == month,
                PayrollPeriod.period_name == period_name,
                PayrollPeriod.company == self.division  # Filtrar por empresa
            )
        ).first()
        
        if period:
            print(f"✅ Período existente encontrado: {period_name} (empresa {self.division})")
            return period
        
        # Criar novo com empresa
        period = PayrollPeriod(
            year=year,
            month=month,
            period_name=period_name,
            company=self.division  # Salvar empresa no período
        )
        
        self.db.add(period)
        self.db.flush()
        print(f"✅ Novo período criado: {period_name} (empresa {self.division})")
        
        return period
    
    def _get_month_name(self, month: int) -> str:
        """Retorna nome do mês em português"""
        months = {
            1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
            5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
            9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
        }
        return months.get(month, f'Mês {month}')
    
    def _process_employee_payroll(
        self,
        row: pd.Series,
        period_id: int,
        upload_filename: str,
        division_code: str,
        auto_create_employees: bool = False
    ):
        """Processa linha do CSV e salva/atualiza PayrollData"""
        # 1. Extrair código do funcionário
        codigo_func = str(row.get('Código Funcionário', 
                        row.get('CODIGO_FUNC', 
                        row.get('COD_FUNC', 
                        row.get('Codigo Funcionario', '')))))
        if not codigo_func or str(codigo_func).strip() == '':
            raise ValueError("Código do funcionário não encontrado na linha")
        
        # 2. Gerar matrícula completa
        matricula = extract_employee_code(codigo_func, division_code)
        
        # 3. Buscar employee
        employee = self.db.query(Employee).filter(
            Employee.unique_id == matricula
        ).first()
        
        if not employee:
            if auto_create_employees:
                employee = self._create_employee_from_csv(row, matricula, division_code)
                self.stats['new_employees'] += 1
            else:
                self.warnings.append({
                    'matricula': matricula,
                    'message': f"Funcionário não encontrado (matrícula: {matricula})"
                })
                self.stats['skipped'] += 1
                return
        
        # 4. Construir JSONs SIMPLIFICADOS
        earnings_data = self._extract_earnings(row)
        deductions_data = self._extract_deductions(row)
        additional_data = self._extract_additional(row)
        
        # 5. Calcular totais
        gross_salary = self._get_number(row, [
            'TOTAL_PROVENTOS',
            'Total de Proventos',
            'Total Proventos'
        ], default=0.0)

        net_salary = self._get_number(row, [
            'LIQ_A_RECEBER',
            'Líquido de Cálculo',
            'Liquido de Cálculo',
            'Líquido'
        ], default=0.0)
        
        # 6. Verificar se já existe registro
        existing = self.db.query(PayrollData).filter(
            and_(
                PayrollData.employee_id == employee.id,
                PayrollData.period_id == period_id
            )
        ).first()
        
        if existing:
            # Atualizar
            existing.gross_salary = gross_salary
            existing.net_salary = net_salary
            existing.earnings_data = earnings_data
            existing.deductions_data = deductions_data
            existing.benefits_data = {}  # Vazio por enquanto
            existing.additional_data = additional_data
            existing.upload_filename = upload_filename
            existing.upload_date = datetime.now()
            existing.processed_by = self.user_id if self.user_id else None
            
            self.stats['updated'] = self.stats.get('updated', 0) + 1
            
        else:
            # Criar novo
            payroll = PayrollData(
                employee_id=employee.id,
                period_id=period_id,
                gross_salary=gross_salary,
                net_salary=net_salary,
                earnings_data=earnings_data,
                deductions_data=deductions_data,
                benefits_data={},  # Vazio por enquanto
                additional_data=additional_data,
                upload_filename=upload_filename,
                upload_date=datetime.now(),
                processed_by=self.user_id if self.user_id else None
            )
            self.db.add(payroll)
        
        self.stats['processed'] += 1
        self.stats['updated_payrolls'] = self.stats.get('updated_payrolls', 0) + 1
    
    def _create_employee_from_csv(self, row: pd.Series, matricula: str, division_code: str) -> Employee:
        """Cria employee temporário a partir do CSV"""
        employee = Employee(
            unique_id=matricula,
            name=str(row.get('Nome Colaborador', row.get('NOME', ''))).strip(),
            company_code=division_code  # Usar company_code ao invés de division_code
        )
        
        # Campos opcionais
        if 'Data Admissão' in row or 'DT_ADMISSAO' in row:
            date_str = row.get('Data Admissão', row.get('DT_ADMISSAO'))
            if date_str:
                employee.admission_date = parse_br_date(date_str)
        
        if 'CPF' in row or 'CPF_FUNC' in row:
            cpf_str = row.get('CPF', row.get('CPF_FUNC'))
            if cpf_str:
                employee.cpf = normalize_cpf(cpf_str)
        
        self.db.add(employee)
        self.db.flush()
        
        return employee
    
    def _extract_earnings(self, row: pd.Series) -> Dict[str, float]:
        """
        Extrai proventos do CSV - APENAS colunas essenciais
        """
        earnings = {}
        
        # Horas Extras
        he_fields = {
            'HE_50_DIURNAS': 'Horas Extras 50% Diurnas',
            'HE_100_DIURNAS': 'Horas Extras 100% Diurnas',
            'HE_50_NOTURNAS': 'Horas Extras 50% Noturnas',
            'HE_100_NOTURNAS': 'Horas Extras 100% Noturnas',
            'DSR_HE_DIURNAS': 'DSR S/Horas Extras Diurnas',
            'DSR_HE_NOTURNAS': 'DSR S/Horas Extras Noturnas',
            'ADICIONAL_NOTURNO': 'Adicional Noturno',
        }
        
        for json_field, csv_field in he_fields.items():
            val = self._get_number(row, [csv_field])
            if val > 0:
                earnings[json_field] = val
        
        # Gratificações
        val = self._get_number(row, ['Gratificação de Função 20%'])
        if val > 0:
            earnings['GRATIFICACAO_FUNCAO_20'] = val
        
        # Periculosidade e Insalubridade
        val = self._get_number(row, ['Periculosidade'])
        if val > 0:
            earnings['PERICULOSIDADE'] = val
        
        val = self._get_number(row, ['Insalubridade S/Salário Mínimo'])
        if val > 0:
            earnings['INSALUBRIDADE'] = val
        
        # Plano de Saúde (soma de várias colunas)
        plano_saude = 0
        plano_saude += self._get_number(row, ['Outras despesas  Plano de Saúde'])
        plano_saude += self._get_number(row, ['Saude Bradesco'])
        plano_saude += self._get_number(row, ['Mensalidade  Plano de Saúde'])
        plano_saude += self._get_number(row, ['Serviços odontológicos'])
        if plano_saude > 0:
            earnings['PLANO_SAUDE'] = plano_saude
        
        # Outros adicionais
        outros_fields = {
            'TRANSFERENCIA_FILIAL': 'Transferência de Filial',
            'AJUDA_CUSTO': 'Ajuda de Custo',
            'LICENCA_PATERNIDADE': 'Licença Paternidade',
        }
        
        for json_field, csv_field in outros_fields.items():
            val = self._get_number(row, [csv_field])
            if val > 0:
                earnings[json_field] = val
        
        return earnings
    
    def _extract_deductions(self, row: pd.Series) -> Dict[str, float]:
        """
        Extrai descontos do CSV - APENAS colunas essenciais
        """
        deductions = {}
        
        # INSS
        val = self._get_number(row, ['INSS'])
        if val > 0:
            deductions['INSS'] = val
        
        # IRRF
        val = self._get_number(row, ['IRRF'])
        if val > 0:
            deductions['IRRF'] = val
        
        # FGTS
        val = self._get_number(row, ['FGTS'])
        if val > 0:
            deductions['FGTS'] = val
        
        # Empréstimo do Trabalhador
        val = self._get_number(row, ['Empréstimo Crédito do Trabalhador'])
        if val > 0:
            deductions['EMPRESTIMO_TRABALHADOR'] = val
        
        # Adiantamento
        val = self._get_number(row, ['Adiantamento'])
        if val > 0:
            deductions['ADIANTAMENTO'] = val
        
        return deductions
    
    def _extract_additional(self, row: pd.Series) -> Dict[str, Any]:
        """
        Extrai campos adicionais - APENAS essenciais
        """
        additional = {}
        
        # Salário Mensal
        val = self._get_number(row, ['Salário Mensal', 'Valor Salário'])
        if val > 0:
            additional['Salário Mensal'] = val
        
        # Total Proventos
        val = self._get_number(row, ['Total de Proventos'])
        if val > 0:
            additional['Total de Proventos'] = val
        
        # Total Descontos
        val = self._get_number(row, ['Total de Descontos'])
        if val > 0:
            additional['Total de Descontos'] = val
        
        # Líquido
        val = self._get_number(row, ['Líquido de Cálculo'])
        if val > 0:
            additional['Líquido de Cálculo'] = val
        
        # Horas Faltas (soma de duas colunas)
        horas_faltas = 0
        horas_faltas += self._get_number(row, ['Horas Faltas Diurnas'])
        horas_faltas += self._get_number(row, ['Horas Faltas DSR Diurnas'])
        if horas_faltas > 0:
            additional['Horas Faltas'] = horas_faltas
        
        # Atestados Médicos (soma de duas colunas)
        atestados = 0
        atestados += self._get_number(row, ['Atestado Médico'])
        atestados += self._get_number(row, ['Horas Lic.Médica Diurnas'])
        if atestados > 0:
            additional['Atestados Médicos'] = atestados
        
        # Status
        if 'Descrição' in row and row['Descrição']:
            additional['Status'] = str(row['Descrição']).strip()
        
        return additional
    
    def _invalidate_indicators_cache(self):
        """Invalida cache de indicadores"""
        try:
            from app.services.hr_indicators import HRIndicatorsService
            indicators_service = HRIndicatorsService(self.db)
            indicators_service.invalidate_cache()
            print("🔄 Cache de indicadores invalidado")
        except Exception as e:
            print(f"⚠️ Erro ao invalidar cache: {e}")
    
    def _create_processing_log(
        self, 
        period_id: Optional[int],
        filename: str,
        file_path: str,
        status: str,
        error_message: Optional[str] = None,
        processing_time: float = 0
    ):
        """Cria registro de log de processamento"""
        try:
            from app.models.payroll import PayrollProcessingLog
            
            file_size = None
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
            
            log = PayrollProcessingLog(
                period_id=period_id,
                filename=filename,
                file_size=file_size,
                total_rows=self.stats.get('total_rows'),
                processed_rows=self.stats.get('processed'),
                error_rows=self.stats.get('errors'),
                status=status,
                error_message=error_message,
                processing_summary={
                    'new_employees': self.stats.get('new_employees', 0),
                    'updated_payrolls': self.stats.get('updated_payrolls', 0),
                    'skipped': self.stats.get('skipped', 0),
                    'warnings': len(self.warnings),
                    'errors_detail': self.errors[:10] if self.errors else []
                },
                processed_by=self.user_id if self.user_id else None,
                processing_time=round(processing_time, 2)
            )
            
            self.db.add(log)
            self.db.flush()
            print(f"📝 Log de processamento criado: {filename} - {status}")
            
        except Exception as e:
            print(f"⚠️ Erro ao criar log de processamento: {e}")
    
    def _error_response(self, message: str) -> Dict[str, Any]:
        """Retorna resposta de erro"""
        return {
            'success': False,
            'error': message,
            'stats': self.stats,
            'errors': self.errors,
            'warnings': self.warnings
        }
