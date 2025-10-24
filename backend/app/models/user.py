from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

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
    created_employees = relationship("Employee", foreign_keys="Employee.created_by", back_populates="creator")
    updated_employees = relationship("Employee", foreign_keys="Employee.updated_by", back_populates="updater")
    payroll_sends = relationship("PayrollSend", back_populates="user")
    communication_sends = relationship("CommunicationSend", back_populates="user")
    # audit_logs = relationship("AuditLog", back_populates="user")
    
    def verify_password(self, password):
        """Verifica se a senha fornecida corresponde ao hash armazenado"""
        from app.core.auth import verify_password
        return verify_password(password, self.password_hash)
    
    def can_access_page(self, page_name):
        """Verifica se o usuário pode acessar uma página específica"""
        if self.is_admin:
            return True
            
        if self.role:
            return self.role.can_access_page(page_name)
        
        return False
    
    def get_allowed_pages(self):
        """Retorna lista de páginas que o usuário pode acessar"""
        if self.is_admin:
            return ['dashboard', 'employees', 'payroll', 'communications', 'reports', 'users', 'settings']
            
        if self.role:
            return self.role.get_allowed_pages()
        
        return []
    
    @staticmethod
    def hash_password(password):
        """Gera hash da senha"""
        from app.core.auth import get_password_hash
        return get_password_hash(password)
    
    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"
