from sqlalchemy import Column, Integer, String, Text, JSON
from .base import Base, TimestampMixin

class SystemSetting(Base, TimestampMixin):
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(Text, nullable=True)
    data_type = Column(String(20), nullable=False, default='string')  # string, integer, boolean, json
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)
    is_public = Column(String(10), nullable=False, default='false')  # true, false, admin_only
    
    def __repr__(self):
        return f"<SystemSetting(key='{self.key}', data_type='{self.data_type}')>"
    
    def get_value(self):
        """Converte o valor string para o tipo apropriado"""
        if self.value is None:
            return None
        
        if self.data_type == 'integer':
            try:
                return int(self.value)
            except ValueError:
                return None
        elif self.data_type == 'boolean':
            return self.value.lower() in ['true', '1', 'yes']
        elif self.data_type == 'json':
            try:
                import json
                return json.loads(self.value)
            except (json.JSONDecodeError, ImportError):
                return None
        else:  # string
            return self.value
    
    def set_value(self, value):
        """Define o valor convertendo para string"""
        if value is None:
            self.value = None
        elif self.data_type == 'json':
            import json
            self.value = json.dumps(value)
        else:
            self.value = str(value)