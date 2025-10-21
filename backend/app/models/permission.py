from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

# Tabela de associação many-to-many entre User e Permission
user_permissions = Table(
    'user_permissions',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id'), primary_key=True)
)

class Permission(Base, TimestampMixin):
    """Modelo para gerenciar permissões do sistema"""
    __tablename__ = "permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)  # Ex: 'employees.read', 'payroll.send'
    description = Column(String(255), nullable=True)
    module = Column(String(50), nullable=False)  # Ex: 'employees', 'payroll', 'communications'
    action = Column(String(50), nullable=False)  # Ex: 'read', 'write', 'delete', 'send'
    is_active = Column(Boolean, default=True)
    
    # Relacionamentos
    users = relationship("User", secondary=user_permissions, back_populates="permissions")
    
    def __repr__(self):
        return f"<Permission(name='{self.name}', module='{self.module}')>"

class Role(Base, TimestampMixin):
    """Modelo para papéis/funções com conjunto de permissões"""
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)  # Ex: 'admin', 'operator', 'viewer'
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relacionamentos
    users = relationship("User", back_populates="role")
    role_permissions = relationship("RolePermission", back_populates="role")
    
    def __repr__(self):
        return f"<Role(name='{self.name}')>"

# Tabela de associação entre Role e Permission
class RolePermission(Base, TimestampMixin):
    """Associação entre papéis e permissões"""
    __tablename__ = "role_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey('roles.id'), nullable=False)
    permission_id = Column(Integer, ForeignKey('permissions.id'), nullable=False)
    
    # Relacionamentos
    role = relationship("Role", back_populates="role_permissions")
    permission = relationship("Permission")
    
    def __repr__(self):
        return f"<RolePermission(role_id={self.role_id}, permission_id={self.permission_id})>"