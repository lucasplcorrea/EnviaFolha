"""
Routes package - Organização modular das rotas da API
"""

from .auth import AuthRouter
from .system import SystemRouter
from .dashboard import DashboardRouter
from .tax_statements import TaxStatementsRouter
from .indicators import IndicatorsRouter
from .companies import CompaniesRouter
from .work_locations import WorkLocationsRouter
from .employees import EmployeesRouter

__all__ = [
    'AuthRouter',
    'SystemRouter',
    'DashboardRouter',
    'TaxStatementsRouter',
    'IndicatorsRouter',
    'CompaniesRouter',
    'WorkLocationsRouter',
    'EmployeesRouter',
]
