# Debugging Guide

## API Import Errors

Run the backend with `PYTHONPATH=backend` from the repository root, or change into `backend` before running `uvicorn app.main:app`. Install every package in `requirements.txt`; collection modules import Requests, HTTPX, Beautiful Soup, and SOCKS support in addition to FastAPI.

## Empty Dashboard

Confirm the API health endpoint and inspect the browser network panel. Seed demo data if the selected database is empty. Make sure the backend and seeder use the same `DATABASE_URL`; relative SQLite paths depend on the working directory.

## Frontend Cannot Reach API

Confirm port `8000`, `CORS_ORIGINS`, and the browser-visible backend URL. The local UI is expected at port `5173`. `VITE_*` changes require restarting Vite.

## Transformer Model Is Unavailable

The model is downloaded lazily on first use. Offline environments will use the route's heuristic fallback. Check `/api/model-status`; do not present a fallback score as model-backed semantic analysis.

## Tor Is Offline

Tor is optional for the synthetic demo. Check `/api/crawler/tor/check` and verify the configured SOCKS host/port. The bundled executable is Windows-specific and its runtime cache is not versioned. The container does not launch that binary.

## Compose Will Not Start

Ensure `.env` exists and contains non-empty `POSTGRES_*` and `NEO4J_*` values. Run `docker compose config` to locate interpolation errors, then verify Docker Desktop/Engine is running and ports `5173`, `8000`, `5432`, `7474`, and `7687` are free.

## Vite Chunk Warning

The production build currently succeeds but reports a JavaScript chunk above 500 kB. This is a performance warning, not a failed build. Route-level lazy loading can address it in a later frontend-focused change.

## External Feed Failures

Public OSINT, Robin, and DeepDarkCTI operations depend on external availability, rate limits, and schema stability. Treat failures as expected external-state errors, preserve logs without secrets, and use controlled fixtures for the SIH demo.

