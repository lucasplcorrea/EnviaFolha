from sqlalchemy import Column, Integer, String, Date, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base


class LeaveRecord(Base):
    __tablename__ = 'leave_records'

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), index=True, nullable=False)
    unified_code = Column(String, index=True, nullable=True)
    leave_type = Column(String, nullable=False)  # Férias, Doença, Licença
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days = Column(Float, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=True)

    employee = relationship('Employee', back_populates='leaves')
