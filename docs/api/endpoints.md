# API Overview

Run the backend and open <http://localhost:8000/docs> for the generated OpenAPI interface. This page lists route families rather than duplicating every request/response schema.

| Prefix | Purpose | Representative operations |
|---|---|---|
| `/` | Health | Backend status and internal project label |
| `/api/dashboard` | Dashboard | Aggregate counts and DeepDarkCTI summary |
| `/api/model-status` | Model | Lazy model status and subsystem description |
| `/api/actors` | Actors | List/detail, timeline, evidence, relationships, wallet clusters, infrastructure |
| `/api/analysis` | Assessments | List/create assessments, intelligence, infrastructure, relationships, graph |
| `/api/graph` | Graph aliases | Graph, actor graph, search, relationships |
| `/api/ingest` | Live OSINT | Fetch the configured public ransomware telemetry feed |
| `/api/alerts` | Alerts | List, create, acknowledge |
| `/api/infra` | Infrastructure | Scan, fingerprints, shared indicators, targets |
| `/api/crawler` | Collection | Status, Tor checks, seeds, observations, collection, worker, OSINT, mock forum, Robin |
| `/api/deepdarkcti` | Catalogue collection | Status, refresh, source controls, collection, scheduler |

## High-Impact Endpoints

Collection, seed probe, infrastructure scan, live ingestion, scheduler, worker, and Robin search endpoints can make outbound requests or mutate data. The current API has no authentication. Keep it bound to a trusted development environment.

## Assessment Semantics

`POST /api/analysis/assess` compares two stored actors selected by query parameters. It stores and returns a score, label, explanation, and subsystem evidence. A fallback result can be returned if the AI engine is unavailable. Scores are not proof of identity.

## Errors and External Dependencies

Tor and public-feed operations may fail because of proxy state, remote availability, rate limits, or network policy. Clients should display those failures honestly and should not substitute stale/demo data without labeling it.

