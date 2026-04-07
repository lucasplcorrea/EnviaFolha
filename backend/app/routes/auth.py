"""
Authentication Routes - Rotas de autenticação
"""
from .base import BaseRouter
from app.services.runtime_compat import SessionLocal


class AuthRouter(BaseRouter):
    """Router para endpoints de autenticação"""
    
    def handle_login(self):
        """
        POST /api/v1/auth/login
        Autenticar usuário e retornar JWT token
        """
        try:
            data = self.get_request_data()
            username = data.get('username')
            password = data.get('password')
            
            if not username or not password:
                self.send_error("Username e password são obrigatórios", 400)
                return
            
            print(f"🔐 Tentativa de login - Username: '{username}'")
            
            # Verificar no PostgreSQL se disponível
            if SessionLocal:
                try:
                    from app.models import User
                    from datetime import datetime, timezone, timedelta
                    from app.core.auth import create_access_token
                    
                    db = SessionLocal()
                    user = db.query(User).filter(User.username == username).first()
                    
                    if user and user.is_active and user.verify_password(password):
                        # Atualizar o último acesso
                        brazil_tz = timezone(timedelta(hours=-3))  # GMT-3 (Brasília)
                        user.last_login = datetime.now(brazil_tz)
                        db.commit()
                        
                        # Gerar JWT token com user_id
                        token_data = {
                            "sub": user.username,
                            "user_id": user.id,
                            "email": user.email,
                            "is_admin": user.is_admin
                        }
                        print(f"🔐 Dados do token JWT (routes.auth): {token_data}")
                        access_token = create_access_token(data=token_data)
                        
                        print("✅ Login bem-sucedido com PostgreSQL!")
                        self.send_json_response({
                            "access_token": access_token,
                            "token_type": "bearer",
                            "user": {
                                "id": user.id,
                                "username": user.username,
                                "full_name": user.full_name,
                                "email": user.email,
                                "is_admin": user.is_admin,
                                "role": user.role.name if user.role else None
                            }
                        })
                        db.close()
                        return
                    else:
                        if user and not user.is_active:
                            print("❌ Usuário inativo no PostgreSQL!")
                            db.close()
                            self.send_error("Usuário inativo ou removido", 401)
                            return
                        else:
                            print("❌ Credenciais inválidas no PostgreSQL!")
                            db.close()
                            self.send_error("Credenciais inválidas", 401)
                            return
                            
                except Exception as e:
                    print(f"❌ Erro na autenticação PostgreSQL: {e}")
                    if 'db' in locals():
                        db.close()
            
            print("❌ Credenciais inválidas!")
            self.send_error("Credenciais inválidas", 401)
                
        except Exception as e:
            print(f"❌ Erro no login: {e}")
            import traceback
            traceback.print_exc()
            self.send_error(f"Erro interno: {str(e)}", 500)
    
    def handle_auth_me(self):
        """
        GET /api/v1/auth/me
        Retornar dados do usuário autenticado
        """
        try:
            if not SessionLocal:
                self.send_error("Banco de dados não disponível", 503)
                return
            
            db = SessionLocal()
            try:
                # Buscar usuário autenticado
                user = self.handler.get_authenticated_user(db)
                
                if not user:
                    self.send_error("Token de acesso necessário", 401)
                    return
                
                # Retornar dados do usuário
                user_data = {
                    "id": user.id,
                    "username": user.username,
                    "full_name": user.full_name,
                    "email": user.email,
                    "is_admin": user.is_admin,
                    "role": user.role
                }
                self.send_json_response(user_data)
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Erro ao verificar usuário: {e}")
            import traceback
            traceback.print_exc()
            self.send_error(f"Erro interno: {str(e)}", 500)
