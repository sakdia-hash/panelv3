
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Date, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String)  # "admin" or "employee"

    employee = relationship("Employee", back_populates="user", uselist=False)
    audit_logs = relationship("AuditLog", back_populates="user")

class DownloadRecord(Base):
    __tablename__ = "download_records"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    start_date = Column(Date)
    end_date = Column(Date)
    count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", back_populates="download_records")

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    full_name = Column(String)
    visible_password = Column(String, default="")
    account_quota = Column(Integer, default=0)
    total_downloads = Column(Integer, default=0) # Kept for legacy but unused

    user = relationship("User", back_populates="employee")
    assigned_accounts = relationship("InstagramAccount", back_populates="assigned_employee")
    download_records = relationship("DownloadRecord", back_populates="employee")
    reports = relationship("DailyReport", back_populates="employee")


class AdminNote(Base):
    __tablename__ = "admin_notes"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, default="")
    author = Column(String, default="")
    updated_at = Column(DateTime, default=datetime.now)

class InstagramAccount(Base):
    __tablename__ = "instagram_accounts"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    assigned_employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)

    assigned_employee = relationship("Employee", back_populates="assigned_accounts")
    reports = relationship("DailyReport", back_populates="account")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String)
    details = Column(String)
    ip_address = Column(String)
    timestamp = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="audit_logs")


class DailyReport(Base):
    __tablename__ = "daily_reports"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    instagram_account_id = Column(Integer, ForeignKey("instagram_accounts.id"))
    date = Column(Date)
    follower_count = Column(Integer)
    locked = Column(Boolean, default=False)

    employee = relationship("Employee", back_populates="reports")
    account = relationship("InstagramAccount", back_populates="reports")

    __table_args__ = (
        UniqueConstraint('employee_id', 'instagram_account_id', 'date', name='unique_daily_report'),
    )
