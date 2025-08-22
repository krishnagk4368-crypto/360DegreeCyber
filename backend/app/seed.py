from app.core.db import SessionLocal, engine
from app.models.models import Base, User, Project, Assignment, Role
from app.auth.security import hash_password
import datetime

def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Create tester
    tester = db.query(User).filter_by(email="tester@demo.com").first()
    if not tester:
        tester = User(email="tester@demo.com", password_hash=hash_password("Test@123"), role=Role.tester)
        db.add(tester); db.commit(); db.refresh(tester)

    # Create a sample project
    p = db.query(Project).filter_by(title="External Web VAPT").first()
    if not p:
        p = Project(client_name="Acme Corp", title="External Web VAPT", status="In Progress",
                    due_date=datetime.date.today())
        db.add(p); db.commit(); db.refresh(p)

    # Assign tester
    if not db.query(Assignment).filter_by(project_id=p.id, tester_id=tester.id).first():
        db.add(Assignment(project_id=p.id, tester_id=tester.id)); db.commit()

    print("Seeded tester: tester@demo.com / Test@123")

if __name__ == "__main__":
    run()
