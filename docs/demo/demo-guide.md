# SIH 2026 Demo Guide

## Goal and Safety Boundary

Demonstrate the existing evidence workflow using synthetic or controlled data. Do not use unknown live `.onion` targets during judging. State at the beginning that DHRUVA supports attribution assessment, not automatic proof of identity.

## Preparation

1. Copy `.env.example` to `.env`, change local passwords, and start DHRUVA.
2. Confirm the API at <http://localhost:8000/> and UI at <http://localhost:5173>.
3. If the Compose database is empty, run `docker compose exec backend python scripts/seed_database.py`. The seeder clears its target tables, so use only a disposable demo database.
4. Open Persona Analysis once before the presentation if you want the embedding model downloaded and warm.
5. Confirm the chosen two actors have posts and identifiers so each score can be explained.

## Walkthrough

### 1. Start DHRUVA

```bash
docker compose up --build
```

Show the health endpoint and explain the four Compose services. If Docker is unavailable, use the manual setup in `docs/development/local-setup.md`.

### 2. Open Command Center

Open the root dashboard and point out tracked actors, handles, services, alerts, observations, and high-confidence assessments. Explain that counts come from the current database.

### 3. Choose the Target/Input

Open **Actors**, use its search/filter controls, and select a seeded actor. DHRUVA works from stored evidence; the deterministic demo does not need a live target.

### 4. Show Discovery and Collection

Open **Darknet Collection**. Show status, seeds, recent observations, and the source authorization model. If demonstrating collection, use the controlled mock forum or an approved seed. Explain Tor status honestly; do not claim Tor collection if the proxy is offline.

### 5. Show Collected Evidence

Open the selected actor profile and show handles, PGP identifiers, wallets, posts, sources, and confidence metadata. Point out provenance and timestamps.

### 6. Show Entity Relationships

Open **Graph Intelligence**, select/filter the actor, and show actor-to-handle, PGP, wallet, post, service, infrastructure, relationship, and assessment nodes that are present. Explain that the active API graph is assembled from relational records.

### 7. Show Infrastructure Relationships

Open **Infrastructure** or the profile infrastructure section. Demonstrate stored fingerprints and shared indicators. Only run a new scan against an authorized host.

### 8. Show Behavioral Signals

Open **Persona Analysis**, select two actors, and start the comparison. Explain the behavioral and stylometric signals alongside semantic, handle, and graph scores. If the UI says heuristic fallback, say that the transformer model is unavailable.

### 9. Show Timeline

Open **Timeline**, select an actor, and show chronological evidence. Emphasize that ordering and timestamps support investigation but do not by themselves establish identity.

### 10. Show Supporting Evidence

Review the assessment explanation and positive signal values. Connect each claim back to stored posts, identifiers, or infrastructure rather than the score alone.

### 11. Show Contradicting Evidence

Open **Reports** and select an actor/assessment with seeded negative evidence if available. The UI can display a **Negative / Conflicting Evidence** section. Be explicit that newly generated assessments currently do not derive negative evidence automatically.

### 12. Show the Attribution Assessment

Explain the fused score and confidence label as prioritization. Export CSV, JSON, or STIX 2.1 if useful. Do not promise PDF export; it is not implemented.

### 13. Explain Uncertainty and Abstention

Close with a low-evidence or fallback example. State that the current build does not enforce an automatic abstention state, so analysts must abstain when evidence is sparse, contradictory, unverified, or produced by a degraded model path.

## Suggested Closing

“DHRUVA makes evidence and uncertainty inspectable. It helps analysts correlate observations; it does not convert correlation into proof of identity.”

## Demo Recovery

- API unavailable: show the health check and restart the backend.
- Empty data: verify `DATABASE_URL` and seed the disposable demo database.
- Model unavailable: continue with the labeled fallback and use it to discuss graceful degradation.
- Tor offline: use synthetic fixtures and show the explicit offline state.
- External feed unavailable: do not retry indefinitely; explain the dependency and return to stored evidence.

