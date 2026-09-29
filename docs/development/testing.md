# Testing and Validation

Run commands from the repository root unless noted.

## Backend

Use Python 3.11, which matches the backend container and CI:

```bash
python -m pytest backend/tests -q
python -m compileall -q backend ai graph scripts
```

The checked-in test suite is a small API smoke suite. Scripts under `backend/scripts/` may contact a running API, public services, or Tor and are intentionally excluded from default CI.

## Frontend

```bash
cd frontend
npm ci
npm run build
npm audit --omit=dev
```

There is no configured frontend lint or browser-test command. The production build currently reports a non-fatal large-chunk warning.

## Configuration

```bash
docker compose --env-file .env.example config --quiet
```

A full image build and smoke test require a running Docker engine:

```bash
docker compose --env-file .env.example build
docker compose up
```

## Security checks

Gitleaks runs in `.github/workflows/secret-scan.yml`. If Gitleaks is installed locally, run `gitleaks detect --redact --no-banner`. Do not paste a detected credential into an issue or build log.

Do not run Tor, OSINT, Robin, or infrastructure-network tests against third-party targets without explicit authorization.
