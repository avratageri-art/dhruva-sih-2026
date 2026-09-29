# Threat Model

## Assets

- Collected content, source references, provenance, and content hashes.
- Actor profiles, identifiers, relationships, analyst decisions, and assessments.
- Database and Neo4j credentials.
- Analyst workstation, Tor proxy, application host, and exported reports.
- Integrity of model inputs, scores, and explanations.

## Actors and Trust Assumptions

- Authorized analysts and developers are trusted to follow scope and handling rules.
- Source content, external feeds, hidden services, and arbitrary API clients are untrusted.
- Synthetic fixtures are controlled but can resemble sensitive data.
- Dependency registries, model hosting, and container registries are supply-chain boundaries.

## Major Threats and Current Controls

| Threat | Impact | Existing control | Remaining gap |
|---|---|---|---|
| Secret committed to Git | Account/system compromise | `.gitignore`, safe template, Gitleaks CI | No server-side policy documented |
| Unauthorized API use | Collection, data access, SSRF-like scanning | Localhost documentation, scoped CORS | No authentication, roles, or rate limiting |
| Malicious source content | Parser abuse, stored harmful content | Normalization and structured storage | No sandbox/content sanitization guarantee |
| Outbound target abuse | Access to unintended hosts | Source authorization fields; `.onion` validation; public-address and port restrictions for infrastructure scans | Production deployments still need an explicit target allow-list and endpoint authorization |
| False attribution | Harm to individuals or investigations | Explanations, confidence, evidence, responsible-use guidance | No enforced abstention/calibration |
| Data leakage | Exposure of sensitive intelligence | Local configuration and ignored databases | No encryption, retention automation, or fine-grained access |
| Evidence tampering | Misleading assessment | SHA-256 content hash and integrity endpoint | No independent timestamp/signature chain |
| Dependency compromise | Code execution/build compromise | npm lockfile, pinned Python requirements, Dependabot configuration | Python advisories remain unresolved and transitive pins are not locked |
| Tor metadata exposure | Operational and legal risk | SOCKS routing checks | Host configuration and DNS behavior require operator validation |

## Abuse Cases

- A user supplies an internal/private host to the infrastructure scanner.
- An unauthenticated remote client starts a crawl or reads stored intelligence.
- A deceptive actor plants shared handles or wallets to create false correlation.
- Synthetic/demo records are presented as verified live intelligence.
- An analyst exports personal or operational data to an uncontrolled device.

## Recommended Production Controls

Add authentication and roles, endpoint-specific authorization, outbound network allow-lists, DNS-rebinding-resistant egress controls, rate limits, centralized audit logs, encryption, secrets management, malware-safe content handling, retention/deletion workflows, dependency scanning, signed releases, backups, and an incident-response plan. Validate legal authority and source scope before every collection activity.

