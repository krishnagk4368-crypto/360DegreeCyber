from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
import csv, io

from app.core.db import SessionLocal
from app.auth.deps import require_role
from app.models.models import Project, Assignment, Finding, Report
from app.services.report_service import simple_pdf

router = APIRouter(prefix="/tester", tags=["tester"])

uploads_dir = Path(__file__).resolve().parents[2] / "uploads"
uploads_dir.mkdir(exist_ok=True)

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
    # Ensure assignment
    assigned = db.query(Assignment).filter(
        Assignment.project_id == project_id,
        Assignment.tester_id == payload["sub"]
    ).first()
    if not assigned:
        raise HTTPException(status_code=403, detail="Not assigned to this project")

    pdf_path = uploads_dir / f"report_proj{project_id}_tester{payload['sub']}.pdf"
    simple_pdf(pdf_path, "VAPT Report", [
        f"Project ID: {project_id}",
        f"Tester ID: {payload['sub']}",
        "Summary: Auto-generated placeholder report."
    ])

    r = Report(project_id=project_id, tester_id=payload["sub"], file_path=str(pdf_path), summary="Placeholder")
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

