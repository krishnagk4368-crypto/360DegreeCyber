from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Body
from sqlalchemy.orm import Session
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
import csv, io

from app.core.db import SessionLocal
from app.auth.deps import require_role
from app.models.models import Project, Assignment, Finding, Report, Client, ServiceTask, ServiceStage

from typing import Optional, List, Dict, Any
from sqlalchemy import func, desc
from app.services.report_service import generate_report_pdf
from app.services.excel_service import findings_to_xlsx


router = APIRouter(prefix="/tester", tags=["tester"])

uploads_dir = Path(__file__).resolve().parents[2] / "uploads"
uploads_dir.mkdir(exist_ok=True)

def _project_summary(db, project_id: int, tester_id: int) -> str:
    total = db.query(func.count(Finding.id)).filter(
        Finding.project_id == project_id, Finding.tester_id == tester_id
    ).scalar()
    crit = db.query(func.count(Finding.id)).filter(
        Finding.project_id == project_id, Finding.tester_id == tester_id, Finding.severity == "Critical"
    ).scalar()
    high = db.query(func.count(Finding.id)).filter(
        Finding.project_id == project_id, Finding.tester_id == tester_id, Finding.severity == "High"
    ).scalar()
    return f"Findings: {total} (Critical: {crit}, High: {high})"


@router.get("/clients")
def my_clients(payload=Depends(require_role("tester"))):
    db: Session = SessionLocal()

    # Projects assigned to this tester
    assigned_projects = db.query(
        Project.client_name, Project.id.label("pid")
    ).join(Assignment, Assignment.project_id == Project.id
    ).filter(Assignment.tester_id == payload["sub"]).subquery()

    # Count projects per client_name
    proj_counts = db.query(
        assigned_projects.c.client_name.label("client_name"),
        func.count(assigned_projects.c.pid).label("project_count")
    ).group_by(assigned_projects.c.client_name).subquery()

    # Count open findings per client_name
    f_join = db.query(
        Project.client_name.label("client_name"),
        func.count(Finding.id).label("open_findings")
    ).join(Finding, Finding.project_id == Project.id
    ).join(Assignment, Assignment.project_id == Project.id
    ).filter(
        Assignment.tester_id == payload["sub"], Finding.status == "open"
    ).group_by(Project.client_name).subquery()

    # Left-join to clients table by name
    rows = db.query(
        Client.id.label("client_id"),
        Client.name.label("name"),
        Client.contact_name, Client.contact_email, Client.contact_phone,
        proj_counts.c.project_count,
        func.coalesce(f_join.c.open_findings, 0).label("open_findings")
    ).outerjoin(Client, Client.name == proj_counts.c.client_name
    ).outerjoin(f_join, f_join.c.client_name == proj_counts.c.client_name
    ).all()

    # Build response; include any assigned client names missing in `clients` table
    counts = {r.name: {
        "client_id": r.client_id, "contact_name": r.contact_name,
        "contact_email": r.contact_email, "contact_phone": r.contact_phone,
        "project_count": r.project_count, "open_findings": r.open_findings
    } for r in rows}

    extras = db.query(assigned_projects.c.client_name).distinct().all()
    for (nm,) in extras:
        if nm not in counts:
            counts[nm] = {"client_id": None, "contact_name": "", "contact_email": "",
                          "contact_phone": "", "project_count": 1, "open_findings": 0}

    return [
        {
            "client_id": v["client_id"], "name": k,
            "contact_name": v["contact_name"], "contact_email": v["contact_email"],
            "contact_phone": v["contact_phone"],
            "project_count": int(v["project_count"] or 0),
            "open_findings": int(v["open_findings"] or 0),
        }
        for k, v in sorted(counts.items(), key=lambda x: x[0].lower())
    ]


