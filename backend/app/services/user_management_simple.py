"""
Serviço simplificado para gerenciamento de usuários com sistema de páginas
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Dict, Optional
import logging
import json

# Imports dos modelos
from app.models.user import User
from app.models.role_simple import Role

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserManagementServiceSimple:
    """Serviço simplificado para gerenciar usuários e roles com páginas"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def initialize_system(self):
        """Método compatibilidade - não faz nada no sistema simplificado"""
        pass
    
    def get_all_users(self) -> List[Dict]:
        """Retorna todos os usuários ativos com suas informações básicas"""
        users = self.db.query(User).filter(User.is_active == True).all()
        result = []
        
        for user in users:
            user_data = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "is_admin": user.is_admin,
                "is_active": user.is_active,
                "role_id": user.role_id,
                "role_name": user.role.name if user.role else None,
                "role_description": user.role.description if user.role else None,
                "allowed_pages": user.get_allowed_pages(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
            result.append(user_data)
            
        return result
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Retorna um usuário específico por ID (dicionário para compatibilidade)"""
        user = self.db.query(User).filter(
            and_(User.id == user_id, User.is_active == True)
        ).first()
        
        if not user:
            return None
            
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_admin": user.is_admin,
            "is_active": user.is_active,
            "role_id": user.role_id,
            "role_name": user.role.name if user.role else None,
            "role_description": user.role.description if user.role else None,
            "allowed_pages": user.get_allowed_pages(),
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
    
    def get_user_object_by_id(self, user_id: int) -> Optional[User]:
        """Retorna um usuário específico por ID (objeto User)"""
        return self.db.query(User).filter(
            and_(User.id == user_id, User.is_active == True)
        ).first()
    
    def create_user(self, user_data: Dict) -> Dict:
        """Cria um novo usuário"""
        try:
            # Verificar se username/email já existem
            existing_user = self.db.query(User).filter(
                (User.username == user_data["username"]) | 
                (User.email == user_data["email"])
            ).first()
            
            if existing_user:
                raise ValueError("Username ou email já existe")
            
            # Verificar se role existe
            role = None
            if user_data.get("role_id"):
                role = self.db.query(Role).filter(Role.id == user_data["role_id"]).first()
                if not role:
                    raise ValueError("Role especificado não existe")
            
            # Criar usuário
            new_user = User(
                username=user_data["username"],
                email=user_data["email"],
                full_name=user_data["full_name"],
                password_hash=User.hash_password(user_data["password"]),
                is_admin=user_data.get("is_admin", False),
                role_id=user_data.get("role_id")
            )
            
            self.db.add(new_user)
            self.db.commit()
            self.db.refresh(new_user)
            
            print(f"Usuário criado: {new_user.username}")
            return {
                "success": True,
                "message": "Usuário criado com sucesso"
            }
            
        except Exception as e:
            self.db.rollback()
            print(f"Erro ao criar usuário: {e}")
            return {"success": False, "error": str(e)}
    
    def update_user(self, user_id: int, user_data: Dict) -> Dict:
        """Atualiza um usuário existente"""
        try:
            user = self.get_user_object_by_id(user_id)
            
            if not user:
                return {"success": False, "error": "Usuário não encontrado"}
            
            # Verificar role se fornecido
            if "role_id" in user_data and user_data["role_id"]:
                role = self.db.query(Role).filter(Role.id == user_data["role_id"]).first()
                if not role:
                    return {"success": False, "error": "Role especificado não existe"}
            
            # Atualizar campos
            if "username" in user_data:
                user.username = user_data["username"]
            if "email" in user_data:
                user.email = user_data["email"]
            if "full_name" in user_data:
                user.full_name = user_data["full_name"]
            if "password_hash" in user_data:
                user.password_hash = user_data["password_hash"]
            if "is_admin" in user_data:
                user.is_admin = user_data["is_admin"]
            if "role_id" in user_data:
                user.role_id = user_data["role_id"]
            
            self.db.commit()
            self.db.refresh(user)
            
            print(f"Usuário atualizado: {user.username}")
            return {
                "success": True,
                "message": "Usuário atualizado com sucesso"
            }
            
        except Exception as e:
            self.db.rollback()
            print(f"Erro ao atualizar usuário: {e}")
            return {"success": False, "error": str(e)}
    
    def delete_user(self, user_id: int) -> Dict:
        """Deleta um usuário (marca como inativo)"""
        try:
            user = self.db.query(User).filter(
                and_(User.id == user_id, User.is_active == True)
            ).first()
            
            if not user:
                return {"success": False, "message": "Usuário não encontrado"}
            
            # Soft delete - marca como inativo
            user.is_active = False
            self.db.commit()
            
            print(f"Usuário deletado (inativo): {user.username}")
            return {"success": True, "message": "Usuário deletado com sucesso"}
            
        except Exception as e:
            self.db.rollback()
            print(f"Erro ao deletar usuário: {e}")
            return {"success": False, "message": f"Erro ao deletar usuário: {str(e)}"}
    
    def get_all_roles(self) -> List[Dict]:
        """Retorna todos os roles disponíveis"""
        roles = self.db.query(Role).filter(Role.is_active == True).all()
        return [
            {
                "id": role.id,
                "name": role.name,
                "description": role.description,
                "allowed_pages": role.get_allowed_pages(),
                "is_active": role.is_active
            }
            for role in roles
        ]
    
    def get_available_permissions(self) -> List[Dict]:
        """Retorna permissões disponíveis (compatibilidade) - sistema simplificado usa apenas roles"""
        return [
            {"name": "dashboard.view", "description": "Visualizar dashboard"},
            {"name": "employees.view", "description": "Visualizar colaboradores"},
            {"name": "payroll.view", "description": "Visualizar folha de pagamento"},
            {"name": "communications.view", "description": "Visualizar comunicações"},
            {"name": "reports.view", "description": "Visualizar relatórios"},
            {"name": "users.manage", "description": "Gerenciar usuários (apenas admin)"},
            {"name": "settings.manage", "description": "Gerenciar configurações"}
        ]
    
    def get_role_by_name(self, role_name: str) -> Optional[Role]:
        """Busca um role pelo nome"""
        return self.db.query(Role).filter(
            and_(Role.name == role_name, Role.is_active == True)
        ).first()
    
    def get_role_id_by_name(self, role_name: str) -> Optional[int]:
        """Retorna o ID de um role pelo nome"""
        role = self.get_role_by_name(role_name)
        return role.id if role else None
    
    def check_user_page_access(self, user_id: int, page_name: str) -> bool:
        """Verifica se um usuário pode acessar uma página específica"""
        user = self.db.query(User).filter(
            and_(User.id == user_id, User.is_active == True)
        ).first()
        
        if not user:
            return False
        
        return user.can_access_page(page_name)

# Função helper para importação no main.py
def get_user_management_service(db_session: Session) -> UserManagementServiceSimple:
    """Factory function para criar instância do serviço"""
    return UserManagementServiceSimple(db_session)