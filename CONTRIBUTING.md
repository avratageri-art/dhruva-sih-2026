# Contributing to DHRUVA

## Development Setup

Follow [the local setup guide](docs/development/local-setup.md). Copy `.env.example` to `.env`, use only local/demo credentials, and never commit collected sensitive material.

## Branches and Commits

Use short branches such as `feature/graph-filter`, `fix/crawler-timeout`, `docs/demo-guide`, or `security/cors-policy`. Keep commits focused and write an imperative subject, for example `docs: clarify SQLite setup`.

## Pull Requests

1. Explain the problem and the smallest proposed change.
2. Link related issues without copying sensitive details.
3. Add or update tests for changed behavior.
4. Run the backend tests, frontend build, Compose validation, and secret scan that apply.
5. Update documentation and `.env.example` for configuration changes.
6. Include screenshots for visible UI changes.
7. Complete the security and responsible-use sections of the PR template.

Do not combine application redesigns with repository maintenance. Preserve schema and API compatibility unless the change explicitly requires it.

## Testing Requirements

```bash
python -m pytest backend/tests -q
cd frontend && npm ci && npm run build
docker compose config --quiet
```

Network-dependent Tor or OSINT tests must be opt-in, use authorized targets, and document external effects. Unit and CI tests must not require private credentials.

## Documentation and Security

Document new endpoints, environment variables, data types, limitations, and demo-visible changes. Mark planned and partial behavior accurately. Never describe correlation as confirmed identity. Do not commit `.env`, tokens, private keys, live credentials, local databases, or unredacted sensitive evidence. Keep private credentials on the backend; `VITE_*` values are browser-visible. Report vulnerabilities privately under [SECURITY.md](SECURITY.md).

