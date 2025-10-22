"""
Routes package - Organização modular das rotas da API
"""

from .auth import AuthRouter
from .employees import EmployeesRouter
from .payrolls import PayrollsRouter
from .communications import CommunicationsRouter
from .system import SystemRouter
from .reports import ReportsRouter

__all__ = [
    'AuthRouter',
    'EmployeesRouter',
    'PayrollsRouter',
    'CommunicationsRouter',
    'SystemRouter',
    'ReportsRouter'
]
