# Security Policy

## Supported Versions

DHRUVA has not yet published a versioned release. Security fixes are applied to the current default branch only. Update this policy when releases are tagged.

## Reporting a Vulnerability

Do not open a public issue containing exploit details, credentials, personal data, sensitive source locations, or unredacted evidence. Use GitHub **Private vulnerability reporting** if it is enabled. Otherwise, contact the repository owner through a private channel shown on the owner's GitHub profile and disclose only enough information to establish a secure reporting path.

The repository does not provide a verified security email address, so none is invented here. Maintainers should acknowledge a private report, agree on a disclosure timeline, and credit the reporter if requested.

## Responsible Disclosure

- Minimize access to affected data and systems.
- Do not test against third-party services without authorization.
- Provide reproduction steps, affected components, impact, and suggested mitigations privately.
- Allow maintainers reasonable time to validate and remediate before public disclosure.

## Secret Exposure Procedure

1. Revoke or rotate the exposed credential immediately at the issuing service.
2. Remove it from the working tree and replace it with an environment variable.
3. Review access and audit logs for misuse.
4. Check Git history, releases, CI logs, forks, and caches.
5. Coordinate any history rewrite; deleting the latest file does not remove historical exposure.
6. Re-run Gitleaks and document the incident without reproducing the secret.

## Data Handling

DHRUVA can store handles, email addresses, wallet identifiers, PGP material, posts, source references, and inferred relationships. Treat collected data as sensitive. Use synthetic data for demonstrations, apply minimization and retention limits, encrypt production storage and backups, and restrict access according to law and authorization.

See [data handling](docs/security/data-handling.md).

## Security Limitations

The current project has no authentication, authorization, rate limiting, encrypted application-level storage, or production secrets manager. Crawler and infrastructure endpoints can initiate outbound requests. Public-address validation and response limits reduce risk but are not a substitute for an authenticated API and network egress policy. Development servers and default Compose ports must not be exposed to an untrusted network. Attribution output is an analytical assessment, not proof of identity.

