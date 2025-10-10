"""
Serviço para processamento de dados de folha de pagamento
"""

import pandas as pd
import json
import logging
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING
from sqlalchemy.orm import Session
from datetime import datetime
import re

if TYPE_CHECKING:
    from ..models.payroll import PayrollTemplate
    from ..models.employee import Employee

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PayrollProcessingService:
    """Serviço para processar planilhas Excel de folha de pagamento"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def create_period(self, year: int, month: int, period_name: str, description: str = None) -> Dict:
        """Cria um novo período de folha de pagamento"""
        from ..models.payroll import PayrollPeriod
        
        try:
            # Verificar se período já existe
            existing = self.db.query(PayrollPeriod).filter(
                PayrollPeriod.year == year,
                PayrollPeriod.month == month,
                PayrollPeriod.period_name == period_name
            ).first()
            
            if existing:
                return {"success": False, "message": "Período já existe"}
            
            period = PayrollPeriod(
                year=year,
                month=month,
                period_name=period_name,
                description=description
            )
            
            self.db.add(period)
            self.db.commit()
            
            logger.info(f"Período {period_name} criado com sucesso")
            return {"success": True, "message": "Período criado com sucesso", "period_id": period.id}
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar período: {str(e)}")
            return {"success": False, "message": f"Erro ao criar período: {str(e)}"}
    
    def create_template(self, template_data: Dict) -> Dict:
        """Cria um template para processamento de planilhas"""
        from ..models.payroll import PayrollTemplate
        
        try:
            template = PayrollTemplate(
                name=template_data["name"],
                description=template_data.get("description"),
                column_mapping=template_data["column_mapping"],
                skip_rows=template_data.get("skip_rows", 0),
                header_row=template_data.get("header_row", 1),
                is_default=template_data.get("is_default", False),
                created_by=template_data.get("created_by")
            )
            
            # Se for template padrão, remover flag de outros templates
            if template.is_default:
                self.db.query(PayrollTemplate).update({"is_default": False})
            
            self.db.add(template)
            self.db.commit()
            
            logger.info(f"Template {template.name} criado com sucesso")
            return {"success": True, "message": "Template criado com sucesso", "template_id": template.id}
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar template: {str(e)}")
            return {"success": False, "message": f"Erro ao criar template: {str(e)}"}
    
    def process_excel_file(self, file_path: str, period_id: int, template_id: Optional[int] = None, 
                          user_id: int = None) -> Dict:
        """Processa arquivo Excel de folha de pagamento"""
        from ..models.payroll import PayrollProcessingLog, PayrollTemplate, PayrollPeriod, PayrollData
        from ..models.employee import Employee
        
        start_time = datetime.now()
        
        try:
            # Criar log de processamento
            log = PayrollProcessingLog(
                period_id=period_id,
                template_id=template_id,
                filename=file_path.split('/')[-1],
                status='processing',
                processed_by=user_id
            )
            self.db.add(log)
            self.db.flush()  # Para obter o ID
            
            # Carregar template se especificado
            template = None
            if template_id:
                template = self.db.query(PayrollTemplate).filter(PayrollTemplate.id == template_id).first()
            else:
                # Usar template padrão
                template = self.db.query(PayrollTemplate).filter(PayrollTemplate.is_default == True).first()
            
            # Ler arquivo Excel
            df = pd.read_excel(file_path, skiprows=template.skip_rows if template else 0)
            log.total_rows = len(df)
            log.file_size = self._get_file_size(file_path)
            
            processed_count = 0
            error_count = 0
            errors = []
            
            # Processar cada linha
            for index, row in df.iterrows():
                try:
                    result = self._process_row(row, period_id, template, user_id)
                    if result["success"]:
                        processed_count += 1
                    else:
                        error_count += 1
                        errors.append(f"Linha {index + 2}: {result['message']}")
                        
                except Exception as e:
                    error_count += 1
                    errors.append(f"Linha {index + 2}: Erro inesperado - {str(e)}")
            
            # Atualizar log
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            log.processed_rows = processed_count
            log.error_rows = error_count
            log.processing_time = processing_time
            log.processing_summary = {
                "total_rows": len(df),
                "processed_rows": processed_count,
                "error_rows": error_count,
                "errors": errors[:10],  # Apenas os primeiros 10 erros
                "processing_time": processing_time
            }
            
            if error_count == 0:
                log.status = 'completed'
            elif processed_count > 0:
                log.status = 'partial'
            else:
                log.status = 'failed'
                log.error_message = "Nenhuma linha foi processada com sucesso"
            
            self.db.commit()
            
            return {
                "success": log.status in ['completed', 'partial'],
                "message": f"Processamento concluído: {processed_count} linhas processadas, {error_count} erros",
                "details": {
                    "total_rows": len(df),
                    "processed_rows": processed_count,
                    "error_rows": error_count,
                    "processing_time": processing_time,
                    "errors": errors
                }
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro no processamento: {str(e)}")
            
            # Atualizar log com erro
            if 'log' in locals():
                log.status = 'failed'
                log.error_message = str(e)
                self.db.commit()
            
            return {"success": False, "message": f"Erro no processamento: {str(e)}"}
    
    def _process_row(self, row: pd.Series, period_id: int, template: 'PayrollTemplate', user_id: int) -> Dict:
        """Processa uma linha da planilha"""
        from ..models.payroll import PayrollData
        from ..models.employee import Employee
        
        try:
            # Identificar funcionário
            employee = self._identify_employee(row, template)
            if not employee:
                return {"success": False, "message": "Funcionário não encontrado"}
            
            # Verificar se já existe registro para este período
            existing = self.db.query(PayrollData).filter(
                PayrollData.employee_id == employee.id,
                PayrollData.period_id == period_id
            ).first()
            
            if existing:
                # Atualizar registro existente
                payroll_data = existing
            else:
                # Criar novo registro
                payroll_data = PayrollData(
                    employee_id=employee.id,
                    period_id=period_id,
                    processed_by=user_id
                )
                self.db.add(payroll_data)
            
            # Extrair dados usando template
            if template:
                extracted_data = self._extract_data_with_template(row, template)
            else:
                extracted_data = self._extract_data_auto(row)
            
            # Atualizar campos
            payroll_data.gross_salary = extracted_data.get("gross_salary")
            payroll_data.net_salary = extracted_data.get("net_salary")
            payroll_data.earnings_data = extracted_data.get("earnings", {})
            payroll_data.deductions_data = extracted_data.get("deductions", {})
            payroll_data.benefits_data = extracted_data.get("benefits", {})
            payroll_data.additional_data = extracted_data.get("additional", {})
            
            return {"success": True, "message": "Linha processada com sucesso"}
            
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def _identify_employee(self, row: pd.Series, template: 'PayrollTemplate') -> Optional['Employee']:
        """Identifica o funcionário na linha"""
        from ..models.employee import Employee
        
        if template and template.column_mapping.get("employee_identifier"):
            identifier_column = template.column_mapping["employee_identifier"]
            identifier_value = str(row.get(identifier_column, "")).strip()
        else:
            # Tentar identificar por CPF, unique_id ou nome
            identifier_value = None
            for col in row.index:
                col_lower = str(col).lower()
                if any(term in col_lower for term in ['cpf', 'unique_id', 'id', 'matricula']):
                    identifier_value = str(row[col]).strip()
                    break
        
        if not identifier_value:
            return None
        
        # Buscar funcionário
        # Primeiro por CPF
        if len(identifier_value) == 11 and identifier_value.isdigit():
            employee = self.db.query(Employee).filter(Employee.cpf == identifier_value).first()
            if employee:
                return employee
        
        # Depois por unique_id
        employee = self.db.query(Employee).filter(Employee.unique_id == identifier_value).first()
        if employee:
            return employee
        
        # Por último por nome (parcial)
        employee = self.db.query(Employee).filter(Employee.name.ilike(f"%{identifier_value}%")).first()
        return employee
    
    def _extract_data_with_template(self, row: pd.Series, template: 'PayrollTemplate') -> Dict:
        """Extrai dados usando template"""
        mapping = template.column_mapping
        result = {
            "earnings": {},
            "deductions": {},
            "benefits": {},
            "additional": {}
        }
        
        # Extrair proventos
        for column in mapping.get("earnings", []):
            if column in row.index:
                value = self._clean_numeric_value(row[column])
                if value is not None:
                    result["earnings"][column] = value
        
        # Extrair descontos
        for column in mapping.get("deductions", []):
            if column in row.index:
                value = self._clean_numeric_value(row[column])
                if value is not None:
                    result["deductions"][column] = value
        
        # Extrair benefícios
        for column in mapping.get("benefits", []):
            if column in row.index:
                value = self._clean_numeric_value(row[column])
                if value is not None:
                    result["benefits"][column] = value
        
        # Calcular totais
        if result["earnings"]:
            result["gross_salary"] = sum(result["earnings"].values())
        
        if result["deductions"]:
            deductions_total = sum(result["deductions"].values())
            result["net_salary"] = result.get("gross_salary", 0) - deductions_total
        
        return result
    
    def _extract_data_auto(self, row: pd.Series) -> Dict:
        """Extrai dados automaticamente baseado nos nomes das colunas"""
        result = {
            "earnings": {},
            "deductions": {},
            "benefits": {},
            "additional": {}
        }
        
        for column, value in row.items():
            col_lower = str(column).lower()
            clean_value = self._clean_numeric_value(value)
            
            if clean_value is None:
                continue
            
            # Categorizar por palavras-chave
            if any(term in col_lower for term in ['salario', 'salário', 'vencimento', 'remuneracao']):
                result["earnings"][column] = clean_value
            elif any(term in col_lower for term in ['hora', 'extra', 'adicional', 'gratificacao']):
                result["earnings"][column] = clean_value
            elif any(term in col_lower for term in ['inss', 'ir', 'irrf', 'desconto', 'contribuicao']):
                result["deductions"][column] = clean_value
            elif any(term in col_lower for term in ['vale', 'alimentacao', 'transporte', 'saude', 'plano']):
                result["benefits"][column] = clean_value
            elif any(term in col_lower for term in ['liquido', 'líquido', 'total']):
                result["net_salary"] = clean_value
            else:
                result["additional"][column] = clean_value
        
        return result
    
    def _clean_numeric_value(self, value) -> Optional[float]:
        """Limpa e converte valor numérico"""
        if pd.isna(value) or value == '' or value is None:
            return None
        
        # Converter para string e limpar
        str_value = str(value).strip()
        
        # Remover símbolos de moeda e espaços
        str_value = re.sub(r'[R$\\s]', '', str_value)
        
        # Substituir vírgula por ponto (formato brasileiro)
        if ',' in str_value and '.' in str_value:
            # Se tem ambos, vírgula é decimal
            str_value = str_value.replace('.', '').replace(',', '.')
        elif ',' in str_value:
            # Apenas vírgula, assumir que é decimal
            str_value = str_value.replace(',', '.')
        
        try:
            return float(str_value)
        except ValueError:
            return None
    
    def _get_file_size(self, file_path: str) -> int:
        """Obtém tamanho do arquivo em bytes"""
        try:
            import os
            return os.path.getsize(file_path)
        except:
            return 0
    
    def get_payroll_summary(self, period_id: int) -> Dict:
        """Retorna resumo da folha de pagamento para um período"""
        from ..models.payroll import PayrollData, PayrollPeriod
        from ..models.employee import Employee
        
        try:
            period = self.db.query(PayrollPeriod).filter(PayrollPeriod.id == period_id).first()
            if not period:
                return {"success": False, "message": "Período não encontrado"}
            
            # Buscar dados do período
            payroll_records = self.db.query(PayrollData).filter(PayrollData.period_id == period_id).all()
            
            total_employees = len(payroll_records)
            total_gross = sum(record.gross_salary or 0 for record in payroll_records)
            total_net = sum(record.net_salary or 0 for record in payroll_records)
            total_deductions = total_gross - total_net
            
            # Agrupar por departamento
            department_summary = {}
            for record in payroll_records:
                dept = record.employee.department or "Sem Departamento"
                if dept not in department_summary:
                    department_summary[dept] = {
                        "employees": 0,
                        "gross_total": 0,
                        "net_total": 0
                    }
                
                department_summary[dept]["employees"] += 1
                department_summary[dept]["gross_total"] += record.gross_salary or 0
                department_summary[dept]["net_total"] += record.net_salary or 0
            
            return {
                "success": True,
                "period": {
                    "id": period.id,
                    "name": period.period_name,
                    "year": period.year,
                    "month": period.month
                },
                "summary": {
                    "total_employees": total_employees,
                    "total_gross_salary": total_gross,
                    "total_net_salary": total_net,
                    "total_deductions": total_deductions,
                    "average_gross": total_gross / total_employees if total_employees > 0 else 0,
                    "average_net": total_net / total_employees if total_employees > 0 else 0
                },
                "by_department": department_summary
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar resumo: {str(e)}")
            return {"success": False, "message": f"Erro ao gerar resumo: {str(e)}"}