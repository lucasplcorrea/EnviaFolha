"""Communication delivery endpoint recovered from the former monolith."""

import asyncio
from datetime import datetime
from pathlib import Path

from app.models.base import SessionLocal
from app.models.communication_recipient import CommunicationRecipient
from app.models.communication_send import CommunicationSend
from app.models.employee import Employee
from app.routes.base import BaseRouter
from app.services.evolution_api import EvolutionAPIService
from app.services.instance_manager import get_instance_manager
from app.services.phone_validator import PhoneValidator


class CommunicationsRouter(BaseRouter):
    @staticmethod
    def _resolve_attachment(uploaded_file):
        if not uploaded_file:
            return None
        candidate = uploaded_file.get('file_path') or uploaded_file.get('filepath')
        if not candidate:
            return None
        path = Path(candidate).resolve()
        uploads_root = (Path(__file__).resolve().parents[2] / 'uploads').resolve()
        try:
            path.relative_to(uploads_root)
        except ValueError:
            return None
        return str(path) if path.is_file() else None

    def handle_send(self):
        db = SessionLocal()
        loop = asyncio.new_event_loop()
        try:
            user = self.handler.get_authenticated_user(db)
            if not user:
                self.send_json_response({'error': 'Usuário não autenticado'}, 401)
                return

            data = self.get_request_data()
            selected_ids = data.get('selectedEmployees') or []
            message = str(data.get('message') or '').strip()
            uploaded_file = data.get('uploadedFile') or None
            file_path = self._resolve_attachment(uploaded_file)
            if not selected_ids:
                self.send_json_response({'error': 'Nenhum colaborador selecionado'}, 400)
                return
            if not message and not file_path:
                self.send_json_response({'error': 'É necessário enviar uma mensagem ou arquivo válido'}, 400)
                return

            employees = db.query(Employee).filter(Employee.id.in_(selected_ids), Employee.is_active == True).all()
            by_id = {employee.id: employee for employee in employees}
            batch = CommunicationSend(
                user_id=user.id,
                title=(message[:80] if message else Path(file_path).name),
                message=message or None,
                file_path=file_path,
                total_recipients=len(selected_ids),
                successful_sends=0,
                failed_sends=0,
                status='sending',
                started_at=datetime.now(),
            )
            db.add(batch)
            db.commit()
            db.refresh(batch)

            manager = get_instance_manager()
            failed = []
            successful = 0
            asyncio.set_event_loop(loop)
            for employee_id in selected_ids:
                employee = by_id.get(employee_id)
                error = None
                formatted_phone = None
                if not employee:
                    error = 'Colaborador ativo não encontrado'
                else:
                    valid, formatted_phone, phone_error = PhoneValidator.validate_and_format(employee.phone)
                    if not valid:
                        error = f'Telefone inválido: {phone_error or "formato_invalido"}'

                result = None
                if not error:
                    instance = loop.run_until_complete(manager.get_next_available_instance())
                    if not instance:
                        error = 'Nenhuma instância WhatsApp online'
                    else:
                        result = loop.run_until_complete(
                            EvolutionAPIService(instance_name=instance).send_communication_message(
                                phone=formatted_phone,
                                message_text=message or None,
                                file_path=file_path,
                            )
                        )
                        if not result.get('success'):
                            error = result.get('message') or 'Falha no envio'

                if employee:
                    recipient = CommunicationRecipient(
                        communication_send_id=batch.id,
                        employee_id=employee.id,
                        status='failed' if error else 'sent',
                        sent_at=datetime.now() if not error else None,
                        error_message=error,
                    )
                    db.add(recipient)
                if error:
                    failed.append({
                        'id': employee_id,
                        'name': employee.name if employee else None,
                        'reason': error,
                    })
                else:
                    successful += 1

            batch.successful_sends = successful
            batch.failed_sends = len(failed)
            batch.status = 'completed' if not failed else ('failed' if not successful else 'completed_with_errors')
            batch.completed_at = datetime.now()
            db.commit()
            self.send_json_response({
                'success_count': successful,
                'failed_count': len(failed),
                'failed_employees': failed,
                'message': f'{successful} comunicado(s) enviado(s) com sucesso',
            })
        except Exception as ex:
            db.rollback()
            self.send_json_response({'error': f'Erro ao enviar comunicado: {str(ex)}'}, 500)
        finally:
            loop.close()
            db.close()
