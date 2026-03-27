import csv
import io
import re
from typing import List, Dict, Optional
from datetime import datetime

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except Exception:
    PANDAS_AVAILABLE = False

from app.models.employee import Employee
from app.models.system_log import LogLevel, LogCategory
from app.services.logging_service import LoggingService


def _clean_str(value) -> Optional[str]:
    """Limpa valor para string, retornando None se vazio/inválido."""
    if not value:
        return None
    s = str(value).strip()
    if s.endswith('.0'):
        s = s[:-2]
    if s.lower() in ('', 'nan', 'none'):
        return None
    return s


def _only_digits(value: str) -> str:
    """Retorna apenas os dígitos de uma string."""
    return re.sub(r'\D', '', value or '')


def _build_absolute_id(company_prefix: str, matricula: str, cpf: str) -> Optional[str]:
    """
    Constrói o absolute_id único e definitivo do colaborador.
    Fórmula: CompanyPrefix (padded 4) + Matricula (padded 5) + CPF (11 dígitos)
    Exemplo: 0059 + 00571 + 04775016997 = "005900571" + "04775016997" → "00590057104775016997"
    """
    prefix = _only_digits(company_prefix or '').zfill(4)
    mat = _only_digits(matricula or '').zfill(5)
    cpf_digits = _only_digits(cpf or '')

    if not prefix or not mat or len(cpf_digits) != 11:
        return None

    return f"{prefix}{mat}{cpf_digits}"


