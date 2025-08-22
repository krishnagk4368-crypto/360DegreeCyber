from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Date, DateTime, Text, Enum, ForeignKey
from sqlalchemy.orm import relationship
import enum, datetime

Base = declarative_base()

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
