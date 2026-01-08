"""
Authentication Handler - Lógica de negócio para autenticação
"""
import sys
import os
from datetime import datetime, timezone, timedelta


class AuthHandler:
    """Handler para operações de autenticação"""
    
    def __init__(self, db_session, request_handler):
        """
        Args:
            db_session: Sessão do banco de dados (SessionLocal)
            request_handler: Instância do HTTP request handler
        """
        self.db = db_session
        self.handler = request_handler
    
    def login(self, username: str, password: str) -> dict:
        """
        Autentica usuário e retorna token JWT
        
        Args:
            username: Nome de usuário
            password: Senha
            
        Returns:
            dict com access_token e dados do usuário
            
        Raises:
            ValueError: Se credenciais inválidas ou usuário inativo
        """
        print(f"🔐 Tentativa de login - Username: '{username}'")
        
        # Tentar autenticação com PostgreSQL
        if self.db:
            try:
                sys.path.append(os.path.dirname(__file__))
                from app.models import User
                
                user = self.db.query(User).filter(User.username == username).first()
                
                if user and user.is_active and user.verify_password(password):
                    # Atualizar último acesso
                    from app.core.auth import create_access_token
                    
                    brazil_tz = timezone(timedelta(hours=-3))
                    user.last_login = datetime.now(brazil_tz)
                    self.db.commit()
                    
                    # Gerar JWT token com user_id
                    token_data = {
                        "sub": user.username,
                        "user_id": user.id,
                        "email": user.email,
                        "is_admin": user.is_admin
                    }
                    print(f"🔐 Dados do token JWT (AuthHandler): {token_data}")
                    access_token = create_access_token(data=token_data)
                    
                    print("✅ Login bem-sucedido com PostgreSQL!")
                    return {
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
                    }
                else:
                    if user and not user.is_active:
                        print("❌ Usuário inativo no PostgreSQL!")
                        raise ValueError("Usuário inativo ou removido")
                    else:
                        print("❌ Credenciais inválidas no PostgreSQL!")
                        raise ValueError("Credenciais inválidas")
                        
            except ValueError:
                raise
            except Exception as e:
                print(f"❌ Erro na autenticação PostgreSQL: {e}")
                # Fallback para credenciais padrão
        
        # Fallback para credenciais padrão
        if username == 'admin' and password == 'admin123':
            print("✅ Login bem-sucedido com credenciais padrão!")
            return {
                "access_token": "simple-token-123",
                "token_type": "bearer",
                "user": {
                    "id": 1,
                    "username": "admin",
                    "full_name": "Administrador",
                    "email": "admin@empresa.com",
                    "is_admin": True
                }
            }
        else:
            print("❌ Credenciais inválidas!")
            raise ValueError("Credenciais inválidas")
    
    def get_current_user(self) -> dict:
        """
        Retorna dados do usuário autenticado
        
        Returns:
            dict com dados do usuário
            
        Raises:
            ValueError: Se token inválido ou usuário não encontrado
        """
        if not self.db:
            raise ValueError("Token de acesso necessário")
        
        # Buscar usuário autenticado (método do handler)
        user = self.handler.get_authenticated_user(self.db)
        
        if not user:
            raise ValueError("Token de acesso necessário")
        
        return {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email,
            "is_admin": user.is_admin,
            "role": user.role
        }
