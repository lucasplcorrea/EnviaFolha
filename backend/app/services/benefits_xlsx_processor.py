"""
Serviço para processar arquivos XLSX de benefícios iFood
"""
import logging
import openpyxl
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.employee import Employee
from app.models.payroll import BenefitsPeriod, BenefitsData, BenefitsProcessingLog

logger = logging.getLogger(__name__)


class BenefitsXLSXProcessor:
    """Processador de arquivos XLSX de benefícios"""
    
    def __init__(self, db_session: Session, user_id: Optional[int] = None):
        self.db = db_session
        self.user_id = user_id
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    @staticmethod
    def normalize_cpf(cpf: str) -> str:
        """
        Normaliza CPF removendo todos os caracteres não numéricos
        
        Args:
            cpf: CPF em qualquer formato (xxx.xxx.xxx-xx, xxx-xxx.xxx-xx, etc)
            
        Returns:
            CPF apenas com dígitos (xxxxxxxxxxx)
        """
        if not cpf:
            return ""
        # Remove tudo que não é dígito
        import re
        return re.sub(r'\D', '', str(cpf))
        
    def process_xlsx_file(
        self,
        file_path: str,
        year: int,
        month: int,
        company: str,
        period_name: Optional[str] = None
    ) -> Dict:
        """
        Processa arquivo XLSX de benefícios
        
        Args:
            file_path: Caminho para o arquivo XLSX
            year: Ano de referência
            month: Mês de referência
            company: Código da empresa ('0060' ou '0059')
            period_name: Nome do período (opcional, gerado automaticamente se não fornecido)
            
        Returns:
            Dicionário com resultado do processamento
        """
        start_time = datetime.now()
        self.errors = []
        self.warnings = []
        
        try:
            # Gerar nome do período se não fornecido
            if not period_name:
                month_names = [
                    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
                ]
                period_name = f"{month_names[month - 1]} {year}"
            
            # Criar ou obter período
            period = self._get_or_create_period(year, month, period_name, company)
            if not period:
                return {
                    "success": False,
                    "error": "Não foi possível criar ou encontrar o período",
                    "errors": self.errors
                }
            
            # Carregar arquivo XLSX
            logger.info(f"Carregando arquivo XLSX: {file_path}")
            wb = openpyxl.load_workbook(file_path, data_only=True)
            ws = wb.active
            
            # Obter cabeçalhos
            headers = [cell.value for cell in ws[1]]
            logger.info(f"Cabeçalhos encontrados: {headers}")
            
            # Validar cabeçalhos necessários
            required_columns = ['CPF', 'Refeicao', 'Alimentacao', 'Mobilidade', 'Livre']
            missing_columns = [col for col in required_columns if col not in headers]
            if missing_columns:
                error_msg = f"Colunas obrigatórias ausentes: {', '.join(missing_columns)}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "errors": [error_msg]
                }
            
            # Mapear índices das colunas
            column_indices = {col: headers.index(col) for col in required_columns}
            
            # Processar linhas
            total_rows = 0
            processed_rows = 0
            error_rows = 0
            
            import os
            filename = os.path.basename(file_path)
            
            for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                total_rows += 1
                
                try:
                    # Extrair dados da linha
                    cpf = row[column_indices['CPF']]
                    refeicao = row[column_indices['Refeicao']]
                    alimentacao = row[column_indices['Alimentacao']]
                    mobilidade = row[column_indices['Mobilidade']]
                    livre = row[column_indices['Livre']]
                    
                    # Validar CPF
                    if not cpf:
                        self.warnings.append(f"Linha {row_idx}: CPF vazio, ignorando")
                        continue
                    
                    # Normalizar CPF (converter para string e formatar)
                    cpf_str = str(cpf).strip()
                    
                    # Processar linha
                    success = self._process_benefits_row(
                        period=period,
                        cpf=cpf_str,
                        refeicao=refeicao,
                        alimentacao=alimentacao,
                        mobilidade=mobilidade,
                        livre=livre,
                        filename=filename,
                        row_number=row_idx
                    )
                    
                    if success:
                        processed_rows += 1
                    else:
                        error_rows += 1
                        
                except Exception as e:
                    error_rows += 1
                    error_msg = f"Linha {row_idx}: {str(e)}"
                    logger.error(error_msg)
                    self.errors.append(error_msg)
            
            # Commit das alterações
            try:
                self.db.commit()
                logger.info(f"Dados de benefícios salvos com sucesso para o período {period.period_name}")
            except SQLAlchemyError as e:
                self.db.rollback()
                error_msg = f"Erro ao salvar dados: {str(e)}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "errors": self.errors
                }
            
            # Calcular tempo de processamento
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Criar log de processamento
            self._create_processing_log(
                period=period,
                filename=filename,
                file_size=os.path.getsize(file_path) if os.path.exists(file_path) else None,
                total_rows=total_rows,
                processed_rows=processed_rows,
                error_rows=error_rows,
                processing_time=processing_time,
                status='completed' if error_rows == 0 else 'partial'
            )
            
            return {
                "success": True,
                "period_id": period.id,
                "period_name": period.period_name,
                "total_rows": total_rows,
                "processed_rows": processed_rows,
                "error_rows": error_rows,
                "warnings": self.warnings,
                "errors": self.errors,
                "processing_time": processing_time
            }
            
        except Exception as e:
            logger.exception(f"Erro ao processar arquivo XLSX: {str(e)}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e),
                "errors": self.errors
            }
    
    def _get_or_create_period(
        self,
        year: int,
        month: int,
        period_name: str,
        company: str
    ) -> Optional[BenefitsPeriod]:
        """Busca ou cria um período de benefícios"""
        try:
            # Verificar se já existe
            period = self.db.query(BenefitsPeriod).filter(
                BenefitsPeriod.year == year,
                BenefitsPeriod.month == month,
                BenefitsPeriod.company == company
            ).first()
            
            if period:
                logger.info(f"Período existente encontrado: {period.period_name}")
                return period
            
            # Criar novo período
            period = BenefitsPeriod(
                year=year,
                month=month,
                period_name=period_name,
                company=company
            )
            self.db.add(period)
            self.db.flush()  # Para obter o ID
            
            logger.info(f"Novo período criado: {period.period_name}")
            return period
            
        except Exception as e:
            error_msg = f"Erro ao criar período: {str(e)}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return None
    
    def _process_benefits_row(
        self,
        period: BenefitsPeriod,
        cpf: str,
        refeicao,
        alimentacao,
        mobilidade,
        livre,
        filename: str,
        row_number: int
    ) -> bool:
        """Processa uma linha de benefícios"""
        try:
            # Normalizar CPF para busca (apenas dígitos)
            cpf_normalized = self.normalize_cpf(cpf)
            
            if not cpf_normalized or len(cpf_normalized) != 11:
                warning_msg = f"Linha {row_number}: CPF inválido '{cpf}' (deve ter 11 dígitos)"
                logger.warning(warning_msg)
                self.warnings.append(warning_msg)
                return False
            
            # Buscar funcionário comparando CPFs normalizados
            # Usamos função SQL para normalizar o CPF do banco na comparação
            from sqlalchemy import func
            employee = self.db.query(Employee).filter(
                func.regexp_replace(Employee.cpf, r'[^0-9]', '', 'g') == cpf_normalized
            ).first()
            
            if not employee:
                warning_msg = f"Linha {row_number}: Colaborador com CPF {cpf} (normalizado: {cpf_normalized}) não encontrado no sistema"
                logger.warning(warning_msg)
                self.warnings.append(warning_msg)
                return False
            
            # Verificar se já existe registro para este período e colaborador
            existing = self.db.query(BenefitsData).filter(
                BenefitsData.period_id == period.id,
                BenefitsData.employee_id == employee.id
            ).first()
            
            # Converter valores para Decimal
            def to_decimal(value):
                if value is None or value == '':
                    return Decimal('0')
                try:
                    return Decimal(str(value))
                except:
                    return Decimal('0')
            
            if existing:
                # Atualizar registro existente
                existing.refeicao = to_decimal(refeicao)
                existing.alimentacao = to_decimal(alimentacao)
                existing.mobilidade = to_decimal(mobilidade)
                existing.livre = to_decimal(livre)
                existing.upload_filename = filename
                existing.processed_by = self.user_id
            else:
                # Criar novo registro
                benefits_data = BenefitsData(
                    period_id=period.id,
                    employee_id=employee.id,
                    cpf=cpf,
                    refeicao=to_decimal(refeicao),
                    alimentacao=to_decimal(alimentacao),
                    mobilidade=to_decimal(mobilidade),
                    livre=to_decimal(livre),
                    upload_filename=filename,
                    processed_by=self.user_id
                )
                self.db.add(benefits_data)
            
            return True
            
        except Exception as e:
            error_msg = f"Linha {row_number}: {str(e)}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return False
    
    def _create_processing_log(
        self,
        period: BenefitsPeriod,
        filename: str,
        file_size: Optional[int],
        total_rows: int,
        processed_rows: int,
        error_rows: int,
        processing_time: float,
        status: str
    ):
        """Cria log de processamento"""
        try:
            log = BenefitsProcessingLog(
                period_id=period.id,
                filename=filename,
                file_size=file_size,
                total_rows=total_rows,
                processed_rows=processed_rows,
                error_rows=error_rows,
                status=status,
                processing_summary={
                    "warnings": self.warnings,
                    "errors": self.errors
                },
                processed_by=self.user_id,
                processing_time=Decimal(str(round(processing_time, 2)))
            )
            self.db.add(log)
            self.db.commit()
            logger.info(f"Log de processamento criado para {filename}")
        except Exception as e:
            logger.error(f"Erro ao criar log de processamento: {str(e)}")
