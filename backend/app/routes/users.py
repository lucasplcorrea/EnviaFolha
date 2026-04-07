"""HTTP router for users and roles management endpoints."""

from app.routes.base import BaseRouter
from app.services.runtime_compat import SessionLocal
from app.core.auth import get_password_hash
from app.models.user import User
from app.models.role_simple import Role


class UsersRouter(BaseRouter):
    def handle_get(self, path: str):
        if path == '/api/v1/users':
            self.handle_list_users()
            return

        if path == '/api/v1/roles':
            self.handle_list_roles()
            return

        if path == '/api/v1/users/permissions':
            self.handle_available_permissions()
            return

        self.send_error('Endpoint não encontrado', 404)

    def handle_post(self, path: str):
        if path == '/api/v1/users':
            self.handle_create_user()
            return

        if path == '/api/v1/users/permissions':
            self.handle_update_user_permissions()
            return

        self.send_error('Endpoint não encontrado', 404)

    def handle_put(self, path: str):
        if path.startswith('/api/v1/users/'):
            user_id = path.split('/')[-1]
            self.handle_update_user(user_id)
            return

        self.send_error('Endpoint não encontrado', 404)

    def handle_delete(self, path: str):
        if path.startswith('/api/v1/users/'):
            user_id = path.split('/')[-1]
            self.handle_delete_user(user_id)
            return

        self.send_error('Endpoint não encontrado', 404)

    @staticmethod
    def _serialize_user(user: User):
        return {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'is_active': user.is_active,
            'is_admin': user.is_admin,
            'role_id': user.role_id,
            'role_name': user.role.name if user.role else None,
            'role': user.role.name if user.role else None,
            'allowed_pages': user.get_allowed_pages(),
        }

    def handle_list_users(self):
        db = SessionLocal()
        try:
            users = db.query(User).order_by(User.username.asc()).all()
            users_data = [self._serialize_user(user) for user in users]
            self.send_json_response({'users': users_data, 'total': len(users_data)})
        except Exception as ex:
            self.send_json_response({'error': str(ex)}, 500)
        finally:
            db.close()

    def handle_list_roles(self):
        db = SessionLocal()
        try:
            roles = db.query(Role).filter(Role.is_active == True).order_by(Role.name.asc()).all()
            payload = []
            for role in roles:
                payload.append({
                    'id': role.id,
                    'name': role.name,
                    'description': role.description,
                    'is_active': role.is_active,
                    'allowed_pages': role.get_allowed_pages(),
                })
            self.send_json_response(payload)
        except Exception as ex:
            self.send_json_response({'error': str(ex)}, 500)
        finally:
            db.close()

    def handle_available_permissions(self):
        permissions = {
            'dashboard': 'Dashboard',
            'employees': 'Colaboradores',
            'payroll': 'Folha de Pagamento',
            'tax-statements': 'Informes de Rendimentos',
            'communications': 'Comunicados',
            'reports': 'Relatórios',
            'users': 'Usuários',
            'settings': 'Configurações',
        }
        self.send_json_response({'permissions': permissions})

    def _resolve_role(self, db, data):
        role_id = data.get('role_id')
        role_name = data.get('role_name')

        if role_id not in (None, ''):
            return db.query(Role).filter(Role.id == int(role_id), Role.is_active == True).first()

        if role_name:
            return db.query(Role).filter(Role.name == str(role_name).strip(), Role.is_active == True).first()

        return None

    def handle_create_user(self):
        db = SessionLocal()
        try:
            data = self.get_request_data()
            username = (data.get('username') or '').strip()
            email = (data.get('email') or '').strip().lower()
            full_name = (data.get('full_name') or '').strip()
            password = data.get('password') or ''

            if not username or not email or not full_name or not password:
                self.send_json_response({'success': False, 'message': 'Campos obrigatórios: username, email, full_name, password'}, 400)
                return

            existing = db.query(User).filter((User.username == username) | (User.email == email)).first()
            if existing:
                self.send_json_response({'success': False, 'message': 'Usuário ou email já existe'}, 400)
                return

            role = self._resolve_role(db, data)

            new_user = User(
                username=username,
                email=email,
                full_name=full_name,
                password_hash=get_password_hash(password),
                is_active=bool(data.get('is_active', True)),
                is_admin=bool(data.get('is_admin', False)),
                role_id=role.id if role else None,
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)

            self.send_json_response({'success': True, 'message': 'Usuário criado com sucesso', 'user': self._serialize_user(new_user)}, 201)
        except Exception as ex:
            db.rollback()
            self.send_json_response({'success': False, 'message': f'Erro ao criar usuário: {str(ex)}'}, 500)
        finally:
            db.close()

    def handle_update_user(self, user_id: str):
        db = SessionLocal()
        try:
            try:
                user_id_int = int(user_id)
            except ValueError:
                self.send_json_response({'success': False, 'message': 'ID de usuário inválido'}, 400)
                return

            user = db.query(User).filter(User.id == user_id_int).first()
            if not user:
                self.send_json_response({'success': False, 'message': 'Usuário não encontrado'}, 404)
                return

            data = self.get_request_data()

            if 'username' in data:
                user.username = (data.get('username') or '').strip() or user.username
            if 'email' in data:
                user.email = (data.get('email') or '').strip().lower() or user.email
            if 'full_name' in data:
                user.full_name = (data.get('full_name') or '').strip() or user.full_name
            if 'is_active' in data:
                user.is_active = bool(data.get('is_active'))
            if 'is_admin' in data:
                user.is_admin = bool(data.get('is_admin'))

            password = data.get('password')
            if password:
                user.password_hash = get_password_hash(password)

            role = self._resolve_role(db, data)
            if role is not None:
                user.role_id = role.id

            db.commit()
            db.refresh(user)

            self.send_json_response({'success': True, 'message': 'Usuário atualizado com sucesso', 'user': self._serialize_user(user)})
        except Exception as ex:
            db.rollback()
            self.send_json_response({'success': False, 'message': f'Erro ao atualizar usuário: {str(ex)}'}, 500)
        finally:
            db.close()

    def handle_delete_user(self, user_id: str):
        db = SessionLocal()
        try:
            try:
                user_id_int = int(user_id)
            except ValueError:
                self.send_json_response({'success': False, 'message': 'ID de usuário inválido'}, 400)
                return

            user = db.query(User).filter(User.id == user_id_int).first()
            if not user:
                self.send_json_response({'success': False, 'message': 'Usuário não encontrado'}, 404)
                return

            if user.username == 'admin':
                self.send_json_response({'success': False, 'message': 'Não é possível excluir o usuário admin'}, 400)
                return

            db.delete(user)
            db.commit()
            self.send_json_response({'success': True, 'message': 'Usuário excluído com sucesso'})
        except Exception as ex:
            db.rollback()
            self.send_json_response({'success': False, 'message': f'Erro ao excluir usuário: {str(ex)}'}, 500)
        finally:
            db.close()

    def handle_update_user_permissions(self):
        db = SessionLocal()
        try:
            data = self.get_request_data()
            user_id = data.get('user_id')
            permissions = data.get('permissions', [])

            if user_id in (None, ''):
                self.send_json_response({'success': False, 'message': 'user_id é obrigatório'}, 400)
                return

            try:
                user_id_int = int(user_id)
            except ValueError:
                self.send_json_response({'success': False, 'message': 'user_id inválido'}, 400)
                return

            user = db.query(User).filter(User.id == user_id_int).first()
            if not user:
                self.send_json_response({'success': False, 'message': 'Usuário não encontrado'}, 404)
                return

            if user.is_admin:
                self.send_json_response({'success': False, 'message': 'Permissões do admin não podem ser alteradas'}, 400)
                return

            role = user.role
            if not role:
                role = db.query(Role).filter(Role.name == 'viewer').first()
                if not role:
                    self.send_json_response({'success': False, 'message': 'Role padrão não encontrado'}, 400)
                    return
                user.role_id = role.id

            role.set_allowed_pages(permissions if isinstance(permissions, list) else [])
            db.commit()
            self.send_json_response({'success': True, 'message': 'Permissões atualizadas com sucesso'})
        except Exception as ex:
            db.rollback()
            self.send_json_response({'success': False, 'message': f'Erro ao atualizar permissões: {str(ex)}'}, 500)
        finally:
            db.close()
