# 360 Degree Cybersecurity (VAPT Web App)

**Monorepo layout**
- backend/  → FastAPI API (Python)
- frontend/ → Next.js UI (React/TypeScript)
- infra/    → Docker Compose, infra notes/scripts
- docs/     → Specs, diagrams

**Next steps**
- Phase 2: Add Postgres via Docker Compose and a minimal FastAPI `/health`.
- Phase 3: Create Next.js app with `/login` and a protected `/dashboard`.
