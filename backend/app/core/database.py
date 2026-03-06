"""
Configuração do banco de dados - centralização de imports
"""
from app.models.base import Base, SessionLocal, engine, get_db, TimestampMixin

__all__ = ['Base', 'SessionLocal', 'engine', 'get_db', 'TimestampMixin']
