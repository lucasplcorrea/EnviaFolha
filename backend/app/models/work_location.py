from sqlalchemy import Column, Integer, String, Text, Boolean, Float, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class WorkLocation(Base, TimestampMixin):
    """Locais de atuação / canteiros de obras"""
    __tablename__ = "work_locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)                  # Nome do local / obra
    code = Column(String(50), nullable=True, index=True)        # Código interno da obra (ex: OB-2025-001)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)  # Empresa responsável

    # Endereço
    address_street = Column(String(255), nullable=True)
    address_number = Column(String(20), nullable=True)
    address_complement = Column(String(100), nullable=True)
    address_neighborhood = Column(String(100), nullable=True)
    address_city = Column(String(100), nullable=True)
    address_state = Column(String(2), nullable=True)             # UF (ex: PR, SP)
    address_zip = Column(String(9), nullable=True)               # CEP (ex: 85500-000)

    # Geolocalização (OpenStreetMap / Leaflet)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)

    # Relacionamentos
    company = relationship("Company", back_populates="work_locations")
    employees = relationship("Employee", back_populates="work_location")

    def __repr__(self):
        return f"<WorkLocation(name='{self.name}', city='{self.address_city}')>"