@router.get("/clients/{client_id}")
def client_profile(client_id: int, payload=Depends(require_role("tester"))):
    db: Session = SessionLocal()
    client = db.query(Client).get(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    prows = db.query(Project).join(Assignment, Assignment.project_id == Project.id
    ).filter(
        Assignment.tester_id == payload["sub"],
        Project.client_name == client.name
    ).order_by(desc(Project.id)).limit(10).all()

    open_findings = db.query(func.count(Finding.id)).join(
        Project, Finding.project_id == Project.id
    ).join(Assignment, Assignment.project_id == Project.id
    ).filter(
        Assignment.tester_id == payload["sub"],
        Project.client_name == client.name,
        Finding.status == "open"
    ).scalar()

    return {
        "client": {
            "id": client.id, "name": client.name,
            "contact_name": client.contact_name, "contact_email": client.contact_email,
            "contact_phone": client.contact_phone, "notes": client.notes,
        },
        "stats": { "open_findings": int(open_findings or 0), "project_count": len(prows) },
        "recent_projects": [
            {"id": p.id, "title": p.title, "status": p.status, "due_date": str(p.due_date)} for p in prows
        ]
    }

@router.get("/projects")
def my_projects(payload=Depends(require_role("tester"))):
    db: Session = SessionLocal()
    q = db.query(Project).join(Assignment, Assignment.project_id == Project.id)            .filter(Assignment.tester_id == payload["sub"])
    return [
        {"id": p.id, "title": p.title, "status": p.status, "due_date": str(p.due_date)}
        for p in q.all()
    ]

@router.post("/findings")
async def upload_finding(
    project_id: int = Form(...),
    title: str = Form(...),
    severity: str = Form(...),
    description: str = Form(""),
    poc: UploadFile = File(None),
    payload=Depends(require_role("tester"))
):
    db: Session = SessionLocal()
    # Basic validation: ensure tester is assigned to project
    assigned = db.query(Assignment).filter(
        Assignment.project_id == project_id,
        Assignment.tester_id == payload["sub"]
    ).first()
    if not assigned:
        raise HTTPException(status_code=403, detail="Not assigned to this project")

    poc_path = None
    if poc:
        dest = uploads_dir / f"poc_{payload['sub']}_{poc.filename}"
        with dest.open("wb") as f:
            f.write(await poc.read())
        poc_path = str(dest)

    finding = Finding(
        project_id=project_id, tester_id=payload["sub"],
        title=title, severity=severity, description=description,
        poc_path=poc_path
    )
    db.add(finding); db.commit(); db.refresh(finding)
    return {"id": finding.id, "message": "Upload successful"}

@router.post("/reports/generate")
def generate_report(project_id: int, payload=Depends(require_role("tester"))):
    db: Session = SessionLocal()
    # ensure assignment...
    assigned = db.query(Assignment).filter(
        Assignment.project_id == project_id,
        Assignment.tester_id == payload["sub"]
    ).first()
    if not assigned:
        raise HTTPException(status_code=403, detail="Not assigned to this project")

    # collect findings
    rows = db.query(Finding).filter(
        Finding.project_id == project_id,
        Finding.tester_id == payload["sub"]
    ).order_by(desc(Finding.id)).all()
    findings = [{"title": r.title, "severity": r.severity, "description": r.description or ""} for r in rows]
    summary = _project_summary(db, project_id, payload["sub"])

    pdf_path = uploads_dir / f"report_proj{project_id}_tester{payload['sub']}.pdf"
    generate_report_pdf(pdf_path, project_id, payload["sub"], summary=summary, findings=findings)

    r = Report(project_id=project_id, tester_id=payload["sub"], file_path=str(pdf_path), summary=summary)
    db.add(r); db.commit(); db.refresh(r)
    return {"report_id": r.id, "download_url": f"/tester/reports/{r.id}/download"}

@router.get("/reports/{report_id}/download")
def download_report(report_id: int, payload=Depends(require_role("tester"))):
    db: Session = SessionLocal()
    r = db.query(Report).get(report_id)
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(r.file_path, filename=f"report_{report_id}.pdf")

@router.get("/findings/list")
def list_findings(project_id: int, payload=Depends(require_role("tester"))):
    db: Session = SessionLocal()
    q = db.query(Finding).filter(
        Finding.project_id == project_id,
        Finding.tester_id == payload["sub"]
    ).order_by(Finding.id.desc())
    return [
        {
            "id": f.id, "project_id": f.project_id, "title": f.title,
            "severity": f.severity, "status": f.status,
            "description": f.description, "poc_path": f.poc_path,
        } for f in q.all()
    ]

@router.get("/findings/export.csv")
def export_findings_csv(project_id: int, payload=Depends(require_role("tester"))):
    db: Session = SessionLocal()
    q = db.query(Finding).filter(
        Finding.project_id == project_id,
        Finding.tester_id == payload["sub"]
    ).order_by(Finding.id.desc())

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id","project_id","title","severity","status","description","poc_path"])
    for f in q.all():
        w.writerow([f.id, f.project_id, f.title, f.severity, f.status, f.description, f.poc_path])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.read()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="findings.csv"'}
    )

@router.get("/reports")
def list_reports(
    project_id: Optional[int] = None,
    payload=Depends(require_role("tester"))
) -> List[Dict[str, Any]]:
    db: Session = SessionLocal()
    q = db.query(Report).filter(Report.tester_id == payload["sub"])
    if project_id is not None:
        q = q.filter(Report.project_id == project_id)
    q = q.order_by(desc(Report.created_at))
    items = []
    for r in q.all():
        items.append({
            "id": r.id,
            "project_id": r.project_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "summary": r.summary,
            "download_url": f"/tester/reports/{r.id}/download"
        })
    return items

