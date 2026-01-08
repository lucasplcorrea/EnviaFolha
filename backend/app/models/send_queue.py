"""
Modelo de Fila de Envio
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.models.base import Base, TimestampMixin


class SendQueue(Base, TimestampMixin):
    """Modelo para gerenciar filas de envio."""
    
    __tablename__ = 'send_queues'
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Identificação
    queue_id = Column(String(100), unique=True, index=True, nullable=False)  # UUID único
    queue_type = Column(String(50), nullable=False)  # 'payroll', 'communication'
    
    # Status
    status = Column(String(50), nullable=False, default='pending')  # pending, processing, completed, failed, cancelled
    
    # Informações do envio
    total_items = Column(Integer, nullable=False, default=0)
    processed_items = Column(Integer, nullable=False, default=0)
    successful_items = Column(Integer, nullable=False, default=0)
    failed_items = Column(Integer, nullable=False, default=0)
    
    # Detalhes
    description = Column(String(500))
    file_name = Column(String(255))
    
    # Metadados
    queue_metadata = Column(JSON)  # Informações extras como filtros, configurações, etc
    error_message = Column(Text)
    
    # Controle
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    cancelled_at = Column(DateTime)
    
    # Usuário responsável
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship('User', backref='send_queues')
    
    # Informações do computador/sessão
    computer_name = Column(String(255))
    ip_address = Column(String(45))
    
    def __repr__(self):
        try:
            # Usar object.__getattribute__ para evitar recursão com SQLAlchemy
            queue_id = object.__getattribute__(self, '__dict__').get('queue_id', 'N/A')
            queue_type = object.__getattribute__(self, '__dict__').get('queue_type', 'N/A')
            status = object.__getattribute__(self, '__dict__').get('status', 'N/A')
            return f"<SendQueue(queue_id={queue_id}, type={queue_type}, status={status})>"
        except:
            return "<SendQueue(...)>"
    
    @property
    def progress_percentage(self):
        """Calcula percentual de progresso."""
        if self.total_items == 0:
            return 0
        return round((self.processed_items / self.total_items) * 100, 2)
    
    @property
    def is_active(self):
        """Verifica se a fila está ativa."""
        return self.status in ['pending', 'processing']
    
    @property
    def success_rate(self):
        """Calcula taxa de sucesso."""
        if self.processed_items == 0:
            return 0
        return round((self.successful_items / self.processed_items) * 100, 2)


class SendQueueItem(Base, TimestampMixin):
    """Modelo para itens individuais da fila."""
    
    __tablename__ = 'send_queue_items'
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relacionamento com a fila
    queue_id = Column(String(100), ForeignKey('send_queues.queue_id'), nullable=False)
    queue = relationship('SendQueue', backref='items')
    
    # Identificação do item
    employee_id = Column(Integer, ForeignKey('employees.id'))
    employee = relationship('Employee')
    
    # Status do envio
    status = Column(String(50), nullable=False, default='pending')  # pending, sending, sent, failed, skipped
    
    # Detalhes
    phone_number = Column(String(20))
    file_path = Column(String(500))
    
    # Resultado
    sent_at = Column(DateTime)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Metadados
    item_metadata = Column(JSON)
    
    def __repr__(self):
        try:
            # Usar object.__getattribute__ para evitar recursão com SQLAlchemy
            queue_id = object.__getattribute__(self, '__dict__').get('queue_id', 'N/A')
            status = object.__getattribute__(self, '__dict__').get('status', 'N/A')
            return f"<SendQueueItem(queue_id={queue_id}, status={status})>"
        except:
            return "<SendQueueItem(...)>"
