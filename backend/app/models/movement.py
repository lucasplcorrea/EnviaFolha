from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base


class MovementRecord(Base):
    __tablename__ = 'movement_records'

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), index=True, nullable=False)
    unified_code = Column(String, index=True, nullable=True)
    movement_type = Column(String, nullable=False)  # Promotion, Transfer, Termination
    previous_position = Column(String, nullable=True)
    new_position = Column(String, nullable=True)
    previous_department = Column(String, nullable=True)
    new_department = Column(String, nullable=True)
    previous_work_location_id = Column(Integer, ForeignKey('work_locations.id'), nullable=True)
    new_work_location_id = Column(Integer, ForeignKey('work_locations.id'), nullable=True)
    date = Column(Date, nullable=False)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=True)

    employee = relationship('Employee', back_populates='movements')
