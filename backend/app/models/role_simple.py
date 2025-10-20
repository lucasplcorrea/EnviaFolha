from sqlalchemy import Column, Integer, String, Boolean, Text
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class Role(Base, TimestampMixin):
    """Modelo simplificado para papéis com controle de páginas"""
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)  # Ex: 'admin', 'manager', 'operator', 'viewer'
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Páginas que o role pode acessar (JSON como texto)
    allowed_pages = Column(Text, nullable=False, default='[]')  # Ex: '["dashboard", "employees", "payroll"]'
    
    # Relacionamentos
    users = relationship("User", back_populates="role")
    
    def __repr__(self):
        return f"<Role(name='{self.name}')>"
    
    def get_allowed_pages(self):
        """Retorna lista de páginas permitidas"""
        import json
        try:
            return json.loads(self.allowed_pages)
        except:
            return []
    
    def set_allowed_pages(self, pages_list):
        """Define lista de páginas permitidas"""
        import json
        self.allowed_pages = json.dumps(pages_list)
    
    def can_access_page(self, page_name):
        """Verifica se o role pode acessar uma página específica"""
        allowed = self.get_allowed_pages()
        return page_name in allowed or 'all' in allowed

# Dados padrão dos roles
DEFAULT_ROLES = [
    {
        'name': 'admin',
        'description': 'Administrador - Acesso completo',
        'allowed_pages': ['dashboard', 'employees', 'payroll', 'communications', 'reports', 'users', 'settings']
    },
    {
        'name': 'manager',
        'description': 'Gerente - Operações e configurações',
        'allowed_pages': ['dashboard', 'employees', 'payroll', 'communications', 'reports', 'settings']
    },
    {
        'name': 'operator',
        'description': 'Operador - Envios e relatórios',
        'allowed_pages': ['dashboard', 'payroll', 'communications', 'reports']
    },
    {
        'name': 'viewer',
        'description': 'Visualizador - Apenas relatórios',
        'allowed_pages': ['reports']
    }
]