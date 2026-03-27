# Import all models to ensure they are registered with SQLAlchemy
from .base import Base, TimestampMixin
from .user import User
from .employee import Employee
from .company import Company
from .work_location import WorkLocation
from .role_simple import Role
from .payroll import PayrollRecord
from .benefit import BenefitRecord
from .movement import MovementRecord
from .leave import LeaveRecord
from .system_log import SystemLog, LogLevel, LogCategory
from .payroll_send import PayrollSend
from .communication_send import CommunicationSend
from .communication_recipient import CommunicationRecipient
from .send_queue import SendQueue, SendQueueItem
from .hr_indicators import HRIndicatorSnapshot
from .tax_statement import TaxStatement, TaxStatementUpload

# keep older payroll-related imports if they exist elsewhere; import safe names
try:
    from .payroll import PayrollPeriod, PayrollData, PayrollTemplate, PayrollProcessingLog
except Exception:
    # legacy names may be defined in other modules; ignore if not present
    PayrollPeriod = None
    PayrollData = None
    PayrollTemplate = None
    PayrollProcessingLog = None
# from .audit_log import AuditLog
# from .system_setting import SystemSetting

# This allows importing all models with: from app.models import *
__all__ = [
    "Base",
    "TimestampMixin",
    "User",
    "Employee",
    "Company",
    "WorkLocation",
    "Role",
    "PayrollRecord",
    "BenefitRecord",
    "MovementRecord",
    "LeaveRecord",
    "SystemLog",
    "LogLevel",
    "LogCategory",
    "PayrollPeriod",
    "PayrollData",
    "PayrollTemplate",
    "PayrollProcessingLog",
    "PayrollSend",
    "CommunicationSend",
    "CommunicationRecipient",
    "SendQueue",
    "SendQueueItem",
    "HRIndicatorSnapshot",
    "TaxStatement",
    "TaxStatementUpload"
    # "AuditLog",
    # "SystemSetting"
]