@router.post("/reports/{report_id}/regenerate")
def regenerate_report(report_id: int, payload=Depends(require_role("tester"))):
    db: Session = SessionLocal()
    old = db.query(Report).get(report_id)
    if not old or old.tester_id != payload["sub"]:
        raise HTTPException(status_code=404, detail="Report not found")

    rows = db.query(Finding).filter(
        Finding.project_id == old.project_id,
        Finding.tester_id == payload["sub"]
    ).order_by(desc(Finding.id)).all()
    findings = [{"title": r.title, "severity": r.severity, "description": r.description or ""} for r in rows]
    summary = "Regenerated — " + _project_summary(db, old.project_id, payload["sub"])

    new_pdf = uploads_dir / f"report_proj{old.project_id}_tester{payload['sub']}_re_{old.id}.pdf"
    generate_report_pdf(new_pdf, old.project_id, payload["sub"], summary=summary, findings=findings)

    new_row = Report(project_id=old.project_id, tester_id=payload["sub"], file_path=str(new_pdf), summary=summary)
    db.add(new_row); db.commit(); db.refresh(new_row)
    return {"report_id": new_row.id, "download_url": f"/tester/reports/{new_row.id}/download"}

# Helper to ensure the tester is assigned to the project
def _ensure_assigned(db: Session, tester_id: int, project_id: int):
    assigned = db.query(Assignment).filter(
        Assignment.project_id == project_id,
        Assignment.tester_id == tester_id
    ).first()
    if not assigned:
        raise HTTPException(status_code=403, detail="Not assigned to this project")

@router.get("/services")
def list_services(project_id: int, payload=Depends(require_role("tester"))):
    """Return tasks grouped by stage for the tester on a project."""
    db: Session = SessionLocal()
    _ensure_assigned(db, payload["sub"], project_id)
    tasks = db.query(ServiceTask).filter(
        ServiceTask.project_id == project_id,
        ServiceTask.tester_id == payload["sub"]
    ).order_by(ServiceTask.stage, ServiceTask.order_index, desc(ServiceTask.id)).all()

    def serialize(t: ServiceTask):
        return {
            "id": t.id,
            "project_id": t.project_id,
            "title": t.title,
            "severity": t.severity,
            "stage": t.stage.value,
            "due_date": str(t.due_date) if t.due_date else None,
            "order_index": t.order_index
        }

    grouped = {"not_started": [], "in_progress": [], "validated": []}
    for t in tasks:
        grouped[t.stage.value].append(serialize(t))
    return grouped

@router.post("/services")
def create_service(
    project_id: int = Body(..., embed=True),
    title: str = Body(..., embed=True),
    severity: str = Body("Medium", embed=True),
    description: str = Body("", embed=True),
    due_date: str | None = Body(None, embed=True),   # "YYYY-MM-DD"
    payload=Depends(require_role("tester"))
):
    db: Session = SessionLocal()
    _ensure_assigned(db, payload["sub"], project_id)
    due = None
    if due_date:
        import datetime
        due = datetime.date.fromisoformat(due_date)
    # find max order_index in not_started
    max_order = db.query(func.coalesce(func.max(ServiceTask.order_index), 0)).filter(
        ServiceTask.project_id == project_id,
        ServiceTask.tester_id == payload["sub"],
        ServiceTask.stage == ServiceStage.not_started
    ).scalar()
    task = ServiceTask(
        project_id=project_id, tester_id=payload["sub"], title=title,
        description=description, severity=severity, due_date=due,
        stage=ServiceStage.not_started, order_index=(max_order + 1)
    )
    db.add(task); db.commit(); db.refresh(task)
    return {"id": task.id}

@router.patch("/services/{task_id}/stage")
def move_service(
    task_id: int,
    stage: ServiceStage = Body(..., embed=True),
    order_index: int | None = Body(None, embed=True),
    payload=Depends(require_role("tester"))
):
    """Move a task to another stage (and optionally set order_index)."""
    db: Session = SessionLocal()
    task = db.query(ServiceTask).get(task_id)
    if not task or task.tester_id != payload["sub"]:
        raise HTTPException(status_code=404, detail="Task not found")
    _ensure_assigned(db, payload["sub"], task.project_id)

    task.stage = stage
    if order_index is not None:
        task.order_index = order_index
    db.commit(); db.refresh(task)
    return {"id": task.id, "stage": task.stage.value, "order_index": task.order_index}

@router.get("/findings/export.xlsx")
def export_findings_xlsx(project_id: int, payload=Depends(require_role("tester"))):
    db: Session = SessionLocal()
    # ensure tester is assigned to this project (reuse helper if you have it)
    assigned = db.query(Assignment).filter(
        Assignment.project_id == project_id,
        Assignment.tester_id == payload["sub"]
    ).first()
    if not assigned:
        raise HTTPException(status_code=403, detail="Not assigned to this project")

    rows = db.query(Finding).filter(
        Finding.project_id == project_id,
        Finding.tester_id == payload["sub"]
    ).order_by(Finding.id.desc()).all()

    buf = findings_to_xlsx(rows)
    filename = f"findings_project_{project_id}.xlsx"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )

