from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Date, DateTime, Text, Enum, ForeignKey
from sqlalchemy.orm import relationship
import enum, datetime
import datetime

Base = declarative_base()


# --- new enum + table ---
class ServiceStage(str, enum.Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    validated = "validated"

class ServiceTask(Base):
    __tablename__ = "service_tasks"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    tester_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    severity = Column(String, default="Medium")      # Low | Medium | High | Critical
    stage = Column(Enum(ServiceStage), default=ServiceStage.not_started, nullable=False)
    due_date = Column(Date)
    order_index = Column(Integer, default=0)         # for drag/drop ordering

class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True, nullable=False)
    contact_name = Column(String, default="")
    contact_email = Column(String, default="")
    contact_phone = Column(String, default="")
    notes = Column(Text, default="")

class Role(str, enum.Enum):
    tester = "tester"
    manager = "manager"
    client = "client"
    superadmin = "superadmin"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(Role), nullable=False)

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    client_name = Column(String, nullable=False)
    title = Column(String, nullable=False)
    status = Column(String, default="Not Started")
    due_date = Column(Date)

class Assignment(Base):
    __tablename__ = "assignments"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    tester_id = Column(Integer, ForeignKey("users.id"))

class Finding(Base):
    __tablename__ = "findings"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    tester_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, nullable=False)
    severity = Column(String)  # Critical/High/Medium/Low
    description = Column(Text)
    poc_path = Column(String)  # file path (dev) or S3 key (prod)
    status = Column(String, default="open")

class Report(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    tester_id = Column(Integer, ForeignKey("users.id"))
    file_path = Column(String)
    summary = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)