"""
Serviço de logging do sistema.
Centraliza a gravação de logs no banco de dados para rastreabilidade.
"""
import json
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.system_log import SystemLog, LogLevel, LogCategory


class LoggingService:
    """Serviço para gerenciamento de logs do sistema"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def log(
        self,
        level: LogLevel,
        category: LogCategory,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_method: Optional[str] = None,
        request_path: Optional[str] = None
    ) -> SystemLog:
        """
        Cria um novo log no banco de dados.
        
        Args:
            level: Nível do log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            category: Categoria do log (SYSTEM, AUTH, EMPLOYEE, etc)
            message: Mensagem principal do log
            details: Dicionário com detalhes adicionais (será convertido para JSON)
            user_id: ID do usuário que realizou a ação
            username: Nome do usuário
            entity_type: Tipo de entidade afetada (Employee, Payroll, etc)
            entity_id: ID da entidade afetada
            ip_address: Endereço IP da requisição
            user_agent: User agent do navegador
            request_method: Método HTTP (GET, POST, etc)
            request_path: Caminho da requisição
        
        Returns:
            SystemLog: Objeto de log criado
        """
        try:
            # Converter details para JSON string se fornecido
            details_json = None
            if details:
                try:
                    details_json = json.dumps(details, ensure_ascii=False, default=str)
                except Exception as e:
                    details_json = json.dumps({'error': f'Erro ao serializar details: {str(e)}'})
            
            # Criar log
            log_entry = SystemLog(
                level=level,
                category=category,
                message=message,
                details=details_json,
                user_id=user_id,
                username=username,
                entity_type=entity_type,
                entity_id=entity_id,
                ip_address=ip_address,
                user_agent=user_agent,
                request_method=request_method,
                request_path=request_path
            )
            
            self.db.add(log_entry)
            self.db.commit()
            self.db.refresh(log_entry)
            
            return log_entry
            
        except Exception as e:
            self.db.rollback()
            print(f"❌ Erro ao gravar log no banco: {e}")
            # Não lançar exceção para não quebrar fluxo principal
            return None
    
    # Métodos convenientes para cada nível
    
    def debug(self, category: LogCategory, message: str, **kwargs):
        """Log de debug"""
        return self.log(LogLevel.DEBUG, category, message, **kwargs)
    
    def info(self, category: LogCategory, message: str, **kwargs):
        """Log informativo"""
        return self.log(LogLevel.INFO, category, message, **kwargs)
    
    def warning(self, category: LogCategory, message: str, **kwargs):
        """Log de aviso"""
        return self.log(LogLevel.WARNING, category, message, **kwargs)
    
    def error(self, category: LogCategory, message: str, **kwargs):
        """Log de erro"""
        return self.log(LogLevel.ERROR, category, message, **kwargs)
    
    def critical(self, category: LogCategory, message: str, **kwargs):
        """Log crítico"""
        return self.log(LogLevel.CRITICAL, category, message, **kwargs)
    
    # Métodos específicos para eventos comuns
    
    def log_auth(self, message: str, user_id: Optional[int] = None, username: Optional[str] = None, **kwargs):
        """Log de autenticação"""
        return self.info(LogCategory.AUTH, message, user_id=user_id, username=username, **kwargs)
    
    def log_employee_action(self, action: str, employee_id: str, user_id: Optional[int] = None, **kwargs):
        """Log de ação em colaborador"""
        return self.info(
            LogCategory.EMPLOYEE,
            action,
            entity_type='Employee',
            entity_id=employee_id,
            user_id=user_id,
            **kwargs
        )
    
    def log_import(self, message: str, details: Optional[Dict] = None, user_id: Optional[int] = None, **kwargs):
        """Log de importação de dados"""
        return self.info(LogCategory.IMPORT, message, details=details, user_id=user_id, **kwargs)
    
    def log_payroll(self, message: str, payroll_id: Optional[str] = None, **kwargs):
        """Log de folha de pagamento"""
        return self.info(
            LogCategory.PAYROLL,
            message,
            entity_type='Payroll',
            entity_id=payroll_id,
            **kwargs
        )
    
    def log_communication(self, message: str, communication_id: Optional[str] = None, **kwargs):
        """Log de comunicação/envio"""
        return self.info(
            LogCategory.COMMUNICATION,
            message,
            entity_type='Communication',
            entity_id=communication_id,
            **kwargs
        )
    
    def log_whatsapp(self, message: str, details: Optional[Dict] = None, **kwargs):
        """Log de integração WhatsApp"""
        return self.info(LogCategory.WHATSAPP, message, details=details, **kwargs)
    
    def get_logs(
        self,
        level: Optional[LogLevel] = None,
        category: Optional[LogCategory] = None,
        user_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list:
        """
        Busca logs com filtros.
        
        Args:
            level: Filtrar por nível
            category: Filtrar por categoria
            user_id: Filtrar por usuário
            limit: Quantidade máxima de registros
            offset: Offset para paginação
        
        Returns:
            Lista de logs
        """
        query = self.db.query(SystemLog)
        
        if level:
            query = query.filter(SystemLog.level == level)
        if category:
            query = query.filter(SystemLog.category == category)
        if user_id:
            query = query.filter(SystemLog.user_id == user_id)
        
        logs = query.order_by(SystemLog.created_at.desc()).limit(limit).offset(offset).all()
        
        return [log.to_dict() for log in logs]
    
    def get_recent_logs(self, limit: int = 50) -> list:
        """Retorna logs recentes"""
        logs = self.db.query(SystemLog).order_by(SystemLog.created_at.desc()).limit(limit).all()
        return [log.to_dict() for log in logs]
