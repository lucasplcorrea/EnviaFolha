"""HTTP router for endomarketing endpoints used by dashboard and RH pages."""

from app.routes.base import BaseRouter
from app.services.runtime_compat import SessionLocal
from app.services.endomarketing import EndomarketingService


class EndomarketingRouter(BaseRouter):
    def handle_get(self, path: str):
        if path == '/api/v1/endomarketing/summary':
            self.handle_summary()
            return

        if path == '/api/v1/endomarketing/birthdays':
            self.handle_birthdays()
            return

        if path == '/api/v1/endomarketing/work-anniversaries':
            self.handle_work_anniversaries()
            return

        if path == '/api/v1/endomarketing/probation':
            self.handle_probation()
            return

        self.send_error('Endpoint não encontrado', 404)

    def _service(self, db):
        return EndomarketingService(db)

    def _query_params(self):
        from urllib.parse import parse_qs, urlparse

        return parse_qs(urlparse(self.handler.path).query)

    def handle_summary(self):
        db = SessionLocal()
        try:
            data = self._service(db).get_dashboard_summary()
            self.send_json_response(data)
        except Exception as ex:
            self.send_json_response({'error': str(ex)}, 500)
        finally:
            db.close()

    def handle_birthdays(self):
        db = SessionLocal()
        try:
            period = self._query_params().get('period', ['month'])[0]
            data = self._service(db).get_birthday_employees(period=period)
            self.send_json_response(data)
        except Exception as ex:
            self.send_json_response({'error': str(ex)}, 500)
        finally:
            db.close()

    def handle_work_anniversaries(self):
        db = SessionLocal()
        try:
            period = self._query_params().get('period', ['month'])[0]
            data = self._service(db).get_work_anniversary_employees(period=period)
            self.send_json_response(data)
        except Exception as ex:
            self.send_json_response({'error': str(ex)}, 500)
        finally:
            db.close()

    def handle_probation(self):
        db = SessionLocal()
        try:
            phase_raw = self._query_params().get('phase', ['1'])[0]
            phase = int(phase_raw)
            if phase not in (1, 2):
                self.send_json_response({'error': 'phase deve ser 1 ou 2'}, 400)
                return
            data = self._service(db).get_probation_employees(phase=phase)
            self.send_json_response(data)
        except ValueError:
            self.send_json_response({'error': 'phase inválido'}, 400)
        except Exception as ex:
            self.send_json_response({'error': str(ex)}, 500)
        finally:
            db.close()
