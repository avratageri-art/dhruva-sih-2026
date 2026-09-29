# Local Development Setup

## Requirements

- Python 3.11
- Node.js 20.19 or newer and npm
- Git
- Optional PostgreSQL 15 and Neo4j 5
- Optional Tor SOCKS5 service on `127.0.0.1:9050`

Python 3.12+ is not the documented target because the pinned 2023-era scientific dependencies were selected for Python 3.11.

## Configure

From the repository root:

```bash
cp .env.example .env
```

PowerShell:

```powershell
Copy-Item .env.example .env
```

The template defaults the manual backend to `sqlite:///./darktrace.db`. Change only what your environment needs. Do not put private credentials in `VITE_*` variables.

## Backend

macOS/Linux:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
PYTHONPATH=backend uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
$env:PYTHONPATH = "backend"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API creates missing tables at startup. Verify <http://localhost:8000/> and <http://localhost:8000/docs>.

## Seed Demo Data

With the virtual environment active and the API stopped:

```bash
python scripts/seed_db_sqlite.py
```

The SQLite seeder targets `backend/darktrace.db` explicitly, while the default root `.env` URL resolves relative to the process working directory. To use the seeded database when starting from the repository root, set `DATABASE_URL=sqlite:///./backend/darktrace.db` in your local `.env`.

`scripts/seed_database.py` clears and repopulates tables at its configured database URL. Use it only on an expendable demo database.

## Frontend

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open <http://localhost:5173>. The Vite proxy forwards relative `/api` requests to `http://localhost:8000`; several current pages also address that backend URL directly.

## Tests and Build

```bash
python -m pytest backend/tests -q
cd frontend
npm run build
```

There is no frontend lint or browser-test command in the current package configuration.

