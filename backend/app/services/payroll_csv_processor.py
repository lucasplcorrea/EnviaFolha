"""
Serviço para processar CSVs de folha de pagamento
Inspirado em: consolidar_empreendimentos.py e consolidar_infraestrutura.py
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
    
    Fluxo:
    1. Detecta tipo de arquivo (mensal, 13º, complementar)
    2. Lê CSV com encoding correto (latin-1)
    3. Cria/busca PayrollPeriod
    4. Processa cada linha do CSV
    5. Salva em payroll_data (JSONB)
    6. Invalida cache de indicadores
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
    
    def process_csv_file(
        self, 
        file_path: str, 
        division_code: str = '0060',
        auto_create_employees: bool = False
    ) -> Dict[str, Any]:
        """
        Processa arquivo CSV de folha de pagamento
        
        Args:
            file_path: Caminho completo do arquivo CSV
            division_code: '0060' (Empreendimentos) ou '0059' (Infraestrutura)
            auto_create_employees: Se True, cria employees não encontrados
            
        Returns:
            {
                'success': bool,
                'period_id': int,
                'period_name': str,
                'stats': dict,
                'errors': list,
                'warnings': list
            }
        """
        start_time = time.time()
        
        try:
            # 1. Validar arquivo
            if not os.path.exists(file_path):
                return self._error_response(f"Arquivo não encontrado: {file_path}")
            
            # 2. Detectar tipo de arquivo
            filename = os.path.basename(file_path)
            file_info = detect_payroll_type(filename)
            
            if not file_info['matched']:
                return self._error_response(f"Tipo de arquivo não reconhecido: {filename}")
            
            print(f"📄 Processando {file_info['tipo']} - {file_info['mes']}/{file_info['ano']}")
            
            # 3. Ler CSV com tratamento de encoding
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
                        division_code=division_code,
                        auto_create_employees=auto_create_employees,
                        upload_filename=filename
                    )
                    self.stats['processed'] += 1
                    
                except Exception as e:
                    self.stats['errors'] += 1
                    self.errors.append({
                        'row': idx + 2,  # +2 porque índice começa em 0 e tem header
                        'error': str(e)
                    })
                    print(f"❌ Erro na linha {idx + 2}: {e}")
            
            # 6. Commit final
            self.db.commit()
            
            # 7. Registrar log de processamento
            self._create_processing_log(
                period_id=period.id,
                filename=filename,
                file_path=file_path,
                status='completed',
                processing_time=time.time() - start_time
            )
            
            # 8. Invalidar cache de indicadores
            self._invalidate_indicators_cache()
            
            # 9. Resultado
            processing_time = time.time() - start_time
            
            return {
                'success': True,
                'period_id': period.id,
                'period_name': period.period_name,
                'division': division_code,
                'file_type': file_info['tipo'],
                'stats': self.stats,
                'errors': self.errors,
                'warnings': self.warnings,
                'processing_time_seconds': round(processing_time, 2)
            }
            
        except Exception as e:
            self.db.rollback()
            # Registrar log de erro
            try:
                self._create_processing_log(
                    period_id=None,
                    filename=filename if 'filename' in locals() else os.path.basename(file_path),
                    file_path=file_path,
                    status='failed',
                    error_message=str(e),
                    processing_time=time.time() - start_time
                )
            except:
                pass  # Ignorar erro ao registrar log
            return self._error_response(f"Erro crítico: {str(e)}")
    
    def _read_csv(self, file_path: str) -> Optional[pd.DataFrame]:
        """
        Lê CSV com encoding correto e tratamento de erros
        
        Tenta:
        1. latin-1 (padrão dos CSVs brasileiros)
        2. utf-8 (fallback)
        3. cp1252 (Windows)
        """
        encodings = ['latin-1', 'utf-8', 'cp1252']
        
        for encoding in encodings:
            try:
                df = pd.read_csv(
                    file_path,
                    delimiter=';',  # Padrão dos CSVs brasileiros
                    encoding=encoding,
                    on_bad_lines='skip',  # Pular linhas com erro
                    dtype=str  # Ler tudo como string primeiro
                )
                print(f"✅ CSV lido com encoding: {encoding}")
                print(f"📋 Colunas encontradas: {len(df.columns)}")
                return df
                
            except Exception as e:
                print(f"⚠️ Falha com encoding {encoding}: {e}")
                continue
        
        return None
    
    def _get_or_create_period(
        self, 
        year: int, 
        month: int, 
        period_type: str
    ) -> Optional[PayrollPeriod]:
        """
        Busca ou cria período de folha
        
        Args:
            year: Ano (ex: 2024)
            month: Mês (1-12)
            period_type: Tipo (mensal, 13_adiantamento, etc)
            
        Nota: 13º salário é CONSOLIDADO com o período mensal correspondente:
        - 13_adiantamento → busca/cria período de Novembro
        - 13_integral → busca/cria período de Dezembro
        """
        # 13º salário deve ser consolidado com o período mensal (não criar separado)
        if period_type in ['13_adiantamento', '13_integral']:
            # Forçar tipo 'mensal' para consolidar com folha do mês
            period_type = 'mensal'
            print(f"🔄 13º salário será consolidado com período mensal: {month}/{year}")
        
        # Mapear tipo para nome amigável
        type_names = {
            'mensal': f'{self._get_month_name(month)} {year}',
            'complementar': f'Folha Complementar {month}/{year}',
            'adiantamento_salario': f'Adiantamento Salarial {month}/{year}'
        }
        
        period_name = type_names.get(period_type, f'Folha {month}/{year}')
        
        # Buscar período existente
        period = self.db.query(PayrollPeriod).filter(
            and_(
                PayrollPeriod.year == year,
                PayrollPeriod.month == month,
                PayrollPeriod.period_name == period_name
            )
        ).first()
        
        if period:
            print(f"✅ Período existente encontrado: {period_name}")
            return period
        
        # Criar novo período
        try:
            period = PayrollPeriod(
                year=year,
                month=month,
                period_name=period_name,
                description=f"Importado de CSV - Tipo: {period_type}",
                is_active=True,
                is_closed=False
            )
            self.db.add(period)
            self.db.commit()
            print(f"✅ Novo período criado: {period_name}")
            return period
            
        except Exception as e:
            print(f"❌ Erro ao criar período: {e}")
            self.db.rollback()
            return None
    
    def _process_employee_payroll(
        self,
        row: pd.Series,
        period_id: int,
        division_code: str,
        auto_create_employees: bool,
        upload_filename: str
    ):
        """
        Processa linha individual do CSV (um colaborador)
        """
        # 1. Extrair código do funcionário (tentar várias variações de nome de coluna)
        codigo_func = row.get('Código Funcionário', 
                            row.get('CODIGO_FUNC', 
                            row.get('COD_FUNC', 
                            row.get('Codigo Funcionario', ''))))
        if not codigo_func or str(codigo_func).strip() == '':
            raise ValueError("Código do funcionário não encontrado na linha")
        
        # 2. Gerar matrícula completa
        matricula = extract_employee_code(codigo_func, division_code)
        
        # 3. Buscar employee no banco
        employee = self.db.query(Employee).filter(
            Employee.unique_id == matricula
        ).first()
        
        if not employee:
            if auto_create_employees:
                # Criar employee temporário
                employee = self._create_employee_from_csv(row, matricula, division_code)
                self.stats['new_employees'] += 1
            else:
                self.warnings.append({
                    'matricula': matricula,
                    'message': f"Funcionário não encontrado (matrícula: {matricula})"
                })
                self.stats['skipped'] += 1
                return
        
        # 4. Construir JSONs dinâmicos
        earnings_data = self._extract_earnings(row)
        deductions_data = self._extract_deductions(row)
        benefits_data = self._extract_benefits(row)
        additional_data = self._extract_additional(row)
        
        # 5. Calcular totais
        gross_salary = parse_br_number(row.get('TOTAL_PROVENTOS', 0))
        net_salary = parse_br_number(row.get('LIQ_A_RECEBER', 0))
        
        # 6. Verificar se já existe registro para este período
        existing = self.db.query(PayrollData).filter(
            and_(
                PayrollData.employee_id == employee.id,
                PayrollData.period_id == period_id
            )
        ).first()
        
        if existing:
            # Atualizar registro existente
            existing.gross_salary = gross_salary
            existing.net_salary = net_salary
            existing.earnings_data = earnings_data
            existing.deductions_data = deductions_data
            existing.benefits_data = benefits_data
            existing.additional_data = additional_data
            existing.upload_filename = upload_filename
            existing.upload_date = datetime.now()
            existing.processed_by = self.user_id
            
        else:
            # Criar novo registro
            payroll = PayrollData(
                employee_id=employee.id,
                period_id=period_id,
                gross_salary=gross_salary,
                net_salary=net_salary,
                earnings_data=earnings_data,
                deductions_data=deductions_data,
                benefits_data=benefits_data,
                additional_data=additional_data,
                upload_filename=upload_filename,
                upload_date=datetime.now(),
                processed_by=self.user_id
            )
            self.db.add(payroll)
        
        # 7. Atualizar termination_date se status indica desligamento
        status = additional_data.get('Status', '')
        if status and ('Demitido' in status or 'Rescisão' in status or 'Rescisao' in status):
            # Obter período para pegar ano/mês
            period = self.db.query(PayrollPeriod).filter(
                PayrollPeriod.id == period_id
            ).first()
            
            if period and not employee.termination_date:
                # Calcular último dia do mês do período
                last_day = calendar.monthrange(period.year, period.month)[1]
                termination_date = date(period.year, period.month, last_day)
                
                employee.termination_date = termination_date
                employee.employment_status = 'Desligado'
                
                print(f"   📅 Desligamento detectado: {employee.name} - Data: {termination_date.strftime('%d/%m/%Y')}")
        
        self.stats['updated_payrolls'] += 1
    
    def _create_employee_from_csv(
        self, 
        row: pd.Series, 
        matricula: str,
        division_code: str
    ) -> Employee:
        """Cria employee a partir dos dados do CSV"""
        # Tentar várias variações de nomes de colunas
        name = row.get('Nome Colaborador', row.get('NOME', 'Nome não informado'))
        cargo = row.get('Descrição Cargo', row.get('CARGO', None))
        
        # CPF e Phone apenas se tiver valor
        cpf_raw = row.get('CPF', None)
        cpf = normalize_cpf(cpf_raw) if cpf_raw and str(cpf_raw).strip() else None
        
        phone_raw = row.get('TELEFONE', None)
        phone = normalize_phone(phone_raw) if phone_raw and str(phone_raw).strip() else None
        
        employee = Employee(
            unique_id=matricula,
            name=name,
            cpf=cpf,
            phone=phone,
            email=row.get('EMAIL', None),
            department=row.get('DEPARTAMENTO', None),
            position=cargo,
            sector=row.get('SETOR', None),
            company_code=division_code,
            is_active=True,
            created_by=self.user_id
        )
        
        # Dados adicionais se disponíveis
        dt_admissao = row.get('Data Admissão', row.get('DT_ADMISSAO', None))
        if dt_admissao:
            employee.admission_date = parse_br_date(dt_admissao)
        
        dt_nascimento = row.get('Data Nascimento', row.get('DT_NASCIMENTO', None))
        if dt_nascimento:
            employee.birth_date = parse_br_date(dt_nascimento)
            
        if 'SEXO' in row:
            employee.sex = row['SEXO']
        if 'ESTADO_CIVIL' in row:
            employee.marital_status = row['ESTADO_CIVIL']
        
        self.db.add(employee)
        self.db.flush()  # Gera o ID sem fazer commit
        
        return employee
    
    def _extract_earnings(self, row: pd.Series) -> Dict[str, float]:
        """Extrai proventos do CSV para JSON"""
        earnings_fields = [
            ('SALARIO_BASE', 'Valor Salário'),
            ('PRO_LABORE', 'Pro-Labore'),
        ]
        
        earnings = {}
        
        # Campos simples
        for json_field, csv_field in earnings_fields:
            if csv_field in row and row[csv_field]:
                value = parse_br_number(row[csv_field])
                if value > 0:
                    earnings[json_field] = value
        
        # Horas Extras - Segmentadas por tipo e período
        he_fields = {
            'HORAS_EXTRAS_50_DIURNAS': 'Horas Extras 50% Diurnas',
            'HORAS_EXTRAS_50_NOTURNAS': 'Horas Extras 50% Noturnas',
            'HORAS_EXTRAS_60_DIURNAS': 'Horas Extras 60% Diurnas',
            'HORAS_EXTRAS_100_DIURNAS': 'Horas Extras 100% Diurnas',
            'HORAS_EXTRAS_100_NOTURNAS': 'Horas Extras 100% Noturnas',
        }
        
        for json_field, csv_field in he_fields.items():
            if csv_field in row and row[csv_field]:
                value = parse_br_number(row[csv_field])
                if value > 0:
                    earnings[json_field] = value
        
        # DSR sobre Horas Extras
        dsr_he_fields = {
            'DSR_HORAS_EXTRAS_DIURNAS': 'DSR S/Horas Extras Diurnas',
            'DSR_HORAS_EXTRAS_NOTURNAS': 'DSR S/Horas Extras Noturnas',
        }
        
        for json_field, csv_field in dsr_he_fields.items():
            if csv_field in row and row[csv_field]:
                value = parse_br_number(row[csv_field])
                if value > 0:
                    earnings[json_field] = value
        
        # Adicional Noturno
        adicional_noturno_fields = {
            'ADICIONAL_NOTURNO': 'Adicional Noturno',
            'REDUCAO_HORA_NOTURNA': 'Redução Hora Noturna',
        }
        
        for json_field, csv_field in adicional_noturno_fields.items():
            if csv_field in row and row[csv_field]:
                value = parse_br_number(row[csv_field])
                if value > 0:
                    earnings[json_field] = value
        
        # Gratificações
        gratificacao_fields = {
            'GRATIFICACAO_FUNCAO': 'Gratificação de Função',
            'GRATIFICACAO_FUNCAO_20': 'Gratificação de Função 20%',
            'GRATIFICACAO_FUNCAO_13_SAL_PROP': 'Gratificacao Função 13o Sal.Prop.',
            'GRATIFICACAO_FUNCAO_ABONO': 'Gratificacao Função Abono Pecuniario',
            'GRATIFICACAO_FUNCAO_FERIAS': 'Gratificacao Função Férias',
            'GRATIFICACAO_FUNCAO_FERIAS_PROP': 'Gratificacao Função Férias Proporc.',
        }
        
        for json_field, csv_field in gratificacao_fields.items():
            if csv_field in row and row[csv_field]:
                value = parse_br_number(row[csv_field])
                if value > 0:
                    earnings[json_field] = value
        
        # 13º Salário - Adiantamento (Novembro)
        decimo_adiantamento_fields = {
            '13_SALARIO_ADIANTAMENTO': '13o Salário Adiantamento',
            '13_GRATIFICACAO_FUNCAO_ADIANTAMENTO': 'Gratificacao Função 13o Sal.Adiantamento',
        }
        
        for json_field, csv_field in decimo_adiantamento_fields.items():
            if csv_field in row and row[csv_field]:
                value = parse_br_number(row[csv_field])
                if value > 0:
                    earnings[json_field] = value
        
        # 13º Salário - Integral (Dezembro)
        decimo_integral_fields = {
            '13_SALARIO_INTEGRAL': '13o Salário Integral',
            '13_SALARIO_MATERNIDADE_GPS': '13o Salário Maternidade (GPS)',
            '13_MEDIA_EVENTOS_VARIAVEIS': 'Med.Eve.Var.13o Sal.Integral',
            '13_MEDIA_HORAS_EXTRAS_DIURNO': 'Med.Hrs.Ext.13o Sal.Integral Diurno',
            '13_MEDIA_HORAS_EXTRAS_NOTURNAS': 'Med.Hrs.Ext.13o Sal.Integral Noturnas',
            '13_GRATIFICACAO_FUNCAO_INTEGRAL': 'Gratificacao Função 13o Sal.Integral',
            '13_ADICIONAL_NOTURNO': 'Adicional Noturno 13o Sal.Integral',
        }
        
        for json_field, csv_field in decimo_integral_fields.items():
            if csv_field in row and row[csv_field]:
                value = parse_br_number(row[csv_field])
                if value > 0:
                    earnings[json_field] = value
        
        # Férias - Valores Base
        ferias_fields = {
            'FERIAS_VALOR_BASE': 'Horas Férias Diurnas',
            'FERIAS_ABONO_1_3': '1/3 Sobre Férias',
            'FERIAS_MEDIA_HORAS_EXTRAS': 'Med.Hrs.Ext.S/Férias Diurnas',
            'FERIAS_MEDIA_HORAS_EXTRAS_NOTURNAS': 'Med.Hrs.Ext.S/Férias Noturnas',
            'FERIAS_ADICIONAL_NOTURNO': 'Adicional Noturno S/Férias',
        }
        
        for json_field, csv_field in ferias_fields.items():
            if csv_field in row and row[csv_field]:
                value = parse_br_number(row[csv_field])
                if value > 0:
                    earnings[json_field] = value
        
        # Adicionais Legais
        adicionais_legais = {
            'PERICULOSIDADE': 'Periculosidade',
            'INSALUBRIDADE': 'Insalubridade S/Salário Mínimo',
            'INSALUBRIDADE_NORMATIVO': 'Insalubridade S/Salário Normativo',
        }
        
        for json_field, csv_field in adicionais_legais.items():
            if csv_field in row and row[csv_field]:
                value = parse_br_number(row[csv_field])
                if value > 0:
                    earnings[json_field] = value
        
        return earnings
    
    def _extract_deductions(self, row: pd.Series) -> Dict[str, float]:
        """Extrai descontos do CSV para JSON"""
        # FGTS - todas as variantes
        fgts_fields = ['FGTS', 'FGTS 13o Salário GRFC', 'FGTS GRFC', 'FGTS Multa - Depósito Saldo',
                       'FGTS S/13o Sal.Proporc.Resc.', 'FGTS S/Aviso Prévio Indenizado', 'FGTS S/Férias',
                       'FGTS s/13o Salário Indenizado GRFC', 'FGTS S/13o Salário']
        
        # INSS - todas as variantes (incluindo devoluções negativas)
        inss_fields = ['INSS', 'INSS S/13o Salário', 'INSS S/Férias', 'Devolução INSS Mês']
        
        # IRRF - todas as variantes  
        irrf_fields = ['IRRF', 'IRRF Férias na Rescisão', 'IRRF S/13o Salário', 'IRRF S/Férias']
        
        deductions = {}
        
        # Descontos específicos de 13º e Férias
        desconto_13_fields = {
            'DESCONTO_13_ADIANTAMENTO': 'Desconto 13o Salário Adiantamento',
        }
        
        for json_field, csv_field in desconto_13_fields.items():
            if csv_field in row and row[csv_field]:
                value = parse_br_number(row[csv_field])
                if value > 0:
                    deductions[json_field] = value
        
        desconto_ferias_fields = {
            'DESCONTO_FERIAS_ADIANTAMENTO': 'Desconto Adiantamento Férias',
        }
        
        for json_field, csv_field in desconto_ferias_fields.items():
            if csv_field in row and row[csv_field]:
                value = parse_br_number(row[csv_field])
                if value > 0:
                    deductions[json_field] = value
        
        # Somar todos os FGTS
        total_fgts = 0
        for field in fgts_fields:
            if field in row and row[field]:
                value = parse_br_number(row[field])
                if value > 0:
                    total_fgts += value
        if total_fgts > 0:
            deductions['FGTS'] = total_fgts
        
        # INSS (somar descontos e SUBTRAIR devoluções)
        inss_discount_fields = [
            'INSS',
            'INSS S/13o Salário',
            'INSS S/Férias'
        ]
        
        total_inss = 0
        # Somar descontos de INSS
        for field in inss_discount_fields:
            if field in row and row[field]:
                value = parse_br_number(row[field])
                if value > 0:
                    total_inss += value
        
        # SUBTRAIR devolução (estorno positivo para colaborador)
        if 'Devolução INSS Mês' in row and row['Devolução INSS Mês']:
            devolucao = parse_br_number(row['Devolução INSS Mês'])
            total_inss -= devolucao  # Subtrai devolução do desconto
        
        if total_inss > 0:  # Apenas se houver desconto líquido
            deductions['INSS'] = total_inss
        
        # Somar todos os IRRF
        total_irrf = 0
        for field in irrf_fields:
            if field in row and row[field]:
                value = parse_br_number(row[field])
                if value > 0:
                    total_irrf += value
        if total_irrf > 0:
            deductions['IRRF'] = total_irrf
        
        # Outros descontos
        other_deductions = [
            ('ADIANTAMENTO', 'Desconto Adiantamento Salarial'),
            ('DESCONTOS_DIVERSOS', 'Descontos Diversos'),
        ]
        
        for json_field, csv_field in other_deductions:
            if csv_field in row and row[csv_field]:
                value = parse_br_number(row[csv_field])
                if value > 0:
                    deductions[json_field] = value
        
        return deductions
    
    def _extract_benefits(self, row: pd.Series) -> Dict[str, float]:
        """Extrai benefícios do CSV para JSON"""
        benefits = {}
        
        # Plano de Saúde - verificar várias colunas possíveis
        plano_fields = ['Mensalidade  Plano de Saúde', 'Planos de Saúde - Total da Fatura', 
                        'Benefício Plano de Saúde - Mensalidade', 'Saude Bradesco']
        
        total_plano = 0
        for field in plano_fields:
            if field in row and row[field]:
                value = parse_br_number(row[field])
                if value > 0:
                    total_plano += value
        
        if total_plano > 0:
            benefits['PLANO_SAUDE'] = total_plano
        
        # Vale Transporte
        if 'Vale Transporte (%)' in row and row['Vale Transporte (%)']:
            value = parse_br_number(row['Vale Transporte (%)'])
            if value > 0:
                benefits['VALE_TRANSPORTE'] = value
        
        return benefits
    
    def _extract_additional(self, row: pd.Series) -> Dict[str, Any]:
        """Extrai dados adicionais/complementares do CSV para JSON"""
        additional_fields = [
            ('Valor Salário', 'Valor Salário'),
            ('Salário Mensal', 'Salário Mensal'),
            ('Total de Proventos', 'Total de Proventos'),
            ('Total de Descontos', 'Total de Descontos'),
            ('Total de Vantagens', 'Total de Vantagens'),  # 🆕 NOVA COLUNA
            ('Líquido de Cálculo', 'Líquido de Cálculo'),
            ('Horas Normais Diurnas', 'Horas Normais Diurnas'),
            ('Horas Normais Noturnas', 'Horas Normais Noturnas'),  # 🆕 HORAS NOTURNAS
            ('Horas Extras 50% Diurnas', 'Horas Extras 50% Diurnas'),
            ('Horas DSR Diurnas', 'Horas DSR Diurnas'),
            ('Descrição', 'Status'),  # Status do colaborador: Trabalhando, Férias, Demitido
        ]
        
        additional = {}
        for csv_field, json_field in additional_fields:
            if csv_field in row and row[csv_field]:
                # Para Status (Descrição), manter como string
                if csv_field == 'Descrição':
                    additional[json_field] = str(row[csv_field]).strip()
                else:
                    value = parse_br_number(row[csv_field])
                    if value != 0:  # Incluir zeros para campos numéricos importantes
                        additional[json_field] = value
        
        return additional
    
    def _invalidate_indicators_cache(self):
        """Invalida cache de indicadores após importação"""
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
            
            # Calcular tamanho do arquivo
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
                    'errors_detail': self.errors[:10] if self.errors else []  # Primeiros 10 erros
                },
                processed_by=self.user_id if self.user_id else None,  # NULL se não tiver user_id
                processing_time=round(processing_time, 2)
            )
            
            self.db.add(log)
            self.db.commit()
            print(f"📝 Log de processamento criado: {filename} - {status}")
            
        except Exception as e:
            print(f"⚠️ Erro ao criar log de processamento: {e}")
            # Não propagar o erro para não quebrar o processamento
    
    def _get_month_name(self, month: int) -> str:
        """Retorna nome do mês em português"""
        months = [
            'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
        ]
        return months[month - 1] if 1 <= month <= 12 else f'Mês {month}'
    
    def _error_response(self, message: str) -> Dict[str, Any]:
        """Retorna resposta de erro padronizada"""
        return {
            'success': False,
            'error': message,
            'stats': self.stats,
            'errors': self.errors,
            'warnings': self.warnings
        }
