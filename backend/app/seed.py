import datetime
from app.core.db import SessionLocal, engine
from app.models.models import (
    Base, User, Project, Assignment, Role, Client,
    ServiceTask, ServiceStage  # <-- new imports
)
from app.auth.security import hash_password


def run():
    # Create all tables (includes Client + ServiceTask)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 1) Tester
        tester = db.query(User).filter_by(email="tester@demo.com").first()
        if not tester:
            tester = User(
                email="tester@demo.com",
                password_hash=hash_password("Test@123"),
                role=Role.tester,
            )
            db.add(tester); db.commit(); db.refresh(tester)

        # 2) Client
        client = db.query(Client).filter_by(name="Acme Corp").first()
        if not client:
            client = Client(
                name="Acme Corp",
                contact_name="Jane Doe",
                contact_email="security@acme.example",
                contact_phone="+1-555-0100",
                notes="Primary contact for external web VAPT.",
            )
            db.add(client); db.commit()

        # 3) Project (note: we still use client_name string for now)
        p = db.query(Project).filter_by(title="External Web VAPT").first()
        if not p:
            p = Project(
                client_name="Acme Corp",
                title="External Web VAPT",
                status="In Progress",
                due_date=dt.date.today(),
            )
            db.add(p); db.commit(); db.refresh(p)

        # 4) Assignment
        if not db.query(Assignment).filter_by(project_id=p.id, tester_id=tester.id).first():
            db.add(Assignment(project_id=p.id, tester_id=tester.id)); db.commit()

        # 5) Service tasks (Kanban) — only seed once
        existing = db.query(ServiceTask).filter_by(project_id=p.id, tester_id=tester.id).first()
        if not existing:
            db.add_all([
                ServiceTask(
                    project_id=p.id, tester_id=tester.id, title="Recon & Scoping",
                    severity="Low", stage=ServiceStage.not_started,
                    due_date=dt.date.today(), order_index=1
                ),
                ServiceTask(
                    project_id=p.id, tester_id=tester.id, title="Auth Bypass Testing",
                    severity="High", stage=ServiceStage.in_progress,
                    due_date=dt.date.today(), order_index=1
                ),
                ServiceTask(
                    project_id=p.id, tester_id=tester.id, title="Report Draft Review",
                    severity="Medium", stage=ServiceStage.validated,
                    due_date=dt.date.today(), order_index=1
                ),
            ])
            db.commit()

        print("Seeded tester: tester@demo.com / Test@123 and client: Acme Corp (with Kanban tasks)")
    finally:
        db.close()


if __name__ == "__main__":
    run()
