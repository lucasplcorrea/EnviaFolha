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
from app.models.system_log import LogLevel, LogCategory
from app.services.logging_service import LoggingService


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
        """
        Parse arquivo Excel (.xlsx ou .xls) para lista de dicionários.
        Usa openpyxl para .xlsx e xlrd para .xls
        
        IMPORTANTE: Força campos críticos como string para preservar zeros à esquerda
        """
        if not PANDAS_AVAILABLE:
            raise RuntimeError('pandas is required to parse xlsx files')
        
        # Definir dtype para forçar campos como string e preservar zeros à esquerda
        dtype_mapping = {
            'unique_id': str,
            'codigo_unificado': str,
            'registration_number': str,
            'cpf': str,
            'phone': str,
            'phone_number': str,
            'telefone': str
        }
        
        try:
            # Tentar com openpyxl primeiro (para .xlsx)
            df = pd.read_excel(
                io.BytesIO(file_bytes), 
                sheet_name=sheet_name, 
                engine='openpyxl',
                dtype=dtype_mapping,  # Força tipos específicos
                keep_default_na=False  # Não converte strings vazias em NaN
            )
            # Converter todas as colunas para string para garantir
            for col in df.columns:
                if col.lower() in ['unique_id', 'codigo_unificado', 'registration_number', 'cpf', 'phone', 'phone_number', 'telefone']:
                    df[col] = df[col].astype(str)
            
            return df.fillna('').to_dict(orient='records')
        except Exception as e:
            print(f"⚠️ Erro com openpyxl: {e}")
            try:
                # Fallback para xlrd (para .xls antigo)
                df = pd.read_excel(
                    io.BytesIO(file_bytes), 
                    sheet_name=sheet_name, 
                    engine='xlrd',
                    dtype=dtype_mapping,
                    keep_default_na=False
                )
                # Converter colunas para string
                for col in df.columns:
                    if col.lower() in ['unique_id', 'codigo_unificado', 'registration_number', 'cpf', 'phone', 'phone_number', 'telefone']:
                        df[col] = df[col].astype(str)
                
                return df.fillna('').to_dict(orient='records')
            except Exception as e2:
                print(f"❌ Erro com xlrd: {e2}")
                raise RuntimeError(f'Não foi possível ler o arquivo Excel. Erro: {str(e)}')

    def import_employees(self, rows: List[Dict]) -> Dict:
        """
        Importa linhas mapeando campos comuns para Employee. 
        Retorna summary com detalhes de criados, atualizados e erros.
        """
        created = 0
        updated = 0
        errors = []
        created_list = []
        updated_list = []

        # Log início da importação
        self.logger.log_import(
            f'Iniciando importação de {len(rows)} colaboradores',
            details={'total_rows': len(rows)},
            user_id=self.user_id,
            username=self.username,
            ip_address=self.ip_address,
            user_agent=self.user_agent,
            request_method=self.request_method,
            request_path=self.request_path
        )

        for i, row in enumerate(rows, start=1):
            try:
                # Validar campos obrigatórios
                unique_id = row.get('unique_id') or row.get('codigo_unificado') or row.get('registration_number')
                
                # Limpar e converter unique_id para string, preservando zeros à esquerda
                if unique_id:
                    unique_id = str(unique_id).strip()
                    # Remover ".0" que pandas pode adicionar
                    if unique_id.endswith('.0'):
                        unique_id = unique_id[:-2]
                    # Se estiver vazio ou for "nan", considerar como None
                    if unique_id.lower() in ('', 'nan', 'none'):
                        unique_id = None
                
                if not unique_id:
                    error_msg = 'Campo obrigatório "unique_id" ausente'
                    errors.append({'row': i, 'error': error_msg, 'data': row})
                    continue

                full_name = row.get('full_name') or row.get('name') or row.get('nome')
                if not full_name:
                    error_msg = 'Campo obrigatório "full_name" ausente'
                    errors.append({'row': i, 'error': error_msg, 'data': row})
                    continue

                cpf = row.get('cpf')
                # Limpar e converter CPF para string
                if cpf:
                    cpf = str(cpf).strip()
                    if cpf.endswith('.0'):
                        cpf = cpf[:-2]
                    if cpf.lower() in ('', 'nan', 'none'):
                        cpf = None
                
                if not cpf:
                    error_msg = 'Campo obrigatório "cpf" ausente'
                    errors.append({'row': i, 'error': error_msg, 'data': row})
                    continue

                phone = row.get('phone_number') or row.get('phone') or row.get('telefone')
                # Limpar e converter phone para string
                if phone:
                    phone = str(phone).strip()
                    if phone.endswith('.0'):
                        phone = phone[:-2]
                    if phone.lower() in ('', 'nan', 'none'):
                        phone = None
                
                if not phone:
                    error_msg = 'Campo obrigatório "phone_number" ausente'
                    errors.append({'row': i, 'error': error_msg, 'data': row})
                    continue

                # Verificar se colaborador já existe
                employee = self.db.query(Employee).filter(Employee.unique_id == str(unique_id)).first()

                # Preparar dados para inserção/atualização
                data = {
                    'unique_id': str(unique_id),
                    'name': full_name,  # Campo no banco é 'name', não 'full_name'
                    'cpf': str(cpf),
                    'phone': str(phone),  # Campo no banco é 'phone', não 'phone_number'
                    'email': row.get('email') or None,
                    'department': row.get('department') or row.get('setor') or None,
                    'position': row.get('position') or row.get('cargo') or None,
                    'birth_date': self._parse_date(row.get('birth_date') or row.get('data_nascimento')),
                    'sex': row.get('sex') or row.get('sexo') or None,
                    'marital_status': row.get('marital_status') or row.get('estado_civil') or None,
                    'admission_date': self._parse_date(row.get('admission_date') or row.get('data_admissao')),
                    'contract_type': row.get('contract_type') or row.get('tipo_contrato') or None,
                    'is_active': True,  # Sempre ativo na importação, ajustar manualmente se necessário
                    'status_reason': row.get('status_reason') or row.get('motivo_status') or None
                }

                if employee:
                    # ATUALIZAR colaborador existente
                    old_data = {k: getattr(employee, k) for k in data.keys()}
                    
                    for k, v in data.items():
                        if v is not None:  # Só atualizar se valor fornecido
                            setattr(employee, k, v)
                    
                    self.db.commit()
                    updated += 1
                    updated_list.append({
                        'unique_id': unique_id,
                        'name': full_name,
                        'row': i
                    })
                    
                    # Log da atualização
                    self.logger.log_employee_action(
                        f'Colaborador atualizado via importação: {full_name}',
                        employee_id=str(employee.id),
                        user_id=self.user_id,
                        username=self.username,
                        details={
                            'unique_id': unique_id,
                            'old_data': old_data,
                            'new_data': data,
                            'import_row': i
                        }
                    )
                else:
                    # CRIAR novo colaborador
                    # Usar user_id se fornecido, senão usar None (permitido agora)
                    new = Employee(**data, created_by=self.user_id)
                    self.db.add(new)
                    self.db.commit()
                    self.db.refresh(new)
                    
                    created += 1
                    created_list.append({
                        'unique_id': unique_id,
                        'name': full_name,
                        'row': i
                    })
                    
                    # Log da criação
                    self.logger.log_employee_action(
                        f'Colaborador criado via importação: {full_name}',
                        employee_id=str(new.id),
                        user_id=self.user_id,
                        username=self.username,
                        details={
                            'unique_id': unique_id,
                            'data': data,
                            'import_row': i
                        }
                    )

            except Exception as e:
                self.db.rollback()
                error_msg = str(e)
                errors.append({'row': i, 'error': error_msg, 'data': row})
                
                # Log do erro
                self.logger.error(
                    LogCategory.IMPORT,
                    f'Erro ao importar linha {i}: {error_msg}',
                    details={'row': i, 'error': error_msg, 'data': row},
                    user_id=self.user_id,
                    username=self.username
                )

        # Log final da importação
        self.logger.log_import(
            f'Importação concluída: {created} criados, {updated} atualizados, {len(errors)} erros',
            details={
                'created': created,
                'updated': updated,
                'errors_count': len(errors),
                'created_list': created_list,
                'updated_list': updated_list,
                'errors': errors[:10]  # Primeiros 10 erros apenas
            },
            user_id=self.user_id,
            username=self.username,
            ip_address=self.ip_address,
            user_agent=self.user_agent,
            request_method=self.request_method,
            request_path=self.request_path
        )

        return {
            'created': created,
            'updated': updated,
            'errors': errors,
            'created_list': created_list,
            'updated_list': updated_list
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
        # fallback: try pandas parse if available
        if PANDAS_AVAILABLE:
            try:
                import pandas as pd
                return pd.to_datetime(value).date()
            except Exception:
                return None
        return None
