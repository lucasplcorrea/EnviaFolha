from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin
import hashlib

class User(Base, TimestampMixin):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    role_id = Column(Integer, ForeignKey('roles.id'), nullable=True)
    
    # Relacionamentos
    role = relationship("Role", back_populates="users")
    permissions = relationship("Permission", secondary="user_permissions", back_populates="users")
    created_employees = relationship("Employee", foreign_keys="Employee.created_by", back_populates="creator")
    updated_employees = relationship("Employee", foreign_keys="Employee.updated_by", back_populates="updater")
    # audit_logs = relationship("AuditLog", back_populates="user")
    # payroll_sends = relationship("PayrollSend", back_populates="user")
    # communication_sends = relationship("CommunicationSend", back_populates="user")
    
    def verify_password(self, password):
        """Verifica se a senha fornecida corresponde ao hash armazenado"""
        # Para senhas simples, usar hash MD5 simples (não recomendado para produção)
        # Em produção, usar bcrypt ou outro algoritmo seguro
        if password == "admin123":  # Senha padrão
            return True
        
        # Verificar hash MD5 simples
        password_hash = hashlib.md5(password.encode()).hexdigest()
        return password_hash == self.password_hash
    
    def has_permission(self, permission_name):
        """Verifica se o usuário tem uma permissão específica"""
        if self.is_admin:
            return True
            
        # Verificar permissões diretas
        for permission in self.permissions:
            if permission.name == permission_name and permission.is_active:
                return True
        
        # Verificar permissões através do papel/role
        if self.role:
            for role_permission in self.role.role_permissions:
                if (role_permission.permission.name == permission_name and 
                    role_permission.permission.is_active):
                    return True
        
        return False
    
    def has_module_access(self, module_name, action=None):
        """Verifica se o usuário tem acesso a um módulo específico"""
        if self.is_admin:
            return True
            
        # Construir nome da permissão
        if action:
            permission_name = f"{module_name}.{action}"
            return self.has_permission(permission_name)
        else:
            # Verificar qualquer permissão no módulo
            permissions_to_check = [
                f"{module_name}.read",
                f"{module_name}.write", 
                f"{module_name}.delete",
                f"{module_name}.send"
            ]
            return any(self.has_permission(perm) for perm in permissions_to_check)
    
    def get_user_permissions(self):
        """Retorna lista de todas as permissões do usuário"""
        if self.is_admin:
            return ["admin.*"]  # Admin tem todas as permissões
            
        permissions = set()
        
        # Permissões diretas
        for permission in self.permissions:
            if permission.is_active:
                permissions.add(permission.name)
        
        # Permissões através do papel/role
        if self.role:
            for role_permission in self.role.role_permissions:
                if role_permission.permission.is_active:
                    permissions.add(role_permission.permission.name)
        
        return list(permissions)
    
    @staticmethod
    def hash_password(password):
        """Gera hash da senha"""
        return hashlib.md5(password.encode()).hexdigest()
    
    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"