class DataImportService:
    """Serviço para importar CSV/XLSX com rastreabilidade completa."""

    def __init__(
        self,
        db_session,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_method: Optional[str] = None,
        request_path: Optional[str] = None
    ):
        self.db = db_session
        self.logger = LoggingService(db_session)
        self.user_id = user_id
        self.username = username
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.request_method = request_method
        self.request_path = request_path

    def parse_csv(self, file_bytes: bytes, encoding: str = 'utf-8') -> List[Dict]:
        text = file_bytes.decode(encoding)
        reader = csv.DictReader(io.StringIO(text))
        return [row for row in reader]

    def parse_xlsx(self, file_bytes: bytes, sheet_name: Optional[str] = 0) -> List[Dict]:
        """Parse arquivo Excel (.xlsx ou .xls) para lista de dicionários."""
        if not PANDAS_AVAILABLE:
            raise RuntimeError('pandas é necessário para ler arquivos xlsx')

        str_cols = ['company_code', 'matricula', 'cpf', 'phone', 'phone_number',
                    'telefone', 'unique_id', 'codigo_unificado', 'registration_number']

        dtype_mapping = {col: str for col in str_cols}

        try:
            df = pd.read_excel(
                io.BytesIO(file_bytes), sheet_name=sheet_name,
                engine='openpyxl', dtype=dtype_mapping, keep_default_na=False
            )
            for col in df.columns:
                if col.lower() in str_cols:
                    df[col] = df[col].astype(str)
            return df.fillna('').to_dict(orient='records')
        except Exception as e:
            print(f"⚠️ Erro com openpyxl: {e}")
            try:
                df = pd.read_excel(
                    io.BytesIO(file_bytes), sheet_name=sheet_name,
                    engine='xlrd', dtype=dtype_mapping, keep_default_na=False
                )
                for col in df.columns:
                    if col.lower() in str_cols:
                        df[col] = df[col].astype(str)
                return df.fillna('').to_dict(orient='records')
            except Exception as e2:
                raise RuntimeError(f'Não foi possível ler o arquivo Excel. Erro: {str(e)}')

    def import_employees(self, rows: List[Dict]) -> Dict:
        """
        Importa colaboradores com geração automática do absolute_id.
        Campos obrigatórios no xlsx: nome, cpf, matricula, company_code
        """
        created = 0
        updated = 0
        errors = []
        created_list = []
        updated_list = []

        self.logger.log_import(
            f'Iniciando importação de {len(rows)} colaboradores',
            details={'total_rows': len(rows)},
            user_id=self.user_id, username=self.username,
            ip_address=self.ip_address, user_agent=self.user_agent,
            request_method=self.request_method, request_path=self.request_path
        )

        for i, row in enumerate(rows, start=1):
            try:
                # ── 1. Campos obrigatórios ──────────────────────────────────
                full_name = _clean_str(row.get('nome') or row.get('name') or row.get('full_name'))
                if not full_name:
                    errors.append({'row': i, 'error': 'Campo obrigatório "nome" ausente', 'data': row})
                    continue

                cpf_raw = _clean_str(row.get('cpf'))
                if not cpf_raw or len(_only_digits(cpf_raw)) != 11:
                    errors.append({'row': i, 'error': 'Campo obrigatório "cpf" ausente ou inválido (11 dígitos)', 'data': row})
                    continue

                matricula = _clean_str(row.get('matricula') or row.get('registration_number') or row.get('unique_id'))
                if not matricula:
                    errors.append({'row': i, 'error': 'Campo obrigatório "matricula" ausente', 'data': row})
                    continue

                company_code = _clean_str(row.get('company_code') or row.get('codigo_empresa') or row.get('empresa'))
                if not company_code:
                    errors.append({'row': i, 'error': 'Campo obrigatório "company_code" ausente (ex: 0059 ou 0060)', 'data': row})
                    continue

                # ── 2. Gerar absolute_id automaticamente ────────────────────
                absolute_id = _build_absolute_id(company_code, matricula, cpf_raw)
                if not absolute_id:
                    errors.append({'row': i, 'error': f'Não foi possível gerar absolute_id (CPF deve ter 11 dígitos)', 'data': row})
                    continue

                # unique_id legado: company_code (4 dígitos) + matricula (5 dígitos)
                prefix_4 = _only_digits(company_code).zfill(4)
                mat_5 = _only_digits(matricula).zfill(5)
                unique_id = f"{prefix_4}{mat_5}"

                # ── 3. Campos opcionais ─────────────────────────────────────
                phone = _clean_str(row.get('telefone') or row.get('phone') or row.get('phone_number'))
                email = _clean_str(row.get('email'))
                department = _clean_str(row.get('departamento') or row.get('department'))
                position = _clean_str(row.get('cargo') or row.get('position'))
                sex = _clean_str(row.get('sexo') or row.get('sex'))
                marital_status = _clean_str(row.get('estado_civil') or row.get('marital_status'))
                contract_type = _clean_str(row.get('tipo_contrato') or row.get('contract_type'))
                status_reason = _clean_str(row.get('situacao') or row.get('status_reason'))
                birth_date = self._parse_date(row.get('data_nascimento') or row.get('birth_date'))
                admission_date = self._parse_date(row.get('data_admissao') or row.get('admission_date'))

                # ── 4. Buscar pelo absolute_id (chave definitiva) ───────────
                employee = self.db.query(Employee).filter(
                    Employee.absolute_id == absolute_id
                ).first()

                data = {
                    'absolute_id': absolute_id,
                    'unique_id': unique_id,
                    'name': full_name,
                    'cpf': cpf_raw,
                    'phone': phone,
                    'email': email,
                    'department': department,
                    'position': position,
                    'company_code': prefix_4,
                    'registration_number': mat_5,
                    'sex': sex,
                    'marital_status': marital_status,
                    'contract_type': contract_type,
                    'status_reason': status_reason,
                    'birth_date': birth_date,
                    'admission_date': admission_date,
                    'is_active': True,
                }

                if employee:
                    # Atualizar existente
                    for k, v in data.items():
                        if v is not None:
                            setattr(employee, k, v)
                    self.db.commit()
                    updated += 1
                    updated_list.append({'absolute_id': absolute_id, 'name': full_name, 'row': i})
                    self.logger.log_employee_action(
                        f'Colaborador atualizado via importação: {full_name}',
                        employee_id=str(employee.id), user_id=self.user_id, username=self.username,
                        details={'absolute_id': absolute_id, 'new_data': data, 'import_row': i}
                    )
                else:
                    # Criar novo
                    new = Employee(**data, created_by=self.user_id)
                    self.db.add(new)
                    self.db.commit()
                    self.db.refresh(new)
                    created += 1
                    created_list.append({'absolute_id': absolute_id, 'name': full_name, 'row': i})
                    self.logger.log_employee_action(
                        f'Colaborador criado via importação: {full_name}',
                        employee_id=str(new.id), user_id=self.user_id, username=self.username,
                        details={'absolute_id': absolute_id, 'data': data, 'import_row': i}
                    )

            except Exception as e:
                self.db.rollback()
                errors.append({'row': i, 'error': str(e), 'data': row})
                self.logger.error(
                    LogCategory.IMPORT, f'Erro ao importar linha {i}: {e}',
                    details={'row': i, 'error': str(e)},
                    user_id=self.user_id, username=self.username
                )

        self.logger.log_import(
            f'Importação concluída: {created} criados, {updated} atualizados, {len(errors)} erros',
            details={'created': created, 'updated': updated, 'errors_count': len(errors),
                     'created_list': created_list, 'updated_list': updated_list, 'errors': errors[:10]},
            user_id=self.user_id, username=self.username,
            ip_address=self.ip_address, user_agent=self.user_agent,
            request_method=self.request_method, request_path=self.request_path
        )

        return {
            'created': created, 'updated': updated, 'errors': errors,
            'created_list': created_list, 'updated_list': updated_list
        }

    def _parse_date(self, value):
        if not value:
            return None
        if isinstance(value, datetime):
            return value.date()
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d'):
            try:
                return datetime.strptime(str(value), fmt).date()
            except Exception:
                continue
        if PANDAS_AVAILABLE:
            try:
                import pandas as pd
                return pd.to_datetime(value).date()
            except Exception:
                return None
        return None
