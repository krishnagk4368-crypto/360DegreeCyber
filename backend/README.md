# 360 Cybersecurity — Tester Backend (Starter)

This is a beginner-friendly FastAPI backend to power the Tester dashboard.

## Features
- JWT login (`/auth/login`)
- Tester endpoints:
  - `GET /tester/projects` — list assigned projects
  - `POST /tester/findings` — create finding + upload PoC file
  - `POST /tester/reports/generate?project_id=ID` — create simple PDF
  - `GET /tester/reports/{id}/download` — download generated report
- Dev-friendly auth skip (`SKIP_AUTH=true` with `DEV_ASSUME_TESTER_ID=1`)

## Prereqs
- Docker & Docker Compose (for Postgres + pgAdmin)
- Python 3.10+
- (Optional) Postman/Insomnia for API testing

## Quick Start
```bash
# 1) Start Postgres
docker compose -f ../infra/docker-compose.yml up -d

# 2) Create venv & install deps
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3) Configure environment
cp .env.example .env
# (Keep SKIP_AUTH=true for now; it assumes tester id 1)

# 4) Run app
uvicorn app.main:app --reload --port 8000

# 5) Seed demo data
python -m app.seed
```

## Test with curl
```bash
# If SKIP_AUTH=true, you can omit Authorization header.

# List projects for tester (assumes tester id=1)
curl http://localhost:8000/tester/projects

# Upload a finding (replace PROJECT_ID=1 and FILE)
curl -X POST http://localhost:8000/tester/findings          -F project_id=1 -F title="SQLi in login" -F severity=High          -F description="Payload: ' OR 1=1 --"          -F poc=@/etc/hosts

# Generate a PDF report and get download URL
curl -X POST "http://localhost:8000/tester/reports/generate?project_id=1"

# Download the report (example id=1)
curl -OJ http://localhost:8000/tester/reports/1/download
```

## Enabling real JWT auth later
1. Set `SKIP_AUTH=false` in `.env`.
2. Obtain a token via `/auth/login` using the seeded user:
   ```json
   { "email": "tester@demo.com", "password": "Test@123" }
   ```
3. Attach the token in requests:
   `Authorization: Bearer <token>`

## Next steps
- Add input validation (Pydantic models) and file size limits
- Add pagination to `/tester/projects` and findings list
- Move from `Base.metadata.create_all` to Alembic migrations
- Replace local file storage with S3 in production
- Add role-based routers for manager/client/admin reusing the same pattern
