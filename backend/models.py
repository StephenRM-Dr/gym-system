# models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from .database import Base

class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    dni = Column(String, unique=True, index=True) # Cédula de identidad
    phone_number = Column(String, nullable=False) # Formato: 58412...
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)