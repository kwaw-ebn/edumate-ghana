# EduMate Ghana

Tablet-first learning platform for Ghanaian private schools. **Core workflow preview, not yet the full master-prompt MVP.** Built with Next.js/TypeScript and FastAPI/SQLAlchemy; production storage targets Neon PostgreSQL.

## Implemented

- Branded responsive landing page, proposed packages and persisted school-demo enquiries.
- Student, teacher, school administrator and platform administrator sessions.
- Argon2 password hashes, short-lived JWT cookies, rotating hashed refresh tokens, origin checks and school/class/subject authorization.
- Create, edit, draft, publish and archive text lessons. Students can complete published lessons in their class.
- Create quizzes and assignments: multiple choice, true/false, short answer and essay. Server-side scoring for objective work; manual grading and released feedback for written work.
- Idempotent submissions, attempt limits, hidden answer keys before submission, and late indicators.
- School student/teacher registration, account activation controls and teacher assignments.
- Fictional demonstration school with 20 students, three teachers, two classes, 12 original lessons and 30 quiz question entries, plus sample graded assignments.
- Platform school registration and enquiry review without direct access to learner records.
- Downloaded lesson reading using IndexedDB and an offline fallback document. Install manifest and service worker.
- Guided presentation checklist; honestly labelled scripted AI tutor preview.

## Local setup

Python 3.12+, Node 22+. Run from two terminals.

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env; do not use the example secrets.
set -a
source .env
set +a
python -m alembic upgrade head
python -m app.seed
python -m uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
cp .env.example .env.local
npm ci
npm run dev
```

Open http://localhost:3000. API docs: http://localhost:8000/docs. The frontend proxies `/api/*` to FastAPI so browser cookies stay on one origin. `API_ORIGIN` must be set **before the frontend build**.

Demo logins all use the password you set in `DEMO_PASSWORD`:

| Role | Identifier |
|---|---|
| Student | student1@demo.edumate.test through student20@demo.edumate.test |
| Mathematics teacher | maths@demo.edumate.test |
| English teacher | english@demo.edumate.test |
| Science teacher | science@demo.edumate.test |
| School administrator | admin@demo.edumate.test |
| Platform administrator | platform@demo.edumate.test |

These are fictional login identifiers, not deliverable email addresses. Seeding is explicit and idempotent; changing DEMO_PASSWORD after seeding does not reset existing passwords.

## Checks

```bash
cd backend
python -m pytest -q
cd ../frontend
npm run build
```

See [implementation status](docs/STATUS.md), [deployment instructions](docs/DEPLOYMENT.md), and [security notes](docs/SECURITY.md).
