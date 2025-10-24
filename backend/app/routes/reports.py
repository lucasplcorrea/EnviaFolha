"""
Routes para relatórios e atividades recentes
"""
import json
from datetime import datetime
from typing import Optional
from sqlalchemy import desc, or_, func
from sqlalchemy.orm import Session, joinedload

from .base import BaseRouter
from ..core.auth import get_current_user
from ..models.employee import Employee
from ..models.payroll_send import PayrollSend
from ..models.communication_send import CommunicationSend
from ..models.communication_recipient import CommunicationRecipient
from ..models.user import User
from ..models.base import get_db


class ReportsRouter(BaseRouter):
    """Router para endpoints de relatórios"""
    
    def __init__(self, handler):
        super().__init__(handler)
        # Copiar atributos do handler para compatibilidade
        self.headers = handler.headers
        self.path = handler.path
    
    def handle_recent_activity(self):
        """
        GET /api/v1/reports/recent
        Retorna as últimas atividades de envio (holerites e comunicados)
        Query params:
        - limit: número máximo de resultados (padrão: 10)
        """
        try:
            # Extrair parâmetros
            query_params = self.parse_query_params()
            limit = int(query_params.get('limit', ['10'])[0])
            limit = min(limit, 50)  # Máximo 50 registros
            
            db = next(get_db())
            
            try:
                # Buscar últimos envios de holerites
                payroll_sends = db.query(PayrollSend).options(
                    joinedload(PayrollSend.employee),
                    joinedload(PayrollSend.user)
                ).order_by(desc(PayrollSend.sent_at)).limit(limit).all()
                
                # Buscar últimos envios de comunicados (via recipients)
                communication_recipients = db.query(CommunicationRecipient).options(
                    joinedload(CommunicationRecipient.employee),
                    joinedload(CommunicationRecipient.communication_send).joinedload(CommunicationSend.user)
                ).order_by(desc(CommunicationRecipient.sent_at)).limit(limit).all()
                
                # Combinar e formatar resultados
                activities = []
                
                # Adicionar holerites
                for send in payroll_sends:
                    if send.sent_at:  # Apenas enviados
                        activities.append({
                            'id': f'payroll_{send.id}',
                            'type': 'payroll',
                            'employee_name': send.employee.name if send.employee else 'Desconhecido',
                            'employee_id': send.employee_id,
                            'sent_by_user': send.user.username if send.user else 'Sistema',
                            'status': send.status,
                            'sent_at': send.sent_at.isoformat() if send.sent_at else None,
                            'month': send.month,
                            'error_message': send.error_message
                        })
                
                # Adicionar comunicados
                for recipient in communication_recipients:
                    if recipient.sent_at:  # Apenas enviados
                        activities.append({
                            'id': f'communication_{recipient.id}',
                            'type': 'communication',
                            'employee_name': recipient.employee.name if recipient.employee else 'Desconhecido',
                            'employee_id': recipient.employee_id,
                            'sent_by_user': recipient.communication_send.user.username if recipient.communication_send and recipient.communication_send.user else 'Sistema',
                            'status': recipient.status,
                            'sent_at': recipient.sent_at.isoformat() if recipient.sent_at else None,
                            'title': recipient.communication_send.title if recipient.communication_send else None,
                            'error_message': recipient.error_message
                        })
                
                # Ordenar por data de envio (mais recente primeiro)
                activities.sort(key=lambda x: x['sent_at'] or '', reverse=True)
                
                # Limitar ao número solicitado
                activities = activities[:limit]
                
                self.send_json_response(activities)
                
            finally:
                db.close()
                
        except ValueError as e:
            self.send_error_response(400, f"Parâmetro inválido: {str(e)}")
        except Exception as e:
            print(f"❌ Erro ao buscar atividades recentes: {str(e)}")
            import traceback
            traceback.print_exc()
            self.send_error_response(500, "Erro ao buscar atividades recentes")
    
    def handle_statistics(self):
        """
        GET /api/v1/reports/statistics
        Retorna estatísticas gerais de envios
        """
        try:
            db = next(get_db())
            
            try:
                # Estatísticas de holerites
                total_payrolls = db.query(func.count(PayrollSend.id)).scalar() or 0
                success_payrolls = db.query(func.count(PayrollSend.id)).filter(
                    PayrollSend.status == 'sent'
                ).scalar() or 0
                failed_payrolls = db.query(func.count(PayrollSend.id)).filter(
                    PayrollSend.status == 'failed'
                ).scalar() or 0
                
                # Estatísticas de comunicados
                total_communications = db.query(func.count(CommunicationRecipient.id)).scalar() or 0
                success_communications = db.query(func.count(CommunicationRecipient.id)).filter(
                    CommunicationRecipient.status == 'sent'
                ).scalar() or 0
                failed_communications = db.query(func.count(CommunicationRecipient.id)).filter(
                    CommunicationRecipient.status == 'failed'
                ).scalar() or 0
                
                # Totais gerais
                total_sent = success_payrolls + success_communications
                total_failed = failed_payrolls + failed_communications
                total_all = total_sent + total_failed
                
                # Taxa de sucesso
                success_rate = (total_sent / total_all * 100) if total_all > 0 else 100.0
                
                statistics = {
                    'summary': {
                        'total_sent': total_all,
                        'total_success': total_sent,
                        'total_failed': total_failed,
                        'success_rate': round(success_rate, 2)
                    },
                    'by_type': {
                        'payrolls': {
                            'total': total_payrolls,
                            'success': success_payrolls,
                            'failed': failed_payrolls,
                            'success_rate': round((success_payrolls / total_payrolls * 100) if total_payrolls > 0 else 100.0, 2)
                        },
                        'communications': {
                            'total': total_communications,
                            'success': success_communications,
                            'failed': failed_communications,
                            'success_rate': round((success_communications / total_communications * 100) if total_communications > 0 else 100.0, 2)
                        }
                    }
                }
                
                self.send_json_response(statistics)
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Erro ao buscar estatísticas: {str(e)}")
            import traceback
            traceback.print_exc()
            self.send_error_response(500, "Erro ao buscar estatísticas")
    
    def send_error_response(self, status_code: int, message: str):
        """Enviar resposta de erro"""
        self.send_json_response({"error": message}, status_code)
    
    def parse_query_params(self):
        """Extrair parâmetros da query string"""
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(self.path)
        return parse_qs(parsed.query)
