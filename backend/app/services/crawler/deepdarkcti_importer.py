"""
deepdarkcti_importer.py — deepdarkCTI Source Registry Importer for DarkTrace

Role:
    deepdarkCTI → Source Discovery → DarkTrace Source Registry
    
This module fetches source lists from the deepdarkCTI GitHub repository,
parses markdown tables, normalizes entries into the DarkTrace SeedSource schema,
and stores them with proper catalogue vs. collection status separation.

KEY RULE:
    catalogue_status (from deepdarkCTI) ≠ collection_status (from real DarkTrace collection)
    deepdarkCTI says "ONLINE" → that is catalogue information only.
    DarkTrace must independently verify reachability before setting collection_status=REACHABLE.
"""

import re
import logging
import hashlib
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

import requests

logger = logging.getLogger("DeepDarkCTI")

# ─────────────────────────────────────────────────────────────────
# SOURCE FILES FROM deepdarkCTI (GitHub raw URLs)
# ─────────────────────────────────────────────────────────────────
DEEPDARKCTI_BASE = "https://raw.githubusercontent.com/fastfire/deepdarkCTI/main"

DEEPDARKCTI_FILES = {
    "forum":          f"{DEEPDARKCTI_BASE}/forum.md",
    "ransomware_gang": f"{DEEPDARKCTI_BASE}/ransomware_gang.md",
    "markets":        f"{DEEPDARKCTI_BASE}/markets.md",
    "exploits":       f"{DEEPDARKCTI_BASE}/exploits.md",
    "search_engines": f"{DEEPDARKCTI_BASE}/search_engines.md",
    "maas":           f"{DEEPDARKCTI_BASE}/maas.md",
    "discord":        f"{DEEPDARKCTI_BASE}/discord.md",
    "phishing":       f"{DEEPDARKCTI_BASE}/phishing.md",
    "defacement":     f"{DEEPDARKCTI_BASE}/defacement.md",
    "others":         f"{DEEPDARKCTI_BASE}/others.md",
    "telegram_threat_actors": f"{DEEPDARKCTI_BASE}/telegram_threat_actors.md",
}

# Category display mappings (for DarkTrace UI)
CATEGORY_DISPLAY = {
    "forum":          "FORUM",
    "ransomware_gang": "RANSOMWARE_GANG",
    "markets":        "MARKET",
    "exploits":       "EXPLOIT_MARKET",
    "search_engines": "DARK_SEARCH_ENGINE",
    "maas":           "MALWARE_AS_SERVICE",
    "discord":        "DISCORD",
    "phishing":       "PHISHING",
    "defacement":     "DEFACEMENT",
    "others":         "OTHER_CTI",
    "telegram_threat_actors": "TELEGRAM_THREAT_ACTOR",
}

# Regex to parse Markdown table rows
_MD_ROW = re.compile(r"^\|(.+?)\|(.+?)\|(.*)$")
# Extract URL from markdown link: [Name](URL)
_MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
# PGP fingerprint in notes (40 hex chars)
_PGP_FP  = re.compile(r"\b([0-9A-Fa-f]{40})\b")
# Onion address
_ONION   = re.compile(r"\b([a-z2-7]{16,56}\.onion)\b", re.IGNORECASE)
# Telegram handle
_TG_LINK = re.compile(r"https?://t\.me/([a-zA-Z0-9_]{4,32})", re.IGNORECASE)


def _parse_markdown_table(text: str, category: str) -> List[Dict[str, Any]]:
    """
    Parse a deepdarkCTI markdown table into normalized source records.
    Handles both forum.md (3-col) and ransomware_gang.md (5-col) formats.
    """
    sources = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|") or "---" in line or "Name" in line.split("|")[1]:
            continue

        parts = [p.strip() for p in line.split("|")]
        parts = [p for p in parts if p]  # remove empty from leading/trailing |
        if len(parts) < 2:
            continue

        # Extract name + URL from first column
        name_col = parts[0]
        link_m = _MD_LINK.search(name_col)
        if link_m:
            source_name = link_m.group(1).strip()
            source_url  = link_m.group(2).strip()
        else:
            source_name = name_col.strip()
            source_url  = ""

        if not source_url:
            continue

        # Status from second column
        catalogue_status = parts[1].strip().upper() if len(parts) > 1 else "UNKNOWN"
        if catalogue_status not in ("ONLINE", "OFFLINE", "UNKNOWN"):
            catalogue_status = "UNKNOWN"

        # Notes: remaining columns joined
        notes_raw = " | ".join(parts[2:]) if len(parts) > 2 else ""

        # Detect onion address
        onion_match = _ONION.search(source_url)
        onion_addr = onion_match.group(1).lower() if onion_match else None
        is_onion = bool(onion_addr)
        source_type = "onion-service" if is_onion else "clearnet-forum"

        # Detect PGP fingerprint in notes
        pgp_fp = None
        pgp_m = _PGP_FP.search(notes_raw)
        if pgp_m:
            pgp_fp = pgp_m.group(1).upper()

        # Detect Telegram channels in notes
        tg_channels = _TG_LINK.findall(notes_raw)

        # Build stable source_id from URL hash
        source_id_hash = hashlib.sha256(source_url.encode()).hexdigest()[:16]

        sources.append({
            "source_id":           f"ddc-{source_id_hash}",
            "source_name":         source_name,
            "source_url":          source_url,
            "source_type":         source_type,
            "category":            CATEGORY_DISPLAY.get(category, "OTHER_CTI"),
            "onion_address":       onion_addr,
            "catalogue_source":    "deepdarkCTI",
            "catalogue_status":    catalogue_status,
            "collection_status":   "DISCOVERED",    # Not yet verified by DarkTrace
            "notes":               notes_raw[:500] if notes_raw else None,
            "pgp_fingerprint":     pgp_fp,
            "telegram_channels":   tg_channels,
        })

    return sources


