# Docker Setup

## Services and Ports

| Service | Container role | Host port |
|---|---|---:|
| `frontend` | Vite development server | 127.0.0.1:5173 |
| `backend` | FastAPI/Uvicorn | 127.0.0.1:8000 |
| `postgres` | Relational data | 127.0.0.1:5432 |
| `neo4j` | Browser and Bolt | 127.0.0.1:7474, 127.0.0.1:7687 |

## Start

```bash
cp .env.example .env
docker compose config --quiet
docker compose up --build
```

Change the local passwords in `.env` first. Compose constructs `DATABASE_URL` inside the backend network and injects Neo4j credentials. PostgreSQL and Neo4j data live in named volumes.

## Verify

```bash
curl http://localhost:8000/
```

Open the dashboard at <http://localhost:5173> and API docs at <http://localhost:8000/docs>.

To seed the disposable Compose database:

```bash
docker compose exec backend python scripts/seed_database.py
```

The seeder clears and repopulates its target tables; do not run it against a non-demo database.

## Tor

The repository includes a Windows Tor bundle for manual Windows operation, not a Linux Tor service in Compose. The backend container defaults `TOR_SOCKS_HOST` to `host.docker.internal`; an authorized host-side SOCKS service must listen on the configured port for Tor collection. Synthetic/demo flows do not require Tor.

## Operational Caveats

- The frontend container runs the Vite development server and is not a hardened production web server.
- Source directories are bind-mounted for local development.
- Service ports are bound to host loopback. Database ports still use local `.env` credentials and should remain inaccessible from untrusted users on the workstation.
- The API lacks authentication and must not be internet-exposed.
- First model use may download a large dependency/model.

For public deployment, add a reverse proxy, TLS, authentication/authorization, restricted networks, a secrets manager, read-only images, resource limits, backups, and monitoring. Those controls are not implemented here.

## Stop

```bash
docker compose down
```

`docker compose down -v` deletes database volumes and is intentionally not recommended as a routine command.

