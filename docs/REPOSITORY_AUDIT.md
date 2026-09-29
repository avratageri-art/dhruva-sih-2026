# DHRUVA Repository Audit

Audit date: 2026-09-29 (Asia/Calcutta)

## 1. Project Overview

DHRUVA (Dark-web Hunt & Relationship-based Unified Verification Architecture) is an existing React/FastAPI research and demonstration platform. This pass preserved the application and focused on public branding, reproducibility, security boundaries, documentation, GitHub configuration, and honest validation. DHRUVA assists analysts; it does not prove identity or guarantee attribution.

## 2. Existing Architecture

- React 18/Vite browser dashboard with Cytoscape and Recharts.
- FastAPI service with SQLAlchemy models and actor, analysis, ingestion, collection, alerts, infrastructure, DeepDarkCTI, and graph routes.
- SQLite for manual development; PostgreSQL in Compose.
- Neo4j container and helper module, while current API graph responses primarily use relational records.
- Sentence Transformer semantic similarity plus stylometric, behavioral, handle, and graph/infrastructure signals.
- Synthetic fixtures, mock forum, public OSINT helpers, Tor SOCKS5 collection, DeepDarkCTI catalogue integration, and Robin search.

## 3. Existing Features

The UI exposes Command Center, Actors, actor profiles, Persona Analysis, Graph Intelligence, Timeline, Infrastructure, Darknet Collection, Robin Search, Alerts, Reports, Models, and Architecture. Reports export CSV, JSON, and STIX 2.1 in the browser. Investigations and Settings are placeholders.

The backend stores actors, handles, PGP identifiers, wallets, posts, domains, onion services, indicators, sources, observations, alerts, relationships, and assessments. Observation resolution supports analyst link or dismiss actions.

## 4. Implemented Features

- Relational evidence storage, provenance metadata, timestamps, extracted entities, and SHA-256 content hashes.
- Actor, timeline, graph, evidence, infrastructure, alerts, and assessment API views.
- Weighted semantic, stylometric, behavioral, handle, and graph assessment with a labeled heuristic fallback.
- Controlled demo seeding and a self-hosted mock forum.
- Source registration, authorized collection cycles, DeepDarkCTI controls, Tor status, and observation review.
- Public-host TLS/banner fingerprinting, now restricted to ports 80/443 and non-private resolved addresses.
- API docs at `/docs`, Docker Compose model, CI, Gitleaks workflow, and Dependabot configuration.

## 5. Partially Implemented Features

- Neo4j helpers exist, but Neo4j is not the primary graph API store.
- Negative evidence can be stored/displayed, but live assessments initialize it empty.
- Tor behavior depends on a reachable proxy or the bundled Windows runtime; the Linux image has no Tor service.
- MLflow is used by a training script, not an integrated product workflow.
- Analyst abstention is documented but not enforced as a state or evidence threshold.

## 6. Planned Features

Not implemented: authentication, roles, audit logging, production authorization, automatic abstention, calibrated evidence sufficiency, PDF export, production task queues/observability, and hardened deployment manifests. The code contains placeholder Investigations and Settings pages.

## 7. Repository Changes

- Rebranded public documentation, API metadata, UI labels, and report exports to DHRUVA while retaining compatibility-sensitive legacy paths and package/database identifiers.
- Added safer source defaults: a newly registered seed is `DISCOVERED` and unauthorized unless explicitly enabled.
- Added HTTP(S) `.onion` validation, redirect-boundary checking, a 2 MiB page limit, and a 512 KiB favicon limit.
- Added public-address validation and ports 80/443 restriction to infrastructure scans; redirects are not followed by the banner request.
- Kept Compose credentials environment-driven, restricted CORS origins, and bound published Compose ports to host loopback.

## 8. Documentation Added

The repository includes the root README, security/contribution/conduct/changelog files, architecture and data-flow guides, correlation pipeline, local setup, debugging, testing, Docker, API, threat model, data handling, SIH demo guide, issue forms, pull-request template, and Dependabot configuration.

## 9. Security Improvements

- Secret and runtime-artifact ignore rules plus a safe `.env.example`.
- Gitleaks workflow for pushes, pull requests, and manual runs.
- Private vulnerability-reporting guidance without an invented email address.
- CORS restricted to configured origins with credentialed CORS disabled.
- Explicit collection authorization defaults and bounded Tor responses.
- SSRF reduction for infrastructure scans and `.onion` target validation.

These controls do not make the unauthenticated development API safe for internet exposure.

## 10. Secret Scan Results

A working-tree scan checked common AWS, Google, OpenAI, GitHub token, password-assignment, connection-string, and private-key patterns. No credential pattern was found in source or documentation. An ignored `backend/.env` was discovered during the final Git audit; its Neo4j password differed from the safe example and did not look like a placeholder. The file was removed without exposing its value. Because the credential's origin and reuse are unknown, the owner must rotate it and audit the affected Neo4j instance. No committed history exists locally, so this file was not present in local Git history. Gitleaks is not installed locally, so its workflow has not yet run. Never treat a pattern scan as proof that no secret exists.

