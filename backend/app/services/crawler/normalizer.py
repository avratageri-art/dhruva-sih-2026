"""
normalizer.py — Unified Observation Normalizer & Schema Harmonizer for DarkTrace
All collection adapters (DarkCrawler, Robin, OSINT Feeds, Breach Engine)
pass raw data through this single normalization layer before storage.

Implements:
  - Common Observation Schema
  - SHA-256 Content Integrity Hashing
  - PGP Private Key Exposure Detection & Redaction (Security/Privacy)
  - Comprehensive Entity Extraction (Handles, PGP, Wallets, Onion, Domains, IOCs)
  - Strict separation of Raw Observation vs Normalized Data
  - Lifecycle Status Progression:
      LISTED -> COLLECTION_PENDING -> COLLECTING -> REACHABLE/UNREACHABLE
      -> CONTENT_OBSERVED -> PARSED -> ANALYZED -> ERROR
"""

import re
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse

# Entity Extraction Patterns
REGEX_PATTERNS = {
    # Handles & Usernames
    "handle": re.compile(r"(?:@([a-zA-Z0-9_]{3,30})|\b(?:handle|user|author|vendor|contact|operator)[:\s]+([a-zA-Z0-9_]{3,30}))", re.IGNORECASE),
    "telegram": re.compile(r"(?:https?:\/\/)?(?:t\.me|telegram\.me)\/([a-zA-Z0-9_]{4,32})", re.IGNORECASE),
    
    # Cryptographic Material
    "pgp_public": re.compile(r"-----BEGIN PGP PUBLIC KEY BLOCK-----[\s\S]+?-----END PGP PUBLIC KEY BLOCK-----"),
    "pgp_private": re.compile(r"-----BEGIN PGP PRIVATE KEY BLOCK-----[\s\S]+?-----END PGP PRIVATE KEY BLOCK-----"),
    "pgp_fingerprint": re.compile(r"\b[0-9A-Fa-f]{32}\b|\b[0-9A-Fa-f]{40}\b"),

    # Wallets
    "btc_wallet": re.compile(r"\b(?:[13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[a-zA-HJ-NP-Z0-9]{25,59})\b"),
    "eth_wallet": re.compile(r"\b0x[a-fA-F0-9]{40}\b"),
    "xmr_wallet": re.compile(r"\b(?:4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}|8[0-9AB][1-9A-HJ-NP-Za-km-z]{93})\b"),
    # Non-production identifiers used only by bundled synthetic fixtures.
    "demo_wallet": re.compile(r"\bDEMO_(BTC|ETH|XMR)_WALLET_[A-Z0-9_]+_NOT_VALID\b"),

    # Network Identifiers
    "onion_v2_v3": re.compile(r"\b[a-z2-7]{16,56}\.onion\b", re.IGNORECASE),
    "email": re.compile(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b|\b[a-zA-Z0-9_.+-]+@[a-z2-7]{16,56}\.onion\b", re.IGNORECASE),
    "domain": re.compile(r"\b(?:[a-zA-Z0-9-]+\.)+(?:com|org|net|io|is|ru|cc|to|biz|me|onion)\b", re.IGNORECASE),
    "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
}

SYSTEM_NON_HANDLES = {
    "admin", "support", "escrow", "contact", "telegram", "darkmarket", "forum",
    "login", "register", "search", "faq", "help", "rules", "marketplace",
    "about", "privacy", "terms", "user", "vendor", "feedback", "onion"
}


def compute_sha256(text: str) -> str:
    """Compute SHA-256 digest of utf-8 text."""
    if text is None:
        text = ""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def extract_entities_harmonized(text: str) -> Tuple[Dict[str, Any], str, List[Dict[str, Any]]]:
    """
    Extract all threat intelligence entities from text.
    Security: Detects PGP private key exposure, computes secure hash,
    and REDACTS private key text so sensitive secrets are never logged or stored raw.
    Returns: (entities_dict, sanitized_text, exposure_alerts)
    """
    if not text:
        return {}, "", []

    sanitized_text = text
    exposure_alerts = []

    # Check for PGP private key exposure (Requirement 9)
    private_pgp_hashes = []
    for m in REGEX_PATTERNS["pgp_private"].finditer(text):
        priv_key = m.group(0)
        priv_hash = hashlib.sha256(priv_key.encode("utf-8")).hexdigest()
        private_pgp_hashes.append(priv_hash)
        # Redact in sanitized_text
        sanitized_text = sanitized_text.replace(priv_key, f"[SENSITIVE_PGP_PRIVATE_KEY_REDACTED sha256:{priv_hash[:16]}]")
        exposure_alerts.append({
            "type": "SENSITIVE_KEY_EXPOSURE",
            "severity": "CRITICAL",
            "key_type": "PGP_PRIVATE_KEY",
            "key_sha256": priv_hash,
            "note": "Private key material observed in darknet communication; redacted for evidence integrity."
        })

    # Public PGP Blocks
    public_pgp_blocks = []
    for m in REGEX_PATTERNS["pgp_public"].finditer(sanitized_text):
        public_pgp_blocks.append(m.group(0))

    # PGP Fingerprints
    pgp_fps = []
    for m in REGEX_PATTERNS["pgp_fingerprint"].finditer(sanitized_text):
        fp = m.group(0).upper()
        if len(fp) in (32, 40) and fp not in pgp_fps:
            pgp_fps.append(fp)

    # Handles & Telegram
    handles = []
    telegram = []
    for m in REGEX_PATTERNS["handle"].finditer(sanitized_text):
        h = m.group(1) or m.group(2)
        if h:
            h_clean = h.strip().lstrip("@")
            if len(h_clean) >= 3 and h_clean.lower() not in SYSTEM_NON_HANDLES:
                tag = f"@{h_clean}"
                if tag not in handles:
                    handles.append(tag)

    for m in REGEX_PATTERNS["telegram"].finditer(sanitized_text):
        tg = f"@{m.group(1).lstrip('@')}"
        if tg not in telegram:
            telegram.append(tg)
        if tg not in handles:
            handles.append(tg)

    # Wallets
    btc = list(dict.fromkeys(REGEX_PATTERNS["btc_wallet"].findall(sanitized_text)))
    eth = list(dict.fromkeys(REGEX_PATTERNS["eth_wallet"].findall(sanitized_text)))
    xmr = list(dict.fromkeys(REGEX_PATTERNS["xmr_wallet"].findall(sanitized_text)))
    for match in REGEX_PATTERNS["demo_wallet"].finditer(sanitized_text):
        chain, wallet = match.group(1), match.group(0)
        target = {"BTC": btc, "ETH": eth, "XMR": xmr}[chain]
        if wallet not in target:
            target.append(wallet)
    
    formatted_wallets = []
    for w in btc:
        formatted_wallets.append(f"BTC:{w}")
    for w in eth:
        formatted_wallets.append(f"ETH:{w}")
    for w in xmr:
        formatted_wallets.append(f"XMR:{w[:12]}...")

    # Onion addresses & Domains
    onions = list(dict.fromkeys(REGEX_PATTERNS["onion_v2_v3"].findall(sanitized_text.lower())))
    emails = [e for e in dict.fromkeys(REGEX_PATTERNS["email"].findall(sanitized_text))
              if not e.endswith((".png", ".jpg", ".css", ".js", ".svg"))]
    domains = [d for d in dict.fromkeys(REGEX_PATTERNS["domain"].findall(sanitized_text.lower()))
               if not d.endswith(".onion") and d not in ["localhost", "127.0.0.1"]]
    
    iocs = [ip for ip in dict.fromkeys(REGEX_PATTERNS["ipv4"].findall(sanitized_text))
            if ip not in ["127.0.0.1", "0.0.0.0", "255.255.255.255"]]

    entities = {
        "handles": handles,
        "telegram": telegram,
        "emails": emails,
        "pgps": pgp_fps,
        "pgp_keys": public_pgp_blocks,
        "wallets": formatted_wallets,
        "btc_wallets": btc,
        "eth_wallets": eth,
        "xmr_wallets": xmr,
        "onions": onions,
        "domains": domains,
        "iocs": iocs,
        "private_pgp_exposure": len(private_pgp_hashes) > 0,
        "private_pgp_hashes": private_pgp_hashes,
    }

    return entities, sanitized_text, exposure_alerts


def normalize_observation(
    raw_item: Dict[str, Any],
    collector: str = "DarkTraceCollector"
) -> Dict[str, Any]:
    """
    Converts any collector's raw output into the unified DarkTrace observation schema.
    Keeps raw data reference and produces sanitized, normalized data with SHA-256 hash.
    """
    raw_url = (
        raw_item.get("source_url")
        or raw_item.get("url")
        or raw_item.get("seed_url")
        or raw_item.get("link")
        or ""
    )
    # URL normalization
    clean_url = raw_url.strip()
    if clean_url.startswith("tor://"):
        clean_url = clean_url.replace("tor://", "http://")
    elif clean_url and not clean_url.startswith("http"):
        clean_url = f"http://{clean_url}"

    parsed = urlparse(clean_url)
    service = parsed.netloc.lower() or raw_item.get("service") or "unknown-service"

    # Source & Collector metadata
    source_type = raw_item.get("source_type") or ("onion-service" if ".onion" in clean_url else "osint-feed")
    now_iso = datetime.now(timezone.utc).isoformat()
    raw_ts = raw_item.get("timestamp") or raw_item.get("collection_time") or now_iso

    # Title & Content
    raw_content = raw_item.get("content") or raw_item.get("content_body") or raw_item.get("text") or ""
    title = raw_item.get("title") or raw_item.get("page_title") or raw_item.get("search_title") or service

    # Compute content SHA-256
    content_sha256 = compute_sha256(raw_content)

    # Harmonized entity extraction + redaction
    extracted_entities, sanitized_content, exposure_alerts = extract_entities_harmonized(raw_content + " " + title)

    # Merge with pre-parsed entities if provided by the collector
    pre_extracted = raw_item.get("extracted_entities") or raw_item.get("entities") or {}
    for k, v in pre_extracted.items():
        if isinstance(v, list) and k in extracted_entities and isinstance(extracted_entities[k], list):
            extracted_entities[k] = list(dict.fromkeys(extracted_entities[k] + v))
        elif k not in extracted_entities or not extracted_entities[k]:
            extracted_entities[k] = v

    # Favicon hash if present
    fav_hash = raw_item.get("favicon_murmur_hash") or raw_item.get("metadata", {}).get("favicon_murmur_hash")
    if fav_hash:
        extracted_entities["favicon_hash"] = fav_hash

    # Raw content reference
    raw_ref = raw_item.get("raw_reference") or raw_item.get("raw_content_reference") or f"sha256:{content_sha256[:16]}"

    # Reliability score (0.0 to 1.0)
    reliability = float(raw_item.get("reliability", 0.85))

    # HTTP Status
    http_status = int(raw_item.get("status_code", raw_item.get("http_status", 200)))

    # Status progression: REACHABLE vs UNREACHABLE, CONTENT_OBSERVED, PARSED
    if http_status in (200, 201, 206) and raw_content:
        obs_status = "CONTENT_OBSERVED"
    elif http_status == 0 or "error" in str(raw_item.get("status", "")).lower():
        obs_status = "UNREACHABLE"
    else:
        obs_status = "REACHABLE"

    # Common Observation Schema (Requirement 3 & 8)
    normalized = {
        "source_url": clean_url,
        "source_type": source_type,
        "service": service,
        "collector": collector,
        "collection_time": raw_ts,
        "title": title[:200] if title else "Untitled Observation",
        "content": sanitized_content,
        "raw_content_reference": raw_ref,
        "http_status": http_status,
        "content_sha256": content_sha256,
        "extracted_entities": extracted_entities,
        "provenance": {
            "collector": collector,
            "engine": raw_item.get("engine", "direct"),
            "query": raw_item.get("query"),
            "headers": raw_item.get("headers", {}),
            "tls_cipher": raw_item.get("tls_cipher"),
            "favicon_murmur_hash": fav_hash,
            "raw_reference": raw_ref,
            "exposure_alerts": exposure_alerts,
        },
        "reliability": reliability,
        "status": obs_status,
    }

    return normalized
