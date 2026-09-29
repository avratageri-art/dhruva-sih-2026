# Data Handling

## Data Categories

DHRUVA models posts and observations; aliases/handles; email, PGP, wallet, domain, and onion identifiers; timestamps; source references; infrastructure fingerprints; candidate actor links; alerts; and attribution assessments. These values may be personal data, sensitive intelligence, or intentionally deceptive source material.

## Provenance

Keep source name/type, raw reference, collection method, timestamps, reliability, and content hash with every observation. A SHA-256 match verifies that stored content has not changed since hashing; it does not prove who published it or when it first appeared.

## Collection

- Collect only from controlled, public, or explicitly authorized sources.
- Keep DeepDarkCTI-discovered sources disabled until an analyst authorizes collection.
- Use synthetic fixtures for demos.
- Do not bypass access controls or acquire credential dumps, malware, or illegal material.
- Stop collection if scope, ownership, or legal authority is uncertain.

## Storage and Access

Local SQLite databases and generated JSON are excluded from Git. Compose databases persist in local Docker volumes. The current application has no authentication or application-level encryption, so use an isolated machine/network and least-privilege filesystem access. Do not use this configuration for sensitive production data.

## Exports

CSV, JSON, and STIX downloads are created in the analyst's browser. Review exports for personal data and source sensitivity, label them as analytical assessments, store them only in approved locations, and delete them under the applicable retention policy.

## Retention and Deletion

The application does not automate retention or deletion. Before operational use, define purpose, legal basis, retention duration, review cadence, correction process, and secure deletion for databases, volumes, logs, backups, and exports.

## Demonstration Data

Repository fixtures and seed scripts are intended to be synthetic/controlled. Keep that label visible during demos. Validate newly added fixtures so they do not contain real secrets, private personal data, or actionable illegal content.

