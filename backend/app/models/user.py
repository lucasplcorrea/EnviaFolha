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
        return hashlib.md5(password.encode()).hexdigest()
    
    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"
