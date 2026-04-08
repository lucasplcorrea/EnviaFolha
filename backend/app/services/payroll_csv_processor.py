"""
Serviço REFATORADO para processar CSVs de folha de pagamento
VERSÃO SIMPLIFICADA - apenas colunas essenciais conforme mapeamento RH
"""
import os
import time
import re
import calendar
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.employee import Employee
from app.models.company import Company
from app.models.payroll import PayrollPeriod, PayrollData
from app.models.leave import LeaveRecord
from app.models.user import User
from sqlalchemy.sql import func
from app.utils.parsers import (
    parse_br_number,
    parse_br_date,
    detect_payroll_type,
    extract_employee_code,
    normalize_cpf,
    normalize_phone,
    normalize_name_for_payroll,
    generate_name_id,
    CSV_COLUMN_MAPPING
)

# Mapeamento de códigos de situação para tipos de afastamento
SITUATION_TO_LEAVE_TYPE = {
    2: 'Férias',
    3: 'Auxílio Doença',
    9: 'Licença Remunerada',
    13: 'Licença Maternidade',
    14: 'Auxílio Doença',  # até 15 dias
    23: 'Auxílio Doença',  # dentro 60 dias
    31: 'Licença Paternidade',
}

# Situações que devem ser ignoradas (trabalhando, demitido)
IGNORE_SITUATIONS = {1, 7}


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

    def _normalize_cnpj(self, cnpj: Optional[str]) -> str:
        if not cnpj:
            return ''
        digits = re.sub(r'\D', '', str(cnpj))
        if len(digits) == 14:
            return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
        return digits

    def _infer_division_code_from_cnpj(self, cnpj: Optional[str]) -> Optional[str]:
        normalized = self._normalize_cnpj(cnpj)
        if not normalized:
            return None
        company = self.db.query(Company).filter(Company.cnpj == normalized).first()
        if company:
            return company.payroll_prefix
        return None

    def _normalize_name(self, name: Optional[str]) -> str:
        if not name:
            return ''
        return re.sub(r'\s+', ' ', str(name).strip().lower())

    def _find_employee(self, division_code: str, matricula: str, absolute_id: str, name: str) -> Optional[Employee]:
        """
        Tenta localizar employee através de regras de prioridade:
        
        1. Absolute_id (company + matricula + cpf_digits) - máxima confiança
        2. Name_id (company + matricula + nome_normalizado) - alta confiança, sem CPF
        3. Company + Matricula + Nome - confiança média
        4. Empresa + Matrícula único - confiança baixa
        5. Nenhum match - revisão manual necessária
        """
        match_source = None
        
        # 1) Absolute_id direto (maior confiança)
        if absolute_id:
            abs_employees = self.db.query(Employee).filter(Employee.absolute_id == absolute_id).all()
            if len(abs_employees) > 1:
                self.warnings.append({
                    'absolute_id': absolute_id,
                    'message': 'Duplicidade de absolute_id encontrada. Revisão manual necessária.',
                    'candidates': [{'id': e.id, 'name': e.name, 'company_code': e.company_code} for e in abs_employees]
                })
                return None
            if len(abs_employees) == 1:
                match_source = 'absolute_id'
                return abs_employees[0]
        
        # 2) Name_id (empresa + matrícula + nome normalizado)
        if division_code and matricula and name:
            name_id_csv = generate_name_id(division_code, matricula, name)
            if name_id_csv:
                name_id_employees = self.db.query(Employee).filter(
                    Employee.name_id == name_id_csv
                ).all()
                if len(name_id_employees) == 1:
                    match_source = 'name_id'
                    return name_id_employees[0]
                elif len(name_id_employees) > 1:
                    self.warnings.append({
                        'name_id': name_id_csv,
                        'message': f'Múltiplos colaboradores para name_id {name_id_csv}. Revisão manual necessária.',
                        'candidates': [{'id': e.id, 'name': e.name, 'company_code': e.company_code} for e in name_id_employees]
                    })

        # 3) Empresa + matricula (com fallback para nome)
        candidates = self.db.query(Employee).filter(
            Employee.company_code == division_code,
            Employee.unique_id == matricula
        ).all()

        if len(candidates) == 1:
            match_source = 'company_matricula_unique'
            return candidates[0]

        normalized_name = self._normalize_name(name)
        if normalized_name:
            name_matches = [e for e in candidates if self._normalize_name(e.name) == normalized_name]
            if len(name_matches) == 1:
                match_source = 'company_matricula_name'
                return name_matches[0]

        # 4) Fallback somente unique_id (várias ou não acompanhadas)
        candidates_by_unique = self.db.query(Employee).filter(Employee.unique_id == matricula).all()
        if len(candidates_by_unique) == 1:
            match_source = 'unique_id_only'
            return candidates_by_unique[0]

        # Nao encontrou único, retorna None para ação manual
        return None

    def _compute_absolute_id(self, division_code: str, matricula: str, cpf: Optional[str] = None) -> str:
        """Gera absolute_id baseado em divisão+matrícula+CPF (somente dígitos)."""
        cpf_digits = ''
        if cpf:
            cpf_digits = re.sub(r'\D', '', str(cpf))

        if cpf_digits:
            return f"{division_code}-{matricula}-{cpf_digits}"

        return f"{division_code}-{matricula}"

    def process_csv_file(
        self, 
        file_path: str, 
        division_code: str = '0060',
        auto_create_employees: bool = False,
        forced_year: Optional[int] = None,
        forced_month: Optional[int] = None,
        forced_payroll_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Processa arquivo CSV de folha de pagamento"""
        start_time = time.time()
        
        # Armazenar division_code como atributo da classe
        self.division = division_code
        
        try:
            # 1. Validar arquivo
            if not os.path.exists(file_path):
                return self._error_response(f"Arquivo não encontrado: {file_path}")
            
            # 2. Resolver tipo/período (preferência para formulário manual)
            filename = os.path.basename(file_path)

            if forced_year and forced_month and forced_payroll_type:
                file_info = {
                    'tipo': forced_payroll_type,
                    'mes': str(int(forced_month)).zfill(2),
                    'ano': str(int(forced_year)),
                    'matched': True,
                    'filename': filename,
                }
            else:
                file_info = detect_payroll_type(filename)
                if not file_info['matched']:
                    return self._error_response(
                        f"Tipo de arquivo não reconhecido: {filename}. Informe mês/ano/tipo no formulário."
                    )
            
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

        # Em alguns CSVs, pode haver CPF para disambiguar
        cpf_value = row.get('CPF', row.get('CPF_FUNC', row.get('Cpf', row.get('cpf', None))))
        cpf_normalized = normalize_cpf(cpf_value) if cpf_value else None
        absolute_id = self._compute_absolute_id(division_code, matricula, cpf_normalized)

# 3. Definir divisão/empresa com base no CSV se não informado pelo frontend
        if not division_code and not cpf_normalized:
            cnpj_value = row.get('CNPJ', row.get('Cnpj', row.get('cnpj', None)))
            inferred_division = self._infer_division_code_from_cnpj(cnpj_value)
            if inferred_division:
                division_code = inferred_division

        # Resolver pelo método unificado de matching
        collaborator_name = str(row.get('Nome Colaborador', row.get('NOME', '') or '')).strip()
        employee = self._find_employee(division_code=division_code, matricula=matricula, absolute_id=absolute_id, name=collaborator_name)

        # Se houver candidatos em múltiplas opções, identificamos a problemática
        if not employee:
            candidates = self.db.query(Employee).filter(
                Employee.company_code == division_code,
                Employee.unique_id == matricula
            ).all()
            if len(candidates) > 1:
                self.warnings.append({
                    'matricula': matricula,
                    'name': collaborator_name,
                    'message': 'Múltiplos colaboradores para mesma empresa+matrícula (colisão). Revisão manual necessária.',
                    'candidates': [{'id': e.id, 'name': e.name} for e in candidates]
                })
                self.stats['skipped'] += 1
                return

            candidates_by_unique = self.db.query(Employee).filter(Employee.unique_id == matricula).all()
            if len(candidates_by_unique) > 1:
                self.warnings.append({
                    'matricula': matricula,
                    'name': collaborator_name,
                    'message': 'Múltiplos colaboradores para mesma matrícula (sem empresa). Revisão manual necessária.',
                    'candidates': [{'id': e.id, 'name': e.name, 'company_code': e.company_code} for e in candidates_by_unique]
                })
                self.stats['skipped'] += 1
                return

        # Não atualizar dados de employee automaticamente para evitar correções silenciosas.
        # Não criar novos employees nessa rotina (força tarefa de validação / revisão manual).
        if not employee:
            self.warnings.append({
                'matricula': matricula,
                'name': str(row.get('Nome Colaborador', row.get('NOME', ''))).strip(),
                'message': f"Funcionário não encontrado (matrícula: {matricula}); não será criado automaticamente"
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
        
        # 7. Processar afastamentos baseado na coluna Situação
        self._process_leave_from_situation(row, employee, period_id)
    
    def _process_leave_from_situation(self, row: pd.Series, employee: Employee, period_id: int):
        """
        Cria/atualiza registro de afastamento baseado na coluna Situação do CSV.
        Considera o mês inteiro como período de afastamento.
        """
        try:
            # Extrair código da situação
            situacao = row.get('Situação', row.get('SITUACAO', None))
            if situacao is None:
                return
            
            try:
                situacao_code = int(situacao)
            except (ValueError, TypeError):
                return
            
            # Ignorar se for situação normal (trabalhando) ou demitido
            if situacao_code in IGNORE_SITUATIONS:
                return
            
            # Verificar se é uma situação de afastamento conhecida
            leave_type = SITUATION_TO_LEAVE_TYPE.get(situacao_code)
            if not leave_type:
                # Situação desconhecida - registrar como "Outro"
                descricao = row.get('Descrição', row.get('DESCRICAO', f'Situação {situacao_code}'))
                leave_type = str(descricao) if descricao else 'Outro'
            
            # Buscar informações do período para calcular datas
            period = self.db.query(PayrollPeriod).filter(PayrollPeriod.id == period_id).first()
            if not period:
                return
            
            # Calcular primeiro e último dia do mês
            year = period.year
            month = period.month
            start_date = date(year, month, 1)
            last_day = calendar.monthrange(year, month)[1]
            end_date = date(year, month, last_day)
            
            # Verificar se já existe um registro de afastamento para este período
            existing_leave = self.db.query(LeaveRecord).filter(
                and_(
                    LeaveRecord.employee_id == employee.id,
                    LeaveRecord.start_date == start_date,
                    LeaveRecord.end_date == end_date
                )
            ).first()
            
            if existing_leave:
                # Atualizar tipo se mudou
                if existing_leave.leave_type != leave_type:
                    existing_leave.leave_type = leave_type
                    existing_leave.notes = f'Atualizado via processamento CSV'
            else:
                # Criar novo registro de afastamento
                leave_record = LeaveRecord(
                    employee_id=employee.id,
                    unified_code=employee.unique_id,
                    leave_type=leave_type,
                    start_date=start_date,
                    end_date=end_date,
                    days=float(last_day),  # Mês inteiro
                    notes=f'Criado automaticamente via processamento CSV',
                    created_at=datetime.now()
                )
                self.db.add(leave_record)
                
                # Atualizar estatísticas
                self.stats['leaves_created'] = self.stats.get('leaves_created', 0) + 1
                
        except Exception as e:
            print(f"⚠️ Erro ao processar afastamento: {e}")
            # Não interromper o processamento por erro de afastamento
    
    def _create_employee_from_csv(self, row: pd.Series, matricula: str, division_code: str) -> Employee:
        """Cria employee temporário a partir do CSV"""
        # Determinar CPF e absolute_id para consistência única
        cpf_str = row.get('CPF', row.get('CPF_FUNC', None)) or ''
        cpf_normalized = normalize_cpf(cpf_str) if cpf_str else None
        absolute_id = self._compute_absolute_id(division_code, matricula, cpf_normalized)

        employee = Employee(
            unique_id=matricula,
            absolute_id=absolute_id,
            cpf=cpf_normalized or None,
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
        Extrai proventos do CSV - incluindo férias e 13º salário
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
        
        # ============ FÉRIAS ============
        # Valor base de férias
        ferias_fields = {
            'FERIAS_VALOR_BASE': 'Horas Férias Diurnas',
            'FERIAS_VALOR_PROPORCIONAIS': 'Horas Férias Proporc.Diurnas',
            'FERIAS_VALOR_VENCIDAS': 'Horas Férias Vencidas Diurnas',
            'FERIAS_VALOR_APP': 'Horas Férias Proporcionais Diurnas API',
            'FERIAS_DIFERENCA': 'Diferença de Férias',
            # 1/3 de férias
            'FERIAS_ABONO_1_3': '1/3 Sobre Férias',
            'FERIAS_ABONO_1_3_PROPORCIONAIS': '1/3 S/Férias Proporcionais',
            'FERIAS_ABONO_1_3_VENCIDAS': '1/3 S/Férias Vencidas',
            'FERIAS_ABONO_1_3_APP': '1/3 S/Férias Proporcionais API',
            # Médias sobre férias
            'FERIAS_MEDIA_EVENTOS': 'Med.Eve.Var.S/Férias',
            'FERIAS_MEDIA_EVENTOS_PROPORC': 'Med.Eve.Var.S/Férias Proporc.',
            'FERIAS_MEDIA_EVENTOS_VENCIDAS': 'Med.Eve.Var.S/Férias Vencidas',
            'FERIAS_MEDIA_EVENTOS_APP': 'Med.Eve.Var.Férias Prop.API',
            'FERIAS_MEDIA_HE': 'Med.Hrs.Ext.S/Férias Diurnas',
            'FERIAS_MEDIA_HE_NOTURNAS': 'Med.Hrs.Ext.S/Férias Noturnas',
            'FERIAS_MEDIA_HE_PROPORC': 'Med.Hrs.Ext.Diurnas S/Ferias Proporc.',
            'FERIAS_MEDIA_HE_VENCIDAS': 'Med.Hrs.Ext.Diurnas S/Férias Vencidas',
            'FERIAS_MEDIA_HE_APP': 'Med.Hrs.Ext.Diurnas Férias Prop.API',
            # Transferência e adicional noturno sobre férias
            'FERIAS_TRANSFERENCIA_FILIAL': 'Transf.Filial S/Férias',
            'FERIAS_ADICIONAL_NOTURNO': 'Adicional Noturno S/Férias',
            # Descontos de férias (adiantamentos)
            'FERIAS_ADIANTAMENTO_PAGO': 'Desconto Adiantamento Férias',
        }
        
        for json_field, csv_field in ferias_fields.items():
            val = self._get_number(row, [csv_field])
            if val > 0:
                earnings[json_field] = val
        
        # ============ 13º SALÁRIO ============
        decimo_terceiro_fields = {
            '13_SALARIO_INDENIZADO': '13o Salário Indenizado',
            '13_SALARIO_PROPORCIONAL': '13o Salário Proporcional',
            '13_SALARIO_PROPORCIONAL_APP': '13o Salário Proporcional APP',
            # Médias sobre 13º
            '13_MEDIA_EVENTOS_INDENIZADO': 'Med.Eve.Var. 13o Sal.Ind.',
            '13_MEDIA_EVENTOS_PROPORCIONAL': 'Med.Eve.Var.13o Sal.Prop.',
            '13_MEDIA_HE_INDENIZADO': 'Med.Hrs.Ext.Diurnas 13o Sal.Ind.',
            '13_MEDIA_HE_PROPORCIONAL': 'Med.Hrs.Ext.Diurnas 13o Sal.Prop.',
        }
        
        for json_field, csv_field in decimo_terceiro_fields.items():
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
