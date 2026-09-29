"""
breach_engine.py — Breach Correlation & Lookup Engine for DarkTrace
Queries data/breaches/breaches.db when any handle or email is extracted,
appending matched breach details to the actor's intelligence profile.
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set

logger = logging.getLogger("BreachEngine")

# Resolve breach database paths
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(MODULE_DIR, "..", "..", ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))

BREACH_DB_PATHS = [
    os.path.join(PROJECT_ROOT, "data", "breaches", "breaches.db"),
    os.path.join(BACKEND_DIR, "data", "breaches", "breaches.db"),
]


def find_breach_db() -> Optional[str]:
    """Locate the breaches.db file."""
    for path in BREACH_DB_PATHS:
        if os.path.isfile(path):
            return path
    return None


class BreachLookupEngine:
    """
    Queries the breach correlation database for handles, emails, and other
    identifiers extracted from crawler and forum observations.
    Returns matched breach records with contextual details.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or find_breach_db()
        if not self.db_path:
            logger.warning("Breach database not found. Checked paths: " + str(BREACH_DB_PATHS))

    def _get_connection(self) -> Optional[sqlite3.Connection]:
        """Get a SQLite connection to the breach database."""
        if not self.db_path or not os.path.isfile(self.db_path):
            return None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to breach DB: {e}")
            return None

    def lookup_handle(self, handle: str) -> List[Dict[str, Any]]:
        """
        Search breach records by handle (case-insensitive, stripped of @ prefix).
        """
        conn = self._get_connection()
        if not conn:
            return []

        clean_handle = handle.strip().lstrip("@").lower()
        try:
            cursor = conn.execute(
                "SELECT * FROM breach_records WHERE LOWER(REPLACE(handle, '@', '')) = ?",
                (clean_handle,)
            )
            results = [dict(row) for row in cursor.fetchall()]
            logger.info(f"[BreachEngine] Handle '{clean_handle}' → {len(results)} breach records found")
            return results
        except Exception as e:
            logger.error(f"Breach handle lookup error: {e}")
            return []
        finally:
            conn.close()

    def lookup_email(self, email: str) -> List[Dict[str, Any]]:
        """
        Search breach records by email address (case-insensitive).
        """
        conn = self._get_connection()
        if not conn:
            return []

        clean_email = email.strip().lower()
        try:
            cursor = conn.execute(
                "SELECT * FROM breach_records WHERE LOWER(email) = ?",
                (clean_email,)
            )
            results = [dict(row) for row in cursor.fetchall()]
            logger.info(f"[BreachEngine] Email '{clean_email}' → {len(results)} breach records found")
            return results
        except Exception as e:
            logger.error(f"Breach email lookup error: {e}")
            return []
        finally:
            conn.close()

    def lookup_ip(self, ip_address: str) -> List[Dict[str, Any]]:
        """
        Search breach records by IP address.
        """
        conn = self._get_connection()
        if not conn:
            return []

        try:
            cursor = conn.execute(
                "SELECT * FROM breach_records WHERE ip_address = ?",
                (ip_address.strip(),)
            )
            results = [dict(row) for row in cursor.fetchall()]
            return results
        except Exception as e:
            logger.error(f"Breach IP lookup error: {e}")
            return []
        finally:
            conn.close()

    def bulk_lookup(
        self,
        handles: Optional[List[str]] = None,
        emails: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Perform a bulk lookup across handles and emails.
        Returns a unified result with all matches and metadata summary.
        """
        all_matches: List[Dict[str, Any]] = []
        matched_breaches: Set[str] = set()
        matched_handles: Set[str] = set()
        matched_emails: Set[str] = set()

        # Look up handles
        for handle in (handles or []):
            results = self.lookup_handle(handle)
            for r in results:
                matched_handles.add(handle)
                matched_breaches.add(r.get("breach_name", ""))
                r["matched_via"] = f"handle:{handle}"
                all_matches.append(r)

        # Look up emails
        for email in (emails or []):
            results = self.lookup_email(email)
            for r in results:
                matched_emails.add(email)
                matched_breaches.add(r.get("breach_name", ""))
                r["matched_via"] = f"email:{email}"
                # Avoid duplicate entries (same breach + same handle/email)
                if not any(
                    m.get("breach_name") == r.get("breach_name") and
                    m.get("handle") == r.get("handle") and
                    m.get("email") == r.get("email")
                    for m in all_matches
                ):
                    all_matches.append(r)

        return {
            "total_matches": len(all_matches),
            "matched_breaches": list(matched_breaches),
            "matched_handles": list(matched_handles),
            "matched_emails": list(matched_emails),
            "records": all_matches,
        }

    def get_breach_metadata(self, breach_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Return metadata about breaches in the database.
        If breach_name is given, return only that breach's metadata.
        """
        conn = self._get_connection()
        if not conn:
            return []

        try:
            if breach_name:
                cursor = conn.execute(
                    "SELECT * FROM breach_metadata WHERE breach_name = ?",
                    (breach_name,)
                )
            else:
                cursor = conn.execute("SELECT * FROM breach_metadata")
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Breach metadata query error: {e}")
            return []
        finally:
            conn.close()

    def get_stats(self) -> Dict[str, Any]:
        """Return summary statistics about the breach database."""
        conn = self._get_connection()
        if not conn:
            return {"status": "unavailable", "db_path": self.db_path}

        try:
            total_records = conn.execute("SELECT COUNT(*) FROM breach_records").fetchone()[0]
            total_breaches = conn.execute("SELECT COUNT(*) FROM breach_metadata").fetchone()[0]
            unique_handles = conn.execute(
                "SELECT COUNT(DISTINCT handle) FROM breach_records WHERE handle IS NOT NULL"
            ).fetchone()[0]
            unique_emails = conn.execute(
                "SELECT COUNT(DISTINCT email) FROM breach_records WHERE email IS NOT NULL"
            ).fetchone()[0]

            severity_dist = {}
            for row in conn.execute(
                "SELECT severity, COUNT(*) as cnt FROM breach_records GROUP BY severity"
            ).fetchall():
                severity_dist[row["severity"]] = row["cnt"]

            return {
                "status": "online",
                "db_path": self.db_path,
                "total_records": total_records,
                "total_breaches": total_breaches,
                "unique_handles": unique_handles,
                "unique_emails": unique_emails,
                "severity_distribution": severity_dist,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
        finally:
            conn.close()


def enrich_entities_with_breaches(entities: Dict[str, Any]) -> Dict[str, Any]:
    """
    Given extracted entities (with 'handles' and 'emails'), perform breach lookups
    and return enriched entities with breach correlation data attached.
    """
    engine = BreachLookupEngine()

    handles = entities.get("handles", [])
    emails = entities.get("emails", [])

    if not handles and not emails:
        return entities

    breach_results = engine.bulk_lookup(handles=handles, emails=emails)

    if breach_results["total_matches"] > 0:
        entities["breach_correlations"] = {
            "total_matches": breach_results["total_matches"],
            "matched_breaches": breach_results["matched_breaches"],
            "records": [
                {
                    "breach_name": r.get("breach_name"),
                    "breach_date": r.get("breach_date"),
                    "source_platform": r.get("source_platform"),
                    "handle": r.get("handle"),
                    "email": r.get("email"),
                    "ip_address": r.get("ip_address"),
                    "severity": r.get("severity"),
                    "matched_via": r.get("matched_via"),
                    "additional_data": r.get("additional_data"),
                }
                for r in breach_results["records"]
            ],
        }
        logger.info(
            f"[BreachEngine] Enriched entities with {breach_results['total_matches']} breach correlations "
            f"from {len(breach_results['matched_breaches'])} breaches"
        )

    return entities


# CLI standalone test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = BreachLookupEngine()

    print("\n" + "=" * 60)
    print("DARKTRACE Breach Correlation Engine — Self-Test")
    print("=" * 60)

    stats = engine.get_stats()
    print(f"\nDatabase: {stats.get('status')}")
    print(f"  Path: {stats.get('db_path')}")
    print(f"  Records: {stats.get('total_records')}")
    print(f"  Breaches: {stats.get('total_breaches')}")
    print(f"  Unique Handles: {stats.get('unique_handles')}")
    print(f"  Unique Emails: {stats.get('unique_emails')}")
    print(f"  Severity: {stats.get('severity_distribution')}")

    # Test lookups
    print("\n--- Handle Lookups ---")
    for handle in ["shadow_fox99", "zerobyte_off", "crimson_dump", "phantom_ddos"]:
        results = engine.lookup_handle(handle)
        print(f"  @{handle}: {len(results)} records")
        for r in results:
            print(f"    → {r['breach_name']} ({r['breach_date']}) severity={r['severity']}")

    print("\n--- Email Lookups ---")
    for email in ["shadow-operator@example.invalid", "zerobyte-operator@example.invalid", "crimson-analyst@example.invalid"]:
        results = engine.lookup_email(email)
        print(f"  {email}: {len(results)} records")

    # Test enrichment
    print("\n--- Entity Enrichment Test ---")
    test_entities = {
        "handles": ["@shadow_fox99", "@zerobyte_off"],
        "emails": ["shadow-operator@example.invalid"],
    }
    enriched = enrich_entities_with_breaches(test_entities)
    bc = enriched.get("breach_correlations", {})
    print(f"  Total matches: {bc.get('total_matches', 0)}")
    print(f"  Breaches: {bc.get('matched_breaches', [])}")
