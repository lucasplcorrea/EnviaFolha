"""
Serviço para processar arquivos XLSX de Cartão Ponto
"""
import logging
import openpyxl
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.employee import Employee
from app.models.timecard import TimecardPeriod, TimecardData, TimecardProcessingLog

logger = logging.getLogger(__name__)


class TimecardXLSXProcessor:
    """Processador de arquivos XLSX de cartão ponto"""
    
    REQUIRED_COLUMNS = ['Nº Folha', 'Nome']  # Colunas mínimas necessárias
    
    # Mapeamento de nomes de colunas
    COLUMN_MAPPING = {
        'Nº Folha': 'employee_number',
        'Nome': 'employee_name',
        'Normais': 'normal_hours',
        'Ex50%': 'overtime_50',
        'Ex100%': 'overtime_100',
        'EN50%': 'night_overtime_50',
        'EN100%': 'night_overtime_100',
        'Not.': 'night_hours',
        'Faltas': 'absences',
        'DSR.Deb': 'dsr_debit',
        'Abono2': 'bonus_hours'
    }
    
    def __init__(self, db: Session, user_id: Optional[int] = None):
        self.db = db
        self.user_id = user_id
        self.warnings = []
        self.errors = []
    
    def process_xlsx_file(
        self,
        file_path: str,
        year: int,
        month: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        Processa arquivo XLSX de cartão ponto
        
        Args:
            file_path: Caminho do arquivo XLSX
            year: Ano do período
            month: Mês do período
            start_date: Data início (opcional)
            end_date: Data fim (opcional)
        
        Returns:
            Dict com resultado do processamento
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"Iniciando processamento de cartão ponto: {file_path}")
            
            # Carregar workbook
            wb = openpyxl.load_workbook(file_path, data_only=True)
            sheet = wb.active
            
            # Encontrar linha de headers
            header_row = self._find_header_row(sheet)
            if not header_row:
                return {
                    'success': False,
                    'error': 'Não foi possível encontrar os headers das colunas'
                }
            
            # Ler e validar headers
            headers = self._read_headers(sheet, header_row)
            validation_result = self._validate_headers(headers)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': validation_result['error']
                }
            
            # Criar ou obter período
            period = self._get_or_create_period(
                year, month, start_date, end_date, file_path
            )
            
            # Processar linhas de dados
            results = self._process_data_rows(
                sheet, headers, header_row, period, file_path
            )
            
            # Criar log de processamento
            processing_time = (datetime.now() - start_time).total_seconds()
            self._create_processing_log(
                period, file_path, results, processing_time
            )
            
            # Commit final
            self.db.commit()
            
            wb.close()
            
            logger.info(f"Processamento concluído: {results['processed_rows']} linhas processadas")
            
            return {
                'success': True,
                'period_id': period.id,
                'period_name': period.period_name,
                'total_rows': results['total_rows'],
                'processed_rows': results['processed_rows'],
                'error_rows': results['error_rows'],
                'warnings': self.warnings,
                'errors': self.errors,
                'processing_time': processing_time
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao processar XLSX de cartão ponto: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Erro ao processar arquivo: {str(e)}'
            }
    
    def _find_header_row(self, sheet) -> Optional[int]:
        """Retorna linha 1 (arquivo tratado tem headers na primeira linha)"""
        logger.info("Usando headers da linha 1 (arquivo tratado)")
        return 1
    
    def _read_headers(self, sheet, header_row: int) -> List[str]:
        """Lê os headers da linha especificada"""
        headers = []
        for col in range(1, sheet.max_column + 1):
            cell_value = sheet.cell(header_row, col).value
            headers.append(str(cell_value).strip() if cell_value else None)
        return headers
    
    def _validate_headers(self, headers: List[str]) -> Dict:
        """Valida se as colunas necessárias estão presentes"""
        for required_col in self.REQUIRED_COLUMNS:
            if required_col not in headers:
                return {
                    'valid': False,
                    'error': f'Coluna obrigatória não encontrada: {required_col}'
                }
        return {'valid': True}
    
    def _get_or_create_period(
        self,
        year: int,
        month: int,
        start_date: Optional[str],
        end_date: Optional[str],
        filename: str
    ) -> TimecardPeriod:
        """Cria ou retorna período existente"""
        try:
            # Buscar período existente
            period = self.db.query(TimecardPeriod).filter(
                TimecardPeriod.year == year,
                TimecardPeriod.month == month
            ).first()
            
            if period:
                logger.info(f"Período existente encontrado: {period.period_name}")
                return period
            
            # Criar novo período
            month_names = [
                'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
            ]
            period_name = f"{month_names[month-1]} {year}"
            
            # Converter datas se fornecidas
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None
            
            period = TimecardPeriod(
                year=year,
                month=month,
                period_name=period_name,
                start_date=start_date_obj,
                end_date=end_date_obj,
                description=f"Importado de {filename}"
            )
            
            self.db.add(period)
            self.db.flush()  # Get ID without committing
            
            logger.info(f"Novo período criado: {period_name}")
            return period
            
        except Exception as e:
            logger.error(f"Erro ao criar período: {e}")
            raise
    
    def _process_data_rows(
        self,
        sheet,
        headers: List[str],
        header_row: int,
        period: TimecardPeriod,
        filename: str
    ) -> Dict:
        """Processa todas as linhas de dados"""
        total_rows = 0
        processed_rows = 0
        error_rows = 0
        
        # Mapear índices das colunas
        col_indices = {}
        for i, header in enumerate(headers):
            if header in self.COLUMN_MAPPING:
                col_indices[self.COLUMN_MAPPING[header]] = i + 1
        
        # Processar linhas (arquivo tratado não tem linha de totais)
        for row_idx in range(header_row + 1, sheet.max_row + 1):
            # Verificar se é linha de dados válida
            employee_number = sheet.cell(row_idx, col_indices.get('employee_number', 1)).value
            
            if not employee_number or not str(employee_number).strip():
                continue  # Linha vazia
            
            total_rows += 1
            
            try:
                # Processar linha
                success = self._process_timecard_row(
                    sheet, row_idx, col_indices, period, filename
                )
                
                if success:
                    processed_rows += 1
                else:
                    error_rows += 1
                    
            except Exception as e:
                error_rows += 1
                error_msg = f"Linha {row_idx}: {str(e)}"
                self.errors.append(error_msg)
                logger.error(error_msg)
        
        return {
            'total_rows': total_rows,
            'processed_rows': processed_rows,
            'error_rows': error_rows
        }
    
    def _process_timecard_row(
        self,
        sheet,
        row_idx: int,
        col_indices: Dict,
        period: TimecardPeriod,
        filename: str
    ) -> bool:
        """Processa uma linha de dados de cartão ponto"""
        try:
            # Ler matrícula (arquivo tratado tem apenas matrículas válidas)
            employee_number_raw = sheet.cell(row_idx, col_indices.get('employee_number', 1)).value
            employee_number = str(employee_number_raw).strip().upper()
            
            # Validação básica de matrícula
            employee_number_clean = employee_number.replace('E', '').strip()
            if not employee_number_clean.isdigit():
                logger.warning(f"Linha {row_idx}: Matrícula inválida ({employee_number})")
                return False
            
            # Identificar empresa pela presença de "E" na matrícula
            if employee_number.endswith('E'):
                company = '0060'  # Empreendimentos
            else:
                company = '0059'  # Infraestrutura
            
            # Ler nome
            employee_name_cell = sheet.cell(row_idx, col_indices.get('employee_name', 2)).value
            employee_name = str(employee_name_cell).strip() if employee_name_cell else ""
            
            # Tentar encontrar employee no banco (apenas por unique_id, sem filtrar por empresa)
            employee = self.db.query(Employee).filter(
                Employee.unique_id == employee_number_clean
            ).first()
            
            if not employee:
                # Tentar por nome se não encontrou por matrícula
                employee = self.db.query(Employee).filter(
                    Employee.name.ilike(f"%{employee_name}%")
                ).first()
            
            employee_id = employee.id if employee else None
            
            if not employee:
                warning = f"Linha {row_idx}: Colaborador '{employee_name}' (matrícula {employee_number}) não encontrado no sistema"
                self.warnings.append(warning)
                logger.warning(warning)
            
            # Ler valores de horas (converter timedelta para horas decimais)
            normal_hours = self._convert_to_hours(sheet.cell(row_idx, col_indices.get('normal_hours', 3)).value)
            overtime_50 = self._convert_to_hours(sheet.cell(row_idx, col_indices.get('overtime_50', 4)).value)
            overtime_100 = self._convert_to_hours(sheet.cell(row_idx, col_indices.get('overtime_100', 5)).value)
            night_overtime_50 = self._convert_to_hours(sheet.cell(row_idx, col_indices.get('night_overtime_50', 6)).value)
            night_overtime_100 = self._convert_to_hours(sheet.cell(row_idx, col_indices.get('night_overtime_100', 7)).value)
            night_hours = self._convert_to_hours(sheet.cell(row_idx, col_indices.get('night_hours', 8)).value)
            absences = self._convert_to_hours(sheet.cell(row_idx, col_indices.get('absences', 9)).value)
            dsr_debit = self._convert_to_hours(sheet.cell(row_idx, col_indices.get('dsr_debit', 10)).value)
            bonus_hours = self._convert_to_hours(sheet.cell(row_idx, col_indices.get('bonus_hours', 11)).value)
            
            # Verificar se já existe registro para este colaborador neste período
            existing = self.db.query(TimecardData).filter(
                TimecardData.period_id == period.id,
                TimecardData.employee_number == employee_number
            ).first()
            
            if existing:
                # Atualizar registro existente
                existing.employee_id = employee_id
                existing.employee_name = employee_name
                existing.company = company
                existing.normal_hours = normal_hours
                existing.overtime_50 = overtime_50
                existing.overtime_100 = overtime_100
                existing.night_overtime_50 = night_overtime_50
                existing.night_overtime_100 = night_overtime_100
                existing.night_hours = night_hours
                existing.absences = absences
                existing.dsr_debit = dsr_debit
                existing.bonus_hours = bonus_hours
                existing.upload_filename = filename
                existing.processed_by = self.user_id
                
                logger.debug(f"Registro atualizado: {employee_name}")
            else:
                # Criar novo registro
                timecard_data = TimecardData(
                    period_id=period.id,
                    employee_id=employee_id,
                    employee_number=employee_number,
                    employee_name=employee_name,
                    company=company,
                    normal_hours=normal_hours,
                    overtime_50=overtime_50,
                    overtime_100=overtime_100,
                    night_overtime_50=night_overtime_50,
                    night_overtime_100=night_overtime_100,
                    night_hours=night_hours,
                    absences=absences,
                    dsr_debit=dsr_debit,
                    bonus_hours=bonus_hours,
                    upload_filename=filename,
                    processed_by=self.user_id
                )
                
                self.db.add(timecard_data)
                logger.debug(f"Novo registro criado: {employee_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao processar linha {row_idx}: {e}")
            raise
    
    def _convert_to_hours(self, value) -> Decimal:
        """
        Converte valor para horas decimais
        
        Suporta:
        - timedelta objects (ex: timedelta(days=3, seconds=58260))
        - Números decimais do Excel (dias como fração)
        - Strings de tempo (ex: "3 days, 16:11:00" ou "1:21:00" ou "3153:13")
        """
        if value is None or value == "":
            return Decimal('0')
        
        # Se for timedelta do Python
        if isinstance(value, timedelta):
            total_seconds = value.total_seconds()
            # Converter para horas com precisão de 4 casas decimais para preservar minutos
            # Exemplo: 2737:26 = 2737.4333 horas (não arredondar para 2 casas)
            hours = total_seconds / 3600
            return Decimal(str(round(hours, 4)))
        
        # Se for número (int/float/Decimal) - Excel retorna dias como decimal
        if isinstance(value, (int, float, Decimal)):
            # Excel armazena tempo como fração de dia (ex: 0.5 = 12 horas)
            # Se for menor que 1, provavelmente é fração de dia
            num_value = float(value)
            if 0 < num_value < 1:
                # Converter dias para horas
                hours = num_value * 24
                return Decimal(str(round(hours, 2)))
            else:
                # Se for >= 1, pode ser dias (pouco provável) ou já estar em horas
                # Para segurança, assumir que valores grandes já estão em horas
                return Decimal(str(round(num_value, 2)))
        
        # Se for string, tentar parsear
        if isinstance(value, str):
            value = value.strip()
            
            if not value:
                return Decimal('0')
            
            try:
                # Tentar converter diretamente para número
                num = float(value)
                # Se for decimal pequeno, converter de dias para horas
                if 0 < num < 1:
                    return Decimal(str(round(num * 24, 2)))
                return Decimal(str(round(num, 2)))
            except:
                pass
            
            # Parsear formato "HH:MM:SS" ou "HHHH:MM:SS" (formato de horas totais)
            if ':' in value and 'day' not in value.lower():
                try:
                    time_parts = value.split(':')
                    hours = int(time_parts[0])
                    minutes = int(time_parts[1]) if len(time_parts) > 1 else 0
                    seconds = int(time_parts[2]) if len(time_parts) > 2 else 0
                    
                    total_hours = hours + (minutes / 60) + (seconds / 3600)
                    return Decimal(str(round(total_hours, 2)))
                except:
                    pass
            
            # Parsear formato "X days, HH:MM:SS"
            if 'day' in value.lower():
                try:
                    total_hours = 0
                    
                    # Extrair dias
                    parts = value.lower().split('day')
                    days = int(parts[0].strip())
                    total_hours += days * 24
                    
                    # Extrair horas:minutos:segundos da parte restante
                    time_str = parts[1].replace('s,', '').replace(',', '').strip()
                    if ':' in time_str:
                        time_parts = time_str.split(':')
                        total_hours += int(time_parts[0])
                        total_hours += int(time_parts[1]) / 60 if len(time_parts) > 1 else 0
                        total_hours += int(time_parts[2]) / 3600 if len(time_parts) > 2 else 0
                    
                    return Decimal(str(round(total_hours, 2)))
                except:
                    pass
        
        return Decimal('0')
    
    def _create_processing_log(
        self,
        period: TimecardPeriod,
        filename: str,
        results: Dict,
        processing_time: float
    ):
        """Cria log de processamento"""
        try:
            import os
            
            status = 'completed' if results['error_rows'] == 0 else 'partial'
            
            log = TimecardProcessingLog(
                period_id=period.id,
                filename=os.path.basename(filename),
                file_size=os.path.getsize(filename) if os.path.exists(filename) else None,
                total_rows=results['total_rows'],
                processed_rows=results['processed_rows'],
                error_rows=results['error_rows'],
                status=status,
                processing_summary={
                    'warnings_count': len(self.warnings),
                    'errors_count': len(self.errors)
                },
                processed_by=self.user_id,
                processing_time=Decimal(str(round(processing_time, 2)))
            )
            
            self.db.add(log)
            logger.info(f"Log de processamento criado: {filename}")
            
        except Exception as e:
            logger.error(f"Erro ao criar log de processamento: {e}")
