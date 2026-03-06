"""
Routes package - Organização modular das rotas da API
"""

from .auth import AuthRouter
from .system import SystemRouter
from .dashboard import DashboardRouter

__all__ = [
    'AuthRouter',
    'SystemRouter',
    'DashboardRouter'
]
