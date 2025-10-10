"""
Serviço para gerenciamento de usuários e permissões
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Dict, Optional
import logging

# Imports dos modelos
from app.models.user import User
from app.models.permission import Permission, Role, RolePermission
from app.core.auth import get_password_hash

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserManagementService:
    """Serviço para gerenciar usuários, papéis e permissões"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def create_default_permissions(self):
        """Cria as permissões padrão do sistema"""
        from ..models.permission import Permission
        
        default_permissions = [
            # Módulo de Colaboradores
            {"name": "employees.read", "description": "Visualizar colaboradores", "module": "employees", "action": "read"},
            {"name": "employees.write", "description": "Criar/editar colaboradores", "module": "employees", "action": "write"},
            {"name": "employees.delete", "description": "Excluir colaboradores", "module": "employees", "action": "delete"},
            {"name": "employees.bulk", "description": "Operações em lote em colaboradores", "module": "employees", "action": "bulk"},
            
            # Módulo de Folha de Pagamento
            {"name": "payroll.read", "description": "Visualizar folha de pagamento", "module": "payroll", "action": "read"},
            {"name": "payroll.process", "description": "Processar folhas de pagamento", "module": "payroll", "action": "process"},
            {"name": "payroll.send", "description": "Enviar holerites por WhatsApp", "module": "payroll", "action": "send"},
            
            # Módulo de Comunicações
            {"name": "communications.read", "description": "Visualizar comunicações", "module": "communications", "action": "read"},
            {"name": "communications.send", "description": "Enviar comunicações", "module": "communications", "action": "send"},
            
            # Módulo de Relatórios
            {"name": "reports.read", "description": "Visualizar relatórios", "module": "reports", "action": "read"},
            {"name": "reports.export", "description": "Exportar relatórios", "module": "reports", "action": "export"},
            
            # Módulo de Configurações
            {"name": "settings.read", "description": "Visualizar configurações", "module": "settings", "action": "read"},
            {"name": "settings.write", "description": "Alterar configurações", "module": "settings", "action": "write"},
            
            # Módulo de Usuários (Admin)
            {"name": "users.read", "description": "Visualizar usuários", "module": "users", "action": "read"},
            {"name": "users.write", "description": "Criar/editar usuários", "module": "users", "action": "write"},
            {"name": "users.delete", "description": "Excluir usuários", "module": "users", "action": "delete"},
            {"name": "users.permissions", "description": "Gerenciar permissões de usuários", "module": "users", "action": "permissions"},
            
            # Módulo de Dashboard
            {"name": "dashboard.read", "description": "Visualizar dashboard", "module": "dashboard", "action": "read"},
        ]
        
        created_permissions = []
        for perm_data in default_permissions:
            existing = self.db.query(Permission).filter(Permission.name == perm_data["name"]).first()
            if not existing:
                permission = Permission(**perm_data)
                self.db.add(permission)
                created_permissions.append(perm_data["name"])
        
        self.db.commit()
        logger.info(f"Criadas {len(created_permissions)} permissões padrão")
        return created_permissions
    
    def create_default_roles(self):
        """Cria os papéis padrão do sistema"""
        from ..models.permission import Role, RolePermission, Permission
        
        # Criar papéis padrão
        roles_data = [
            {
                "name": "admin",
                "description": "Administrador com acesso total ao sistema",
                "permissions": ["*"]  # Todas as permissões
            },
            {
                "name": "manager", 
                "description": "Gerente de RH com acesso a operações principais",
                "permissions": [
                    "employees.read", "employees.write", "employees.bulk",
                    "payroll.read", "payroll.process", "payroll.send",
                    "communications.read", "communications.send",
                    "reports.read", "reports.export",
                    "dashboard.read"
                ]
            },
            {
                "name": "operator",
                "description": "Operador com acesso a funções básicas",
                "permissions": [
                    "employees.read", "employees.write",
                    "payroll.read", "payroll.send",
                    "communications.read", "communications.send",
                    "dashboard.read"
                ]
            },
            {
                "name": "viewer",
                "description": "Visualizador com acesso somente leitura",
                "permissions": [
                    "employees.read",
                    "payroll.read", 
                    "communications.read",
                    "reports.read",
                    "dashboard.read"
                ]
            }
        ]
        
        created_roles = []
        for role_data in roles_data:
            existing = self.db.query(Role).filter(Role.name == role_data["name"]).first()
            if not existing:
                role = Role(name=role_data["name"], description=role_data["description"])
                self.db.add(role)
                self.db.flush()  # Para obter o ID
                
                # Adicionar permissões ao papel
                if role_data["permissions"] == ["*"]:
                    # Admin tem todas as permissões
                    all_permissions = self.db.query(Permission).filter(Permission.is_active == True).all()
                    for permission in all_permissions:
                        role_perm = RolePermission(role_id=role.id, permission_id=permission.id)
                        self.db.add(role_perm)
                else:
                    # Adicionar permissões específicas
                    for perm_name in role_data["permissions"]:
                        permission = self.db.query(Permission).filter(Permission.name == perm_name).first()
                        if permission:
                            role_perm = RolePermission(role_id=role.id, permission_id=permission.id)
                            self.db.add(role_perm)
                
                created_roles.append(role_data["name"])
        
        self.db.commit()
        logger.info(f"Criados {len(created_roles)} papéis padrão")
        return created_roles
    
    def create_user(self, user_data: Dict) -> Dict:
        """Cria um novo usuário"""
        from ..models.user import User
        from ..models.permission import Role
        
        try:
            # Verificar se usuário já existe
            existing = self.db.query(User).filter(
                (User.username == user_data["username"]) | 
                (User.email == user_data["email"])
            ).first()
            
            if existing:
                return {"success": False, "message": "Usuário com este username ou email já existe"}
            
            # Criar usuário
            new_user = User(
                username=user_data["username"],
                email=user_data["email"],
                full_name=user_data["full_name"],
                password_hash=User.hash_password(user_data["password"]),
                is_active=user_data.get("is_active", True),
                is_admin=user_data.get("is_admin", False)
            )
            
            # Associar papel se fornecido
            if user_data.get("role_name"):
                role = self.db.query(Role).filter(Role.name == user_data["role_name"]).first()
                if role:
                    new_user.role_id = role.id
            
            self.db.add(new_user)
            self.db.commit()
            
            logger.info(f"Usuário {user_data['username']} criado com sucesso")
            return {"success": True, "message": "Usuário criado com sucesso", "user_id": new_user.id}
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar usuário: {str(e)}")
            return {"success": False, "message": f"Erro ao criar usuário: {str(e)}"}
    
    def update_user_permissions(self, user_id: int, permission_names: List[str]) -> Dict:
        """Atualiza as permissões diretas de um usuário"""
        from ..models.user import User
        from ..models.permission import Permission
        
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "message": "Usuário não encontrado"}
            
            # Limpar permissões atuais
            user.permissions.clear()
            
            # Adicionar novas permissões
            for perm_name in permission_names:
                permission = self.db.query(Permission).filter(Permission.name == perm_name).first()
                if permission:
                    user.permissions.append(permission)
            
            self.db.commit()
            
            logger.info(f"Permissões do usuário {user.username} atualizadas")
            return {"success": True, "message": "Permissões atualizadas com sucesso"}
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao atualizar permissões: {str(e)}")
            return {"success": False, "message": f"Erro ao atualizar permissões: {str(e)}"}
    
    def get_all_users(self) -> List[Dict]:
        """Retorna lista de todos os usuários com suas permissões"""
        from ..models.user import User
        
        users = self.db.query(User).filter(User.is_active == True).all()
        
        users_list = []
        for user in users:
            user_dict = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "is_admin": user.is_admin,
                "role": user.role.name if user.role else None,
                "permissions": user.get_user_permissions(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "created_at": user.created_at.isoformat() if hasattr(user, 'created_at') else None
            }
            users_list.append(user_dict)
        
        return users_list
    
    def get_available_permissions(self) -> Dict:
        """Retorna todas as permissões disponíveis organizadas por módulo"""
        from ..models.permission import Permission
        
        permissions = self.db.query(Permission).filter(Permission.is_active == True).all()
        
        modules = {}
        for permission in permissions:
            if permission.module not in modules:
                modules[permission.module] = []
            
            modules[permission.module].append({
                "id": permission.id,
                "name": permission.name,
                "description": permission.description,
                "action": permission.action
            })
        
        return modules
    
    def initialize_system(self):
        """Inicializa permissões e papéis padrão do sistema se ainda não existirem"""
        try:
            # Verificar se já existem permissões (significa que já foi inicializado)
            existing_permissions = self.db.query(Permission).first()
            if existing_permissions:
                logger.debug("Sistema de permissões já foi inicializado anteriormente")
                return
                
            logger.info("Inicializando sistema de permissões...")
            
            # Criar permissões padrão
            self.create_default_permissions()
            
            # Criar papéis padrão
            self.create_default_roles()
            
            logger.info("Sistema de permissões inicializado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao inicializar sistema de permissões: {e}")
            self.db.rollback()

    def update_user(self, user_id: int, update_data: dict):
        """Atualizar dados de um usuário"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "message": "Usuário não encontrado"}
            
            # Validar username único se estiver sendo alterado
            if 'username' in update_data and update_data['username'] != user.username:
                existing_user = self.db.query(User).filter(
                    User.username == update_data['username'],
                    User.id != user_id
                ).first()
                if existing_user:
                    return {"success": False, "message": "Nome de usuário já existe"}
            
            # Validar email único se estiver sendo alterado
            if 'email' in update_data and update_data['email'] != user.email:
                existing_email = self.db.query(User).filter(
                    User.email == update_data['email'],
                    User.id != user_id
                ).first()
                if existing_email:
                    return {"success": False, "message": "Email já está em uso"}
            
            # Atualizar campos
            for field, value in update_data.items():
                if hasattr(user, field):
                    setattr(user, field, value)
            
            self.db.commit()
            
            return {
                "success": True,
                "message": "Usuário atualizado com sucesso",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "is_active": user.is_active,
                    "created_at": user.created_at.isoformat() if user.created_at else None
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao atualizar usuário: {e}")
            self.db.rollback()
            return {"success": False, "message": f"Erro interno: {str(e)}"}

    def delete_user(self, user_id: int):
        """Deletar um usuário"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "message": "Usuário não encontrado"}
            
            # Não permitir deletar usuário admin principal
            if user.username == 'admin':
                return {"success": False, "message": "Não é possível deletar o usuário admin principal"}
            
            # Verificar se é o último usuário ativo
            active_users_count = self.db.query(User).filter(User.is_active == True).count()
            if active_users_count <= 1 and user.is_active:
                return {"success": False, "message": "Não é possível deletar o último usuário ativo"}
            
            username = user.username
            self.db.delete(user)
            self.db.commit()
            
            return {
                "success": True,
                "message": f"Usuário '{username}' deletado com sucesso"
            }
            
        except Exception as e:
            logger.error(f"Erro ao deletar usuário: {e}")
            self.db.rollback()
            return {"success": False, "message": f"Erro interno: {str(e)}"}

    def get_user_by_id(self, user_id: int):
        """Buscar usuário por ID"""
        try:
            return self.db.query(User).filter(User.id == user_id).first()
        except Exception as e:
            logger.error(f"Erro ao buscar usuário: {e}")
            return None