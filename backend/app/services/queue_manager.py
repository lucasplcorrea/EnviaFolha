"""
Serviço de Gerenciamento de Filas de Envio
"""

import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_

from app.models.send_queue import SendQueue, SendQueueItem
from app.models.employee import Employee

logger = logging.getLogger(__name__)


class QueueManagerService:
    """Serviço para gerenciar filas de envio."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_queue(
        self,
        queue_type: str,
        total_items: int,
        description: str,
        user_id: int,
        file_name: Optional[str] = None,
        computer_name: Optional[str] = None,
        ip_address: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> SendQueue:
        """
        Cria uma nova fila de envio.
        
        Args:
            queue_type: Tipo da fila ('payroll' ou 'communication')
            total_items: Total de itens a serem enviados
            description: Descrição da fila
            user_id: ID do usuário que iniciou
            file_name: Nome do arquivo (opcional)
            computer_name: Nome do computador
            ip_address: IP do computador
            metadata: Metadados adicionais
            
        Returns:
            SendQueue criada
        """
        queue_id = str(uuid.uuid4())
        
        queue = SendQueue(
            queue_id=queue_id,
            queue_type=queue_type,
            status='pending',
            total_items=total_items,
            processed_items=0,
            successful_items=0,
            failed_items=0,
            description=description,
            file_name=file_name,
            user_id=user_id,
            computer_name=computer_name,
            ip_address=ip_address,
            metadata=metadata or {},
            started_at=datetime.now()
        )
        
        self.db.add(queue)
        self.db.commit()
        self.db.refresh(queue)
        
        logger.info(f"Fila criada: {queue_id} - {description}")
        return queue
    
    def add_queue_item(
        self,
        queue_id: str,
        employee_id: int,
        phone_number: str,
        file_path: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> SendQueueItem:
        """Adiciona um item à fila."""
        item = SendQueueItem(
            queue_id=queue_id,
            employee_id=employee_id,
            phone_number=phone_number,
            file_path=file_path,
            status='pending',
            metadata=metadata or {}
        )
        
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        
        return item
    
    def update_queue_progress(
        self,
        queue_id: str,
        processed: int = 0,
        successful: int = 0,
        failed: int = 0
    ):
        """Atualiza o progresso da fila."""
        queue = self.db.query(SendQueue).filter(
            SendQueue.queue_id == queue_id
        ).first()
        
        if queue:
            if processed > 0:
                queue.processed_items += processed
            if successful > 0:
                queue.successful_items += successful
            if failed > 0:
                queue.failed_items += failed
            
            # Atualizar status
            if queue.processed_items >= queue.total_items:
                queue.status = 'completed'
                queue.completed_at = datetime.now()
            elif queue.status == 'pending':
                queue.status = 'processing'
            
            self.db.commit()
            self.db.refresh(queue)
    
    def update_item_status(
        self,
        item_id: int,
        status: str,
        error_message: Optional[str] = None
    ):
        """Atualiza status de um item."""
        item = self.db.query(SendQueueItem).filter(
            SendQueueItem.id == item_id
        ).first()
        
        if item:
            item.status = status
            if status == 'sent':
                item.sent_at = datetime.now()
            if error_message:
                item.error_message = error_message
                item.retry_count += 1
            
            self.db.commit()
    
    def cancel_queue(self, queue_id: str, user_id: int) -> bool:
        """
        Cancela uma fila de envio.
        
        Args:
            queue_id: ID da fila
            user_id: ID do usuário solicitando cancelamento
            
        Returns:
            True se cancelado com sucesso
        """
        queue = self.db.query(SendQueue).filter(
            SendQueue.queue_id == queue_id
        ).first()
        
        if not queue:
            return False
        
        # Só pode cancelar filas ativas
        if queue.status not in ['pending', 'processing']:
            return False
        
        queue.status = 'cancelled'
        queue.cancelled_at = datetime.now()
        queue.completed_at = datetime.now()
        
        self.db.commit()
        
        logger.info(f"Fila cancelada: {queue_id} por usuário {user_id}")
        return True
    
    def get_active_queues(self) -> List[Dict[str, Any]]:
        """Retorna todas as filas ativas (pending ou processing)."""
        queues = self.db.query(SendQueue).filter(
            SendQueue.status.in_(['pending', 'processing'])
        ).order_by(desc(SendQueue.created_at)).all()
        
        return self._format_queues(queues)
    
    def get_all_queues(
        self,
        limit: int = 50,
        status_filter: Optional[str] = None,
        queue_type_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retorna todas as filas com filtros opcionais.
        
        Args:
            limit: Número máximo de filas
            status_filter: Filtrar por status
            queue_type_filter: Filtrar por tipo
            
        Returns:
            Lista de filas formatadas
        """
        query = self.db.query(SendQueue)
        
        if status_filter:
            query = query.filter(SendQueue.status == status_filter)
        
        if queue_type_filter:
            query = query.filter(SendQueue.queue_type == queue_type_filter)
        
        queues = query.order_by(desc(SendQueue.created_at)).limit(limit).all()
        
        return self._format_queues(queues)
    
    def get_queue_details(self, queue_id: str) -> Optional[Dict[str, Any]]:
        """Retorna detalhes completos de uma fila incluindo itens."""
        queue = self.db.query(SendQueue).filter(
            SendQueue.queue_id == queue_id
        ).first()
        
        if not queue:
            return None
        
        # Buscar itens da fila
        items = self.db.query(SendQueueItem).filter(
            SendQueueItem.queue_id == queue_id
        ).all()
        
        return {
            'queue': self._format_queue(queue),
            'items': self._format_queue_items(items)
        }
    
    def get_queue_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas gerais das filas."""
        total_queues = self.db.query(SendQueue).count()
        active_queues = self.db.query(SendQueue).filter(
            SendQueue.status.in_(['pending', 'processing'])
        ).count()
        
        completed_today = self.db.query(SendQueue).filter(
            SendQueue.status == 'completed',
            SendQueue.completed_at >= datetime.now().replace(hour=0, minute=0, second=0)
        ).count()
        
        return {
            'total_queues': total_queues,
            'active_queues': active_queues,
            'completed_today': completed_today
        }
    
    def _format_queue(self, queue: SendQueue) -> Dict[str, Any]:
        """Formata uma fila para resposta."""
        return {
            'id': queue.id,
            'queue_id': queue.queue_id,
            'queue_type': queue.queue_type,
            'status': queue.status,
            'description': queue.description,
            'file_name': queue.file_name,
            'total_items': queue.total_items,
            'processed_items': queue.processed_items,
            'successful_items': queue.successful_items,
            'failed_items': queue.failed_items,
            'progress_percentage': queue.progress_percentage,
            'success_rate': queue.success_rate,
            'is_active': queue.is_active,
            'user_id': queue.user_id,
            'computer_name': queue.computer_name,
            'ip_address': queue.ip_address,
            'started_at': queue.started_at.isoformat() if queue.started_at else None,
            'completed_at': queue.completed_at.isoformat() if queue.completed_at else None,
            'cancelled_at': queue.cancelled_at.isoformat() if queue.cancelled_at else None,
            'created_at': queue.created_at.isoformat(),
            'metadata': queue.metadata
        }
    
    def _format_queues(self, queues: List[SendQueue]) -> List[Dict[str, Any]]:
        """Formata lista de filas."""
        return [self._format_queue(queue) for queue in queues]
    
    def _format_queue_items(self, items: List[SendQueueItem]) -> List[Dict[str, Any]]:
        """Formata itens da fila."""
        result = []
        for item in items:
            result.append({
                'id': item.id,
                'employee_id': item.employee_id,
                'employee_name': item.employee.name if item.employee else None,
                'phone_number': item.phone_number,
                'status': item.status,
                'sent_at': item.sent_at.isoformat() if item.sent_at else None,
                'error_message': item.error_message,
                'retry_count': item.retry_count,
                'metadata': item.metadata
            })
        return result