def fetch_category(category: str, timeout: int = 15) -> Tuple[List[Dict[str, Any]], str, Optional[str]]:
    """
    Fetch a deepdarkCTI category file and parse it.
    Returns (sources_list, fetched_at_iso, error_or_None).
    """
    url = DEEPDARKCTI_FILES.get(category)
    if not url:
        return [], "", f"Unknown category: {category}"

    fetched_at = datetime.now(timezone.utc).isoformat()
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "DarkTrace-CTI-Importer/1.0"})
        resp.raise_for_status()
        sources = _parse_markdown_table(resp.text, category)
        logger.info(f"[deepdarkCTI] Category '{category}': fetched {len(sources)} sources.")
        return sources, fetched_at, None
    except Exception as e:
        logger.error(f"[deepdarkCTI] Failed to fetch category '{category}': {e}")
        return [], fetched_at, str(e)


def refresh_all(timeout: int = 20) -> Dict[str, Any]:
    """
    Fetch all configured deepdarkCTI categories and return combined results.
    This is the main entry point for the background refresh scheduler.
    """
    result = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total_sources": 0,
        "by_category": {},
        "errors": [],
        "sources": [],
    }

    for category in DEEPDARKCTI_FILES:
        sources, ts, err = fetch_category(category, timeout=timeout)
        result["by_category"][category] = {
            "count": len(sources),
            "fetched_at": ts,
            "error": err,
        }
        if err:
            result["errors"].append(f"{category}: {err}")
        else:
            result["sources"].extend(sources)
            result["total_sources"] += len(sources)

    return result


def upsert_sources_to_db(sources: List[Dict[str, Any]], db_session, refresh_ts: str) -> Dict[str, int]:
    """
    Upsert deepdarkCTI sources into the DarkTrace SeedSource table.
    Uses the existing SeedSource model — no new tables created.
    
    KEY RULE:
        catalogue_status is stored in notes/metadata.
        DarkTrace collection_status starts as 'DISCOVERED' — never inherits catalogue_status.
    """
    from app.models.intelligence import SeedSource

    stats = {"created": 0, "updated": 0, "skipped": 0}
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    for s in sources:
        ref = s["source_url"]
        if not ref:
            stats["skipped"] += 1
            continue

        existing = db_session.query(SeedSource).filter(SeedSource.reference == ref).first()

        # Build metadata note string including catalogue provenance
        note_parts = [f"[deepdarkCTI] catalogue_status={s['catalogue_status']} | category={s['category']}"]
        if s.get("pgp_fingerprint"):
            note_parts.append(f"pgp={s['pgp_fingerprint']}")
        if s.get("telegram_channels"):
            note_parts.append(f"telegram={','.join(s['telegram_channels'])}")
        if s.get("notes"):
            note_parts.append(s["notes"][:200])
        combined_notes = " | ".join(note_parts)

        if existing:
            # Update catalogue metadata but do NOT change collection_status
            existing.name = s["source_name"]
            existing.category = s["category"]
            existing.notes = combined_notes
            # Update last_seen only (first_seen stays original)
            existing.last_seen = now
            stats["updated"] += 1
        else:
            seed = SeedSource(
                reference=ref,
                name=s["source_name"],
                status="DISCOVERED",           # DarkTrace lifecycle — not catalogue
                authorized=0,                  # Not yet authorized for collection — analyst must enable
                category=s["category"],
                collection_frequency="manual", # Do not auto-collect until analyst enables
                reliability=0.5,              # Low initial reliability until verified
                notes=combined_notes,
                first_seen=now,
                last_seen=now,
                error_count=0,
                observation_count=0,
            )
            db_session.add(seed)
            stats["created"] += 1

    try:
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        logger.error(f"[deepdarkCTI] DB upsert failed: {e}")
        raise

    logger.info(f"[deepdarkCTI] DB upsert complete: created={stats['created']} updated={stats['updated']} skipped={stats['skipped']}")
    return stats
