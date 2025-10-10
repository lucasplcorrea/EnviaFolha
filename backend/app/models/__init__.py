# Import all models to ensure they are registered with SQLAlchemy
from .base import Base, TimestampMixin
from .user import User
from .employee import Employee
from .permission import Permission, Role, RolePermission
from .payroll import PayrollPeriod, PayrollData, PayrollTemplate, PayrollProcessingLog
# from .audit_log import AuditLog
# from .payroll_send import PayrollSend
# from .communication_send import CommunicationSend
# from .communication_recipient import CommunicationRecipient
# from .system_setting import SystemSetting

# This allows importing all models with: from app.models import *
__all__ = [
    "Base",
    "TimestampMixin",
    "User",
    "Employee",
    "Permission",
    "Role",
    "RolePermission",
    "PayrollPeriod",
    "PayrollData",
    "PayrollTemplate",
    "PayrollProcessingLog"
    # "AuditLog",
    # "PayrollSend",
    # "CommunicationSend",
    # "CommunicationRecipient",
    # "SystemSetting"
]