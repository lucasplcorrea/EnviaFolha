"""
Routes package - Organização modular das rotas da API
"""

from .auth import AuthRouter
from .system import SystemRouter
from .dashboard import DashboardRouter
from .tax_statements import TaxStatementsRouter
from .companies import CompaniesRouter
from .work_locations import WorkLocationsRouter

__all__ = [
    'AuthRouter',
    'SystemRouter',
    'DashboardRouter',
    'TaxStatementsRouter',
    'CompaniesRouter',
    'WorkLocationsRouter',
]
