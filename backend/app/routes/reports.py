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
from ..services.exportable_reports import build_infra_analytics_xlsx


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
        - page: número da página (padrão: 1)
        - limit: número de resultados por página (padrão: 20, máximo: 100)
        - date_from: data inicial para filtro (formato: YYYY-MM-DD)
        - date_to: data final para filtro (formato: YYYY-MM-DD)
        - send_type: tipo de envio (all, payrolls, communications)
        - status: status do envio (all, success, failed)
        """
        try:
            # Extrair parâmetros
            query_params = self.parse_query_params()
            page = max(int(query_params.get('page', ['1'])[0]), 1)
            limit = int(query_params.get('limit', ['20'])[0])
            limit = min(limit, 100)  # Máximo 100 registros por página
            
            date_from = query_params.get('date_from', [None])[0]
            date_to = query_params.get('date_to', [None])[0]
            send_type = query_params.get('send_type', ['all'])[0]
            status_filter = query_params.get('status', ['all'])[0]
            
            db = next(get_db())
            
            try:
                activities = []
                
                # Filtrar holerites se solicitado
                if send_type in ['all', 'payrolls']:
                    # Construir query para holerites
                    payroll_query = db.query(PayrollSend).options(
                        joinedload(PayrollSend.employee),
                        joinedload(PayrollSend.user)
                    ).filter(PayrollSend.sent_at.isnot(None))
                    
                    # Aplicar filtros de data
                    if date_from:
                        payroll_query = payroll_query.filter(
                            func.date(PayrollSend.sent_at) >= date_from
                        )
                    if date_to:
                        payroll_query = payroll_query.filter(
                            func.date(PayrollSend.sent_at) <= date_to
                        )
                    
                    # Aplicar filtro de status
                    if status_filter == 'success':
                        payroll_query = payroll_query.filter(PayrollSend.status == 'sent')
                    elif status_filter == 'failed':
                        payroll_query = payroll_query.filter(PayrollSend.status == 'failed')
                    
                    payroll_sends = payroll_query.order_by(desc(PayrollSend.sent_at)).all()
                    
                    # Adicionar holerites à lista
                    for send in payroll_sends:
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
                
                # Filtrar comunicados se solicitado
                if send_type in ['all', 'communications']:
                    # Construir query para comunicados
                    comm_query = db.query(CommunicationRecipient).options(
                        joinedload(CommunicationRecipient.employee),
                        joinedload(CommunicationRecipient.communication_send).joinedload(CommunicationSend.user)
                    ).filter(CommunicationRecipient.sent_at.isnot(None))
                    
                    # Aplicar filtros de data
                    if date_from:
                        comm_query = comm_query.filter(
                            func.date(CommunicationRecipient.sent_at) >= date_from
                        )
                    if date_to:
                        comm_query = comm_query.filter(
                            func.date(CommunicationRecipient.sent_at) <= date_to
                        )
                    
                    # Aplicar filtro de status
                    if status_filter == 'success':
                        comm_query = comm_query.filter(CommunicationRecipient.status == 'sent')
                    elif status_filter == 'failed':
                        comm_query = comm_query.filter(CommunicationRecipient.status == 'failed')
                    
                    communication_recipients = comm_query.order_by(desc(CommunicationRecipient.sent_at)).all()
                    
                    # Adicionar comunicados à lista
                    for recipient in communication_recipients:
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
                
                # Calcular paginação
                total = len(activities)
                total_pages = (total + limit - 1) // limit  # Arredondar para cima
                offset = (page - 1) * limit
                
                # Aplicar paginação
                paginated_activities = activities[offset:offset + limit]
                
                # Retornar resposta com metadados de paginação
                response = {
                    'data': paginated_activities,
                    'pagination': {
                        'page': page,
                        'limit': limit,
                        'total': total,
                        'total_pages': total_pages,
                        'has_prev': page > 1,
                        'has_next': page < total_pages
                    }
                }
                
                self.send_json_response(response)
                
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

    def handle_export_infra_analytics(self):
        """
        GET /api/v1/reports/exports/infra-analytics
        Exporta XLSX estrategico com colaboradores ativos e dados de folha/beneficios.
        Query params opcionais:
        - year (default: 2025)
        - month (default: 12)
        - company (default: 0059)
        - payroll_type (default: mensal)
        - department (default: sem filtro)
        - employee_id (default: sem filtro)
        """
        try:
            query_params = self.parse_query_params()
            year = int(query_params.get('year', ['2025'])[0])
            month = int(query_params.get('month', ['12'])[0])
            company = str(query_params.get('company', ['0059'])[0]).strip() or '0059'
            payroll_type = str(query_params.get('payroll_type', ['mensal'])[0]).strip() or 'mensal'
            department = str(query_params.get('department', [''])[0]).strip() or None

            employee_id_raw = str(query_params.get('employee_id', [''])[0]).strip()
            employee_id = int(employee_id_raw) if employee_id_raw else None

            if month < 1 or month > 12:
                self.send_error_response(400, 'Parâmetro month deve estar entre 1 e 12')
                return

            allowed_payroll_types = {
                'mensal',
                '13_adiantamento',
                '13_integral',
                'complementar',
                'adiantamento_salario',
                'all',
            }
            if payroll_type not in allowed_payroll_types:
                self.send_error_response(400, 'Parâmetro payroll_type inválido')
                return

            db = next(get_db())
            try:
                xlsx_bytes, total_rows, filename = build_infra_analytics_xlsx(
                    session=db,
                    year=year,
                    month=month,
                    company=company,
                    payroll_type=payroll_type,
                    department=department,
                    employee_id=employee_id,
                )

                print(
                    f"📊 Relatório exportável gerado: company={company}, year={year}, month={month}, payroll_type={payroll_type}, department={department}, employee_id={employee_id}, rows={total_rows}"
                )
                self.send_binary_response(
                    data=xlsx_bytes,
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    filename=filename,
                )
            finally:
                db.close()

        except ValueError:
            self.send_error_response(400, 'Parâmetros inválidos para geração do relatório')
        except Exception as e:
            print(f"❌ Erro ao exportar relatório estratégico: {str(e)}")
            import traceback
            traceback.print_exc()
            self.send_error_response(500, 'Erro ao exportar relatório estratégico')
    
    def send_error_response(self, status_code: int, message: str):
        """Enviar resposta de erro"""
        self.send_json_response({"error": message}, status_code)
    
    def parse_query_params(self):
        """Extrair parâmetros da query string"""
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(self.path)
        return parse_qs(parsed.query)
