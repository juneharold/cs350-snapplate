# SnapPlate

SnapPlate is a mobile-style food diary and restaurant recommendation app for CS350.
This repo runs the full local stack with:

- Frontend: Next.js
- Backend: FastAPI
- Data layer: Postgres + MinIO in Docker
- Algorithm: deterministic provider by default, optional OpenAI provider

## Prerequisites

- Docker Desktop
- Python 3.11+
- Node.js 20+ and npm

## First-Time Setup

Install backend and frontend dependencies:

```bash
make install
make frontend-install
```

Create backend env:

```bash
cp backend/.env.example backend/.env
```

Create `frontend/.env.local`:

```bash
NEXT_PUBLIC_ENABLE_MOCKS=false
API_URL=http://localhost:8000
```

The default backend env uses `ALGORITHM_PROVIDER=deterministic`, so no OpenAI
key is required for grading/demo. `KAKAO_REST_API_KEY` is optional for local
testing; the demo seed has deterministic restaurant fallback data when Kakao is
not configured.

## Run The Real App

Start Postgres + MinIO and apply migrations:

```bash
make up
make db-migrate
```

Seed demo users, diary entries, taste profiles, and recommendation data:

```bash
cd backend
.venv/bin/python -m scripts.seed_demo
cd ..
```

Start the backend:

```bash
make run-backend
```

In a second terminal, start the frontend:

```bash
make run-frontend
```

Open `http://localhost:3000`.

## Demo Login

Use either seeded email:

- `junho.kang.kr@gmail.com`
- `seoyeon.lim.eats@gmail.com`

From the app:

1. Choose email sign-in.
2. Enter one seeded email.
3. On the inbox screen, press **Tap the magic link**.

Because `SMTP_URL` is empty in local demo mode, the backend returns a dev-only
magic-link token and the frontend can simulate tapping the email link.

## How To Demo

1. Sign in as a seeded user. (Read Demo Login Above)
2. Open the home page and nearby restaurants.
3. Open recommendations; seeded users have at least 10 finalized entries.
4. Open Taste to see the generated taste profile.
5. Open Diary and a diary detail page.
6. Capture or upload a photo, save a draft, finish it with a note, and confirm it appears in Diary.
7. Bookmark a restaurant and verify it appears in saved restaurants.

Personalization intentionally starts after **10 finalized diary entries** for
both taste analysis and restaurant recommendations.

## Verification Commands

Backend:

```bash
make lint
make typecheck
make test
```

Frontend:

```bash
cd frontend
npm run typecheck
npm run build
```

## Optional Modes

Use OpenAI instead of the deterministic provider:

```bash
# backend/.env
ALGORITHM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

When `ALGORITHM_PROVIDER=openai`, the backend fails at startup if
`OPENAI_API_KEY` is missing.

Use frontend mocks instead of the real backend:

```bash
# frontend/.env.local
NEXT_PUBLIC_ENABLE_MOCKS=true
```

Mocks are useful for UI-only work, but grading should use
`NEXT_PUBLIC_ENABLE_MOCKS=false`.
