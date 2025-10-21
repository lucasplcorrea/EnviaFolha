import csv
import io
from typing import List, Dict, Optional
from datetime import datetime

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except Exception:
    PANDAS_AVAILABLE = False

from app.models.employee import Employee


class DataImportService:
    """Serviço simples para importar CSV/XLSX e mapear campos para modelos."""

    def __init__(self, db_session):
        self.db = db_session

    def parse_csv(self, file_bytes: bytes, encoding: str = 'utf-8') -> List[Dict]:
        text = file_bytes.decode(encoding)
        reader = csv.DictReader(io.StringIO(text))
        return [row for row in reader]

    def parse_xlsx(self, file_bytes: bytes, sheet_name: Optional[str] = 0) -> List[Dict]:
        if not PANDAS_AVAILABLE:
            raise RuntimeError('pandas is required to parse xlsx files')
        df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name)
        return df.fillna('').to_dict(orient='records')

    def import_employees(self, rows: List[Dict]) -> Dict:
        """Importa linhas mapeando campos comuns para Employee. Retorna summary."""
        created = 0
        updated = 0
        errors = []

        for i, row in enumerate(rows, start=1):
            try:
                unique_id = row.get('unique_id') or row.get('codigo_unificado') or row.get('registration_number')
                if not unique_id:
                    errors.append({'row': i, 'error': 'missing unique_id'})
                    continue

                employee = self.db.query(Employee).filter(Employee.unique_id == unique_id).first()

                data = {
                    'unique_id': unique_id,
                    'name': row.get('name') or row.get('nome'),
                    'cpf': row.get('cpf'),
                    'phone': row.get('phone') or row.get('telefone'),
                    'email': row.get('email'),
                    'department': row.get('department') or row.get('setor'),
                    'position': row.get('position') or row.get('cargo'),
                    'company_code': row.get('company') or row.get('empresa'),
                    'registration_number': row.get('registration') or row.get('matricula'),
                    'birth_date': self._parse_date(row.get('birth_date') or row.get('data_nascimento')),
                    'sex': row.get('sex') or row.get('sexo'),
                    'marital_status': row.get('marital_status') or row.get('estado_civil'),
                    'admission_date': self._parse_date(row.get('admission_date') or row.get('data_admissao')),
                    'contract_type': row.get('contract_type') or row.get('tipo_contrato'),
                    'is_active': True if (row.get('status','').lower() in ['ativo','true','1','yes']) else False,
                    'status_reason': row.get('status_reason') or row.get('motivo_status')
                }

                if employee:
                    for k, v in data.items():
                        if v is not None:
                            setattr(employee, k, v)
                    self.db.commit()
                    updated += 1
                else:
                    new = Employee(**data, created_by=1)
                    self.db.add(new)
                    self.db.commit()
                    created += 1

            except Exception as e:
                self.db.rollback()
                errors.append({'row': i, 'error': str(e)})

        return {'created': created, 'updated': updated, 'errors': errors}

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
        # fallback: try pandas parse if available
        if PANDAS_AVAILABLE:
            try:
                import pandas as pd
                return pd.to_datetime(value).date()
            except Exception:
                return None
        return None
