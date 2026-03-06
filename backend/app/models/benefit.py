from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.models.base import Base


class BenefitRecord(Base):
    __tablename__ = 'benefit_records'

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), index=True, nullable=False)
    unified_code = Column(String, index=True, nullable=True)
    benefit_type = Column(String, nullable=False)  # e.g., Alimentação, Saúde
    value = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=True)

    employee = relationship('Employee', back_populates='benefits')
