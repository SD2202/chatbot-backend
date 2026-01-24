from typing import Optional
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from datetime import datetime
import enum

Base = declarative_base()

class ComplaintStatus(str, enum.Enum):
    PENDING = "pending"
    RESOLVED = "resolved"
    IN_PROGRESS = "in_progress"

class TaxStatus(str, enum.Enum):
    PAID = "paid"
    DUE = "due"
    PENDING = "pending"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    login_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    mobile = Column(String(20), nullable=False, index=True)
    area = Column(String(100))
    ward_number = Column(String(10))
    created_at = Column(DateTime, default=datetime.utcnow)

class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    phone_number = Column(String(20), nullable=False, index=True)
    state = Column(String(50), default="login")
    current_category = Column(String(50), nullable=True)
    current_sub_issue = Column(String(100), nullable=True)
    login_id = Column(String(50), nullable=True)
    complaint_id = Column(String(50), nullable=True)
    property_id = Column(String(50), nullable=True)
    image_url = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Complaint(Base):
    __tablename__ = "complaints"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    complaint_id = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    login_id = Column(String(50), nullable=False)
    category = Column(String(50), nullable=False)
    sub_issue = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)
    status = Column(SQLEnum(ComplaintStatus), default=ComplaintStatus.PENDING, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PropertyTax(Base):
    __tablename__ = "property_tax"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(String(50), unique=True, nullable=False, index=True)
    owner_name = Column(String(100), nullable=False)
    address = Column(Text, nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(SQLEnum(TaxStatus), nullable=False, index=True)
    year = Column(Integer, nullable=False)
    receipt_no = Column(String(50), nullable=True)
    bill_no = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
