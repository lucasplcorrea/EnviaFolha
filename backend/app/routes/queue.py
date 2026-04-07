"""HTTP router for send queue endpoints used by the frontend."""

from app.routes.base import BaseRouter
from app.services.runtime_compat import SessionLocal
from app.services.queue_manager import QueueManagerService


class QueueRouter(BaseRouter):
    def handle_get(self, path: str):
        if path == '/api/v1/queue/active':
            self.handle_get_active_queues()
            return

        if path == '/api/v1/queue/list':
            self.handle_get_all_queues()
            return

        if path == '/api/v1/queue/statistics':
            self.handle_get_queue_statistics()
            return

        if path.startswith('/api/v1/queue/') and path.endswith('/details'):
            queue_id = path.split('/')[-2]
            self.handle_get_queue_details(queue_id)
            return

        self.send_error('Endpoint não encontrado', 404)

    def handle_post(self, path: str):
        if path.startswith('/api/v1/queue/') and path.endswith('/cancel'):
            queue_id = path.split('/')[-2]
            self.handle_cancel_queue(queue_id)
            return

        if path.startswith('/api/v1/queue/') and path.endswith('/pause'):
            queue_id = path.split('/')[-2]
            self.handle_pause_queue(queue_id)
            return

        if path.startswith('/api/v1/queue/') and path.endswith('/resume'):
            queue_id = path.split('/')[-2]
            self.handle_resume_queue(queue_id)
            return

        self.send_error('Endpoint não encontrado', 404)

    def _get_user_id(self):
        user = self.handler.get_authenticated_user()
        return user.id if user else 0

    def handle_get_active_queues(self):
        db = SessionLocal()
        try:
            service = QueueManagerService(db)
            queues = service.get_active_queues()
            self.send_json_response({'queues': queues})
        except Exception as ex:
            self.send_json_response({'error': str(ex)}, 500)
        finally:
            db.close()

    def handle_get_all_queues(self):
        db = SessionLocal()
        try:
            from urllib.parse import parse_qs, urlparse

            query_params = parse_qs(urlparse(self.handler.path).query)
            limit = int(query_params.get('limit', ['50'])[0])
            status_filter = query_params.get('status', [None])[0]
            queue_type_filter = query_params.get('type', [None])[0]

            if status_filter == 'all':
                status_filter = None
            if queue_type_filter == 'all':
                queue_type_filter = None

            service = QueueManagerService(db)
            queues = service.get_all_queues(
                limit=max(1, min(limit, 200)),
                status_filter=status_filter,
                queue_type_filter=queue_type_filter,
            )
            self.send_json_response({'queues': queues})
        except Exception as ex:
            self.send_json_response({'error': str(ex)}, 500)
        finally:
            db.close()

    def handle_get_queue_statistics(self):
        db = SessionLocal()
        try:
            service = QueueManagerService(db)
            stats = service.get_queue_statistics()
            self.send_json_response(stats)
        except Exception as ex:
            self.send_json_response({'error': str(ex)}, 500)
        finally:
            db.close()

    def handle_get_queue_details(self, queue_id: str):
        db = SessionLocal()
        try:
            service = QueueManagerService(db)
            details = service.get_queue_details(queue_id)
            if not details:
                self.send_json_response({'error': 'Fila não encontrada'}, 404)
                return
            self.send_json_response(details)
        except Exception as ex:
            self.send_json_response({'error': str(ex)}, 500)
        finally:
            db.close()

    def handle_cancel_queue(self, queue_id: str):
        db = SessionLocal()
        try:
            service = QueueManagerService(db)
            ok = service.cancel_queue(queue_id, self._get_user_id())
            if not ok:
                self.send_json_response({'error': 'Fila não encontrada ou não pode ser cancelada'}, 400)
                return
            self.send_json_response({'success': True, 'message': 'Fila cancelada com sucesso'})
        except Exception as ex:
            self.send_json_response({'error': str(ex)}, 500)
        finally:
            db.close()

    def handle_pause_queue(self, queue_id: str):
        db = SessionLocal()
        try:
            service = QueueManagerService(db)
            ok = service.pause_queue(queue_id, self._get_user_id())
            if not ok:
                self.send_json_response({'error': 'Fila não encontrada ou não pode ser pausada'}, 400)
                return
            self.send_json_response({'success': True, 'message': 'Fila pausada com sucesso'})
        except Exception as ex:
            self.send_json_response({'error': str(ex)}, 500)
        finally:
            db.close()

    def handle_resume_queue(self, queue_id: str):
        db = SessionLocal()
        try:
            service = QueueManagerService(db)
            ok = service.resume_queue(queue_id, self._get_user_id())
            if not ok:
                self.send_json_response({'error': 'Fila não encontrada ou não pode ser retomada'}, 400)
                return
            self.send_json_response({'success': True, 'message': 'Fila retomada com sucesso'})
        except Exception as ex:
            self.send_json_response({'error': str(ex)}, 500)
        finally:
            db.close()
