"""Administrative utility-script endpoints."""

from app.models.base import SessionLocal
from app.routes.base import BaseRouter
from app.services.utility_scripts import UtilityScriptsService


class UtilityScriptsRouter(BaseRouter):
    def _admin_session(self):
        db = SessionLocal()
        user = self.handler.get_authenticated_user(db)
        if not user:
            db.close()
            self.send_json_response({'error': 'Autenticação necessária'}, 401)
            return None, None
        if not user.is_admin:
            db.close()
            self.send_json_response({'error': 'Apenas administradores podem executar scripts'}, 403)
            return None, None
        return db, user

    def handle_preview(self, script_id: str):
        db, _ = self._admin_session()
        if db is None:
            return
        try:
            self.send_json_response(UtilityScriptsService(db).preview_script(script_id))
        except ValueError as ex:
            self.send_json_response({'error': str(ex)}, 404)
        except Exception as ex:
            self.send_json_response({'error': f'Erro ao gerar preview: {str(ex)}'}, 500)
        finally:
            db.close()

    def handle_execute(self, script_id: str):
        db, _ = self._admin_session()
        if db is None:
            return
        try:
            self.send_json_response(UtilityScriptsService(db).execute_script(script_id))
        except ValueError as ex:
            self.send_json_response({'error': str(ex)}, 404)
        except Exception as ex:
            db.rollback()
            self.send_json_response({'error': f'Erro ao executar script: {str(ex)}'}, 500)
        finally:
            db.close()