## 11. Dependency Findings

- `npm audit --omit=dev`: passed with 0 reported vulnerabilities (122-package audit metadata before install; `npm ci` later restored 98 packages and also reported 0).
- Recharts 2.x reports itself deprecated; it was not upgraded because migration is an application change.
- `pip-audit` could not perform a full dependency resolution under the available Python 3.14 because the Python 3.11-era `psycopg2-binary` pin has no compatible wheel and attempted a source build without `pg_config`.
- A direct-pin-only audit (`--no-deps --disable-pip`) found 75 unique advisories across five packages: FastAPI 0.103.1 (1), scikit-learn 1.3.1 (1), MLflow 2.7.1 (69), pytest 7.4.2 (1), and Requests 2.31.0 (3). This mode does not assess transitive dependencies.

Dependencies were not blindly upgraded because the backend could not be regression-tested in its documented Python 3.11 environment. Before public operational use, test a staged upgrade, especially separating or upgrading the optional MLflow training stack.

## 12. Docker Validation

- `docker compose --env-file .env.example config --quiet`: passed.
- Backend image build: not run successfully because the Docker Desktop Linux engine was not running; the attempt failed before build execution.
- The development stack binds 5173, 8000, 5432, 7474, and 7687 to host loopback and uses bind mounts. It is not a production deployment.

## 13. Tests Run

| Check | Result |
|---|---|
| Python compile (`backend`, `ai`, `graph`, `scripts`) | Passed with system Python 3.14 |
| Infrastructure local/private target guard | Passed for loopback, localhost, and link-local metadata address |
| Frontend `npm ci` | Passed |
| Frontend production build | Passed; 940 kB JS chunk warning |
| `npm audit --omit=dev` | Passed; 0 reported vulnerabilities |
| Compose configuration validation | Passed |
| Targeted working-tree secret patterns | Passed; no candidates |
| Backend pytest | Not run: project dependencies/pytest are not installed for system Python, Python 3.11 is unavailable, and Docker is stopped |
| Browser smoke test | Not run |
| Network/Tor integration scripts | Not run; require explicit authorization and external services |

## 14. Build Results

Vite 8.3.1 transformed 1,423 modules and completed the production build. The generated JavaScript was about 940 kB before compression and triggered a non-fatal chunk-size warning. Python source compilation passed, but this is not a substitute for importing the full dependency stack or running tests.

## 15. Git History Findings

The directory contains a Git repository on `main`, but it has no commits and every project file is currently untracked. There is therefore no local commit history to inspect or rewrite. If this directory came from another repository or archive, audit that original history separately before publishing. No force push, commit deletion, or history rewrite was performed.

## 16. Known Issues

- No authentication, authorization, API rate limiting, or production egress policy.
- Unresolved Python dependency advisories, dominated by MLflow 2.7.1.
- Frontend container runs a Vite development server; database ports are exposed on host loopback.
- Backend tests, full Docker build, runtime smoke test, and browser navigation remain unverified.
- Automatic contradictory-evidence discovery and abstention are absent.
- Synthetic/demo fallbacks must not be represented as live intelligence.
- Bundled Windows Tor executables/libraries require provenance, license, version, and malware-scanning verification before public distribution.
- No license file exists; default copyright restrictions apply until the owner chooses a license.

## 17. Manual Actions Required

1. Add team names, institution, SIH problem-statement ID, approved contact information, and final repository URL.
2. Choose and add a license before public release.
3. Start Docker Desktop; run the full image build, stack startup, seeding, API health, and browser smoke test.
4. Run pytest under Python 3.11 and stage/test dependency upgrades based on the audit above.
5. Install/run Gitleaks locally or confirm the GitHub workflow passes after the first push.
6. Verify the bundled Tor artifacts' origin, checksums, version, redistribution license, and malware-scan result; remove or redistribute them separately if verification fails.
7. Enable GitHub private vulnerability reporting, secret scanning, branch protection, required reviews, and Dependabot where available.
8. Replace example local passwords in `.env`; keep that file untracked.
9. Audit any upstream/original Git history for credentials and private data.
10. Rotate the Neo4j password that was stored in the removed `backend/.env` and review that service's access logs/configuration.

## 18. Final GitHub Readiness

The repository is ready for owner review and an initial private push. Its public identity, setup path, architecture, implemented/partial/planned status, evidence caveats, responsible-use boundary, CI, and security reporting path are documented. Public or operational release should wait for the license/team decisions, Python dependency remediation, Docker/backend/browser validation, Gitleaks run, and Tor-binary provenance review listed above.
