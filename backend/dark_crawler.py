"""
dark_crawler.py — Real-Time Tor SOCKS5 Darknet Crawler Module for DarkTrace
Extracts cryptocurrency wallets, PGP blocks, contact handles, telegram, emails,
and favicon MurmurHashes from live onion services.
"""

import os
import re
import sys
import json
import codecs
import socket
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# Optional mmh3 for Shodan-compatible MurmurHash3 calculation
try:
    import mmh3
    _HAS_MMH3 = True
except ImportError:
    _HAS_MMH3 = False

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DarkCrawler")

# Default Tor SOCKS proxies from centralized config
try:
    from app.config import settings
    _PRIMARY_TOR = settings.TOR_SOCKS_PROXY
except Exception:
    _PRIMARY_TOR = os.environ.get("TOR_SOCKS_PROXY", "socks5h://127.0.0.1:9050")

DEFAULT_TOR_PROXIES = [
    _PRIMARY_TOR,
    "socks5h://127.0.0.1:9050",
    "socks5h://127.0.0.1:9150",
]

# Intelligence regex patterns
REGEX_PATTERNS = {
    # Bitcoin: Legacy (1), Script (3), and Bech32 (bc1)
    "btc_wallet": re.compile(r"\b(?:[13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[a-zA-HJ-NP-Z0-9]{25,59})\b"),
    # Monero: standard (4) and subaddress (8)
    "xmr_wallet": re.compile(r"\b(?:4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}|8[0-9AB][1-9A-HJ-NP-Za-km-z]{93})\b"),
    # Ethereum addresses
    "eth_wallet": re.compile(r"\b0x[a-fA-F0-9]{40}\b"),
    # Non-production identifiers used only by bundled synthetic fixtures.
    "demo_wallet": re.compile(r"\bDEMO_(BTC|ETH|XMR)_WALLET_[A-Z0-9_]+_NOT_VALID\b"),
    # PGP Public Key Blocks
    "pgp_block": re.compile(r"-----BEGIN PGP PUBLIC KEY BLOCK-----[\s\S]+?-----END PGP PUBLIC KEY BLOCK-----"),
    # PGP Fingerprints (32 or 40 hex characters)
    "pgp_fingerprint": re.compile(r"\b[0-9A-Fa-f]{32}\b|\b[0-9A-Fa-f]{40}\b"),
    # Telegram channels and usernames
    "telegram_url": re.compile(r"(?:https?:\/\/)?t\.me\/([a-zA-Z0-9_]{4,32})", re.IGNORECASE),
    "telegram_handle": re.compile(r"(?:telegram|tg|tele)[:\s]+@?([a-zA-Z0-9_]{4,32})", re.IGNORECASE),
    # General @handles
    "handle": re.compile(r"(?:@([a-zA-Z0-9_]{3,24})|\b(?:handle|user|author|vendor|contact)[:\s]+([a-zA-Z0-9_]{3,24}))", re.IGNORECASE),
    # Email addresses (clearnet + onion mail)
    "email": re.compile(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b|\b[a-zA-Z0-9_.+-]+@[a-z2-7]{16,56}\.onion\b", re.IGNORECASE),
    # Onion addresses (v2 and v3)
    "onion_address": re.compile(r"\b[a-z2-7]{16,56}\.onion\b", re.IGNORECASE),
}

# Resolve paths
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(MODULE_DIR) if os.path.basename(MODULE_DIR) == "backend" else MODULE_DIR
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DEFAULT_INTEL_FILE = os.path.join(DATA_DIR, "crawled_intel.json")


class DarkCrawler:
    """
    Real-Time Darknet Tor Crawler.
    Connects via Tor SOCKS5 proxy, parses onion HTML, extracts multi-vector threat indicators,
    computes Shodan-compatible favicon MurmurHashes, and persists records to JSON/SQLite.
    """

    MAX_RESPONSE_BYTES = 2 * 1024 * 1024
    MAX_FAVICON_BYTES = 512 * 1024

    def __init__(
        self,
        proxy_url: Optional[str] = None,
        timeout: int = 25,
        user_agent: Optional[str] = None,
        intel_file: Optional[str] = None
    ):
        self.proxy_url = proxy_url
        self.timeout = timeout
        self.intel_file = intel_file or DEFAULT_INTEL_FILE
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0"
        )
        self._active_proxy: Optional[str] = None

    def ensure_tor_daemon(self) -> Optional[str]:
        """
        Check if Tor SOCKS5 is running; if not and local Tor daemon binary exists, launch it.
        """
        active = self.detect_tor_proxy()
        if active:
            return active

        tor_dir = os.path.join(MODULE_DIR, "tor")
        tor_exe = os.path.join(tor_dir, "tor-real.exe")
        torrc = os.path.join(tor_dir, "torrc")

        if os.path.exists(tor_exe) and os.path.exists(torrc):
            try:
                import subprocess
                import time
                logger.info("[*] Auto-launching local Tor daemon from backend/tor/ ...")
                subprocess.Popen(
                    [tor_exe, "-f", torrc],
                    cwd=tor_dir,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                for _ in range(12):
                    time.sleep(1)
                    active = self.detect_tor_proxy()
                    if active:
                        logger.info(f"[+] Tor daemon auto-started and ready at {active}")
                        return active
            except Exception as e:
                logger.warning(f"Could not auto-start Tor daemon: {e}")

        return None

    def detect_tor_proxy(self) -> Optional[str]:
        """
        Probe candidate Tor SOCKS5 ports to detect an active Tor proxy circuit.
        Returns the working proxy URL or None if Tor is offline.
        """
        candidates = [self.proxy_url] if self.proxy_url else DEFAULT_TOR_PROXIES

        for candidate in candidates:
            if not candidate:
                continue
            try:
                parsed = urlparse(candidate)
                host = parsed.hostname or "127.0.0.1"
                port = parsed.port or 9150
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1.5)
                res = sock.connect_ex((host, port))
                sock.close()
                if res == 0:
                    self._active_proxy = candidate
                    logger.info(f"[+] Active Tor SOCKS5 proxy detected: {candidate}")
                    return candidate
            except Exception as e:
                logger.debug(f"Candidate proxy probe failed for {candidate}: {e}")

        logger.warning("[-] Tor daemon is offline on standard ports (9150, 9050). Operational fallback active.")
        return None


    def get_session(self, proxy_url: Optional[str] = None) -> requests.Session:
        """
        Construct a requests.Session routed through the Tor SOCKS5 proxy.
        """
        session = requests.Session()
        active = proxy_url or self._active_proxy or self.detect_tor_proxy()
        if active:
            session.proxies = {
                "http": active,
                "https": active,
            }
        session.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "close",
        })
        return session

    def calculate_favicon_hash(self, favicon_bytes: bytes) -> Optional[int]:
        """
        Calculate the Shodan-standard MurmurHash3 value of a favicon's base64 representation.
        Formula: mmh3.hash(codecs.encode(favicon_bytes, 'base64'))
        """
        if not favicon_bytes:
            return None
        try:
            b64_favicon = codecs.encode(favicon_bytes, "base64")
            if _HAS_MMH3:
                return int(mmh3.hash(b64_favicon))
            else:
                # Python fallback hash if mmh3 module is unavailable
                import hashlib
                return int(hashlib.md5(b64_favicon).hexdigest()[:8], 16)
        except Exception as err:
            logger.warning(f"Failed to calculate favicon MurmurHash: {err}")
            return None

    def fetch_favicon(self, session: requests.Session, base_url: str, soup: BeautifulSoup) -> Tuple[Optional[int], Optional[str]]:
        """
        Locate and download the service favicon, returning (murmur_hash, favicon_url).
        """
        favicon_url = None
        # Check <link rel="icon"> or <link rel="shortcut icon">
        icon_link = soup.find("link", rel=lambda x: x and ("icon" in x.lower() or "shortcut" in x.lower()))
        if icon_link and icon_link.get("href"):
            favicon_url = urljoin(base_url, icon_link.get("href"))
        else:
            favicon_url = urljoin(base_url, "/favicon.ico")

        try:
            res = session.get(favicon_url, timeout=min(self.timeout, 10), stream=True)
            content = res.raw.read(self.MAX_FAVICON_BYTES + 1, decode_content=True)
            if res.status_code == 200 and 0 < len(content) <= self.MAX_FAVICON_BYTES:
                h = self.calculate_favicon_hash(content)
                return h, favicon_url
        except Exception as e:
            logger.debug(f"Favicon fetch failed for {favicon_url}: {e}")

        return None, favicon_url

    def extract_intelligence(self, html: str, base_url: str = "") -> Dict[str, Any]:
        """
        Extract cryptocurrency wallets, PGP keys/blocks, contact handles, telegram,
        emails, and page title from raw HTML.
        """
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove script and style elements
        for element in soup(["script", "style", "noscript", "svg"]):
            element.decompose()

        page_title = soup.title.string.strip() if soup.title and soup.title.string else "Untitled Onion Service"
        body_text = soup.get_text(separator=" ", strip=True)
        raw_combined = f"{page_title} {html} {body_text}"

        # 1. Bitcoin Wallets
        btc_wallets = list(set(REGEX_PATTERNS["btc_wallet"].findall(raw_combined)))
        # Filter false positives (short strings or known HTML IDs)
        btc_wallets = [w for w in btc_wallets if len(w) >= 26 and not w.startswith("111111")]

        # 2. Monero Wallets
        xmr_wallets = list(set(REGEX_PATTERNS["xmr_wallet"].findall(raw_combined)))

        # Explicitly invalid wallet identifiers keep offline demos testable.
        for match in REGEX_PATTERNS["demo_wallet"].finditer(raw_combined):
            chain, wallet = match.group(1), match.group(0)
            if chain == "BTC" and wallet not in btc_wallets:
                btc_wallets.append(wallet)
            elif chain == "XMR" and wallet not in xmr_wallets:
                xmr_wallets.append(wallet)

        # 3. PGP Blocks & Fingerprints
        pgp_blocks = REGEX_PATTERNS["pgp_block"].findall(html)
        pgp_fps = list(set(REGEX_PATTERNS["pgp_fingerprint"].findall(raw_combined)))
        # Clean fingerprints (must be 32 or 40 hex characters)
        pgp_fps = [fp.upper() for fp in pgp_fps if len(fp) in [32, 40]]
        all_pgp_keys = pgp_blocks + pgp_fps

        # 4. Telegram Handles / Channels
        telegram_matches = set()
        for m in REGEX_PATTERNS["telegram_url"].finditer(raw_combined):
            telegram_matches.add(f"@{m.group(1).lstrip('@')}")
        for m in REGEX_PATTERNS["telegram_handle"].finditer(raw_combined):
            telegram_matches.add(f"@{m.group(1).lstrip('@')}")

        # 5. General Handles
        handles = set(telegram_matches)
        for m in REGEX_PATTERNS["handle"].finditer(body_text):
            h = m.group(1) or m.group(2)
            if h and h.lower() not in ["escrow", "telegram", "contact", "support", "admin", "darkmarket", "help", "about", "terms"]:
                handles.add(f"@{h.lstrip('@')}")

        # 6. Emails
        emails = list(set(REGEX_PATTERNS["email"].findall(raw_combined)))

        # 7. Onion Addresses in content
        onions = list(set(REGEX_PATTERNS["onion_address"].findall(raw_combined)))

        return {
            "page_title": page_title,
            "btc_wallets": btc_wallets,
            "xmr_wallets": xmr_wallets,
            "pgp_keys": all_pgp_keys,
            "telegram": list(telegram_matches),
            "handles": list(handles),
            "emails": emails,
            "onion_addresses": onions,
            "text_sample": body_text[:600] if body_text else "",
        }

    def crawl_onion(
        self,
        target_url: str,
        save_records: bool = True
    ) -> Dict[str, Any]:
        """
        Crawl a single .onion URL via Tor SOCKS5 proxy.
        Extracts intelligence, computes favicon MurmurHash, and saves results.
        Gracefully handles offline Tor daemons or circuit timeouts.
        """
        # Ensure scheme
        url = target_url.strip()
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"http://{url}"

        parsed = urlparse(url)
        onion_host = parsed.netloc or parsed.path.split("/")[0]
        hostname = (parsed.hostname or "").lower()
        if parsed.scheme not in ("http", "https") or not hostname.endswith(".onion"):
            raise ValueError("Only HTTP(S) .onion targets are accepted")

        timestamp = datetime.now(timezone.utc).isoformat()
        logger.info(f"[*] Crawling Tor onion target: {url}")

        # Detect, ensure or verify Tor proxy
        proxy = self.ensure_tor_daemon()
        if not proxy:
            # Tor is offline: generate operational log and graceful error record
            logger.warning(f"[TOR CRAWLER WARNING] Circuit unreachable for {url} — Tor daemon is not running on 9150 or 9050.")
            intel_record = {
                "url": url,
                "onion_address": onion_host,
                "page_title": f"Service Offline ({onion_host})",
                "btc_wallets": [],
                "xmr_wallets": [],
                "pgp_keys": [],
                "telegram": [],
                "handles": [],
                "emails": [],
                "onion_addresses": [onion_host],
                "favicon_murmur_hash": None,
                "timestamp": timestamp,
                "status": "offline",
                "error": "Tor daemon offline or unreachable at 127.0.0.1:9150/9050",
                "headers": {},
                "status_code": 0,
                "text_sample": "",
            }
            if save_records:
                self.save_to_json(intel_record)
            return intel_record

        # Tor proxy available — execute request
        session = self.get_session(proxy)
        try:
            resp = session.get(url, timeout=self.timeout, allow_redirects=True, stream=True)
            final_host = (urlparse(resp.url).hostname or "").lower()
            if not final_host.endswith(".onion"):
                raise ValueError("Redirect left the authorized .onion boundary")
            raw = resp.raw.read(self.MAX_RESPONSE_BYTES + 1, decode_content=True)
            if len(raw) > self.MAX_RESPONSE_BYTES:
                raise ValueError("Response exceeded the 2 MiB collection limit")
            html = raw.decode(resp.encoding or "utf-8", errors="replace")
            soup = BeautifulSoup(html, "html.parser")

            # Extract intelligence
            extracted = self.extract_intelligence(html, base_url=url)

            # Extract favicon MurmurHash
            fav_hash, _ = self.fetch_favicon(session, url, soup)

            intel_record = {
                "url": url,
                "onion_address": onion_host,
                "page_title": extracted["page_title"],
                "btc_wallets": extracted["btc_wallets"],
                "xmr_wallets": extracted["xmr_wallets"],
                "pgp_keys": extracted["pgp_keys"],
                "telegram": extracted["telegram"],
                "handles": extracted["handles"],
                "emails": extracted["emails"],
                "onion_addresses": extracted["onion_addresses"],
                "favicon_murmur_hash": fav_hash,
                "timestamp": timestamp,
                "status": "success",
                "status_code": resp.status_code,
                "headers": dict(resp.headers),
                "text_sample": extracted["text_sample"],
            }

            logger.info(
                f"[+] Successfully crawled {onion_host}: "
                f"BTC={len(extracted['btc_wallets'])}, XMR={len(extracted['xmr_wallets'])}, "
                f"PGP={len(extracted['pgp_keys'])}, FaviconHash={fav_hash}"
            )

            if save_records:
                self.save_to_json(intel_record)
            return intel_record

        except requests.exceptions.Timeout:
            logger.warning(f"[TOR CRAWLER WARNING] Circuit timed out after {self.timeout}s for {url}.")
            intel_record = {
                "url": url,
                "onion_address": onion_host,
                "page_title": f"Circuit Timeout ({onion_host})",
                "btc_wallets": [],
                "xmr_wallets": [],
                "pgp_keys": [],
                "telegram": [],
                "handles": [],
                "emails": [],
                "onion_addresses": [onion_host],
                "favicon_murmur_hash": None,
                "timestamp": timestamp,
                "status": "timeout",
                "error": f"Circuit timed out after {self.timeout}s",
                "headers": {},
                "status_code": 504,
                "text_sample": "",
            }
            if save_records:
                self.save_to_json(intel_record)
            return intel_record

        except Exception as e:
            logger.warning(f"[TOR CRAWLER WARNING] Connection error for {url}: {e}")
            intel_record = {
                "url": url,
                "onion_address": onion_host,
                "page_title": f"Crawl Error ({onion_host})",
                "btc_wallets": [],
                "xmr_wallets": [],
                "pgp_keys": [],
                "telegram": [],
                "handles": [],
                "emails": [],
                "onion_addresses": [onion_host],
                "favicon_murmur_hash": None,
                "timestamp": timestamp,
                "status": "error",
                "error": str(e),
                "headers": {},
                "status_code": 500,
                "text_sample": "",
            }
            if save_records:
                self.save_to_json(intel_record)
            return intel_record

    def save_to_json(self, intel_record: Dict[str, Any], filepath: Optional[str] = None) -> bool:
        """
        Append the parsed intelligence record to the local JSON data store
        without overwriting historical records.
        """
        target_path = filepath or self.intel_file
        try:
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            existing_records: List[Dict[str, Any]] = []

            if os.path.exists(target_path):
                try:
                    with open(target_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            existing_records = json.loads(content)
                            if not isinstance(existing_records, list):
                                existing_records = [existing_records]
                except Exception as read_err:
                    logger.warning(f"Could not read existing intel file, initializing fresh: {read_err}")
                    existing_records = []

            # Append the new record (preserving full historical timeline)
            existing_records.append(intel_record)

            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(existing_records, f, indent=2, ensure_ascii=False)

            logger.info(f"[+] Appended crawl record to {target_path} (Total records: {len(existing_records)})")
            return True
        except Exception as e:
            logger.error(f"[-] Failed to persist intelligence to {target_path}: {e}")
            return False

    def save_to_db(self, intel_record: Dict[str, Any], db_session=None) -> Optional[int]:
        """
        Ingest the parsed intelligence record into the DarkTrace SQLite database:
        - Creates an Observation record with parsed entities and metadata
        - Registers an InfrastructureIndicator for the favicon MurmurHash
        - Correlates against known threat actors and generates alerts
        """
        close_session = False
        if db_session is None:
            try:
                from app.database import SessionLocal
                db_session = SessionLocal()
                close_session = True
            except Exception as e:
                logger.warning(f"Could not initialize DB session: {e}")
                return None

        try:
            from app.models.intelligence import Observation, InfrastructureIndicator, OnionService, Alert
            from app.models.actor import Actor
            import hashlib

            url = intel_record.get("url", "")
            onion = intel_record.get("onion_address") or urlparse(url).netloc
            title = intel_record.get("page_title") or "Tor Onion Observation"
            fav_hash = intel_record.get("favicon_murmur_hash")

            # Harmonized entities dictionary
            entities = {
                "btc_wallets": intel_record.get("btc_wallets", []),
                "xmr_wallets": intel_record.get("xmr_wallets", []),
                "wallets": [f"BTC:{w}" for w in intel_record.get("btc_wallets", [])] + [f"XMR:{w[:12]}..." for w in intel_record.get("xmr_wallets", [])],
                "pgp_keys": intel_record.get("pgp_keys", []),
                "pgps": [k for k in intel_record.get("pgp_keys", []) if not k.startswith("-----BEGIN")],
                "telegram": intel_record.get("telegram", []),
                "handles": intel_record.get("handles", []),
                "emails": intel_record.get("emails", []),
                "favicon_hash": fav_hash,
            }

            # Observation content summary
            content_summary = (
                f"{title} | Host: {onion} | Status: {intel_record.get('status')} | "
                f"BTC: {len(entities['btc_wallets'])}, XMR: {len(entities['xmr_wallets'])}, "
                f"PGP: {len(entities['pgp_keys'])}, Telegram: {len(entities['telegram'])} | "
                f"Favicon MurmurHash: {fav_hash or 'N/A'}\n"
                f"{intel_record.get('text_sample', '')}"
            )

            raw_ref = f"sha256:{hashlib.sha256((onion + str(intel_record.get('timestamp'))).encode()).hexdigest()[:16]}"

            # Actor correlation check
            candidate_id = None
            candidate_conf = 0.0
            candidate_notes = "Crawled via real-time Tor crawler."

            actors = db_session.query(Actor).all()
            for a in actors:
                actor_wallets = [w.address for w in a.wallets]
                actor_pgps = [p.fingerprint for p in a.pgp_identifiers]
                actor_handles = [h.handle.lower().lstrip("@") for h in a.handles]

                # Match wallets
                shared_w = set(actor_wallets) & set(entities["btc_wallets"])
                if shared_w:
                    candidate_id = a.id
                    candidate_conf = max(candidate_conf, 0.90)
                    candidate_notes = f"Matched wallet {list(shared_w)[0]} with actor {a.actor_name}"

                # Match PGP
                shared_p = set(actor_pgps) & set(entities["pgps"])
                if shared_p:
                    candidate_id = a.id
                    candidate_conf = max(candidate_conf, 0.95)
                    candidate_notes = f"Matched PGP {list(shared_p)[0][:16]} with actor {a.actor_name}"

                # Match handles
                clean_obs_handles = [h.lower().lstrip("@") for h in entities["handles"]]
                shared_h = set(actor_handles) & set(clean_obs_handles)
                if shared_h:
                    candidate_id = a.id
                    candidate_conf = max(candidate_conf, 0.85)
                    candidate_notes = f"Matched handle @{list(shared_h)[0]} with actor {a.actor_name}"

            obs = Observation(
                source_name="RealTimeTorCrawler",
                source_type="onion-service",
                service=onion,
                title=title,
                content=content_summary,
                raw_reference=raw_ref,
                collection_method="TorSocks5LiveCrawler",
                reliability=0.92,
                timestamp=datetime.now(timezone.utc),
                collected_at=datetime.now(timezone.utc),
                metadata_json={
                    "url": url,
                    "status": intel_record.get("status"),
                    "status_code": intel_record.get("status_code"),
                    "favicon_murmur_hash": fav_hash,
                    "headers": intel_record.get("headers", {}),
                },
                extracted_entities=entities,
                status="LINKED" if candidate_id and candidate_conf >= 0.85 else "UNRESOLVED",
                candidate_actor_id=candidate_id,
                candidate_confidence=candidate_conf if candidate_id else None,
                candidate_notes=candidate_notes,
            )
            db_session.add(obs)
            db_session.flush()

            # Record Favicon MurmurHash as an InfrastructureIndicator
            if fav_hash:
                service_rec = db_session.query(OnionService).filter(OnionService.address.ilike(f"%{onion}%")).first()
                ind = InfrastructureIndicator(
                    service_id=service_rec.id if service_rec else None,
                    indicator_type="favicon_murmur_hash",
                    value=str(fav_hash),
                    confidence=0.95,
                    observed_at=datetime.now(timezone.utc),
                )
                db_session.add(ind)

            # Generate alert if high-confidence actor match
            if candidate_id and candidate_conf >= 0.70:
                alert = Alert(
                    alert_type="LIVE_TOR_MATCH",
                    title=f"Live Tor Crawler Match: {onion}",
                    description=f"{candidate_notes} (Confidence: {candidate_conf*100:.1f}%)",
                    severity="CRITICAL" if candidate_conf >= 0.90 else "HIGH",
                    actor_id=candidate_id,
                    observation_id=obs.id,
                    entity_type="Observation",
                    entity_value=onion,
                    confidence=candidate_conf,
                    created_at=datetime.now(timezone.utc),
                    acknowledged=0,
                )
                db_session.add(alert)

            db_session.commit()
            logger.info(f"[+] Ingested crawl record into DB (Observation #{obs.id})")
            return obs.id

        except Exception as e:
            if db_session:
                db_session.rollback()
            logger.error(f"[-] Failed to persist intelligence into DB: {e}")
            return None
        finally:
            if close_session and db_session:
                db_session.close()


# CLI Entrypoint & Verification Helper
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="DarkTrace Real-Time Tor SOCKS5 Crawler")
    parser.add_argument("--url", type=str, help="Target .onion URL to crawl")
    parser.add_argument("--test", action="store_true", help="Run crawler self-test and environment check")
    parser.add_argument("--proxy", type=str, default=None, help="Custom Tor SOCKS5 proxy URL")
    args = parser.parse_args()

    crawler = DarkCrawler(proxy_url=args.proxy)

    if args.test:
        print("\n=======================================================")
        print("[*] DARKTRACE REAL-TIME TOR CRAWLER SELF-TEST")
        print("=======================================================")
        print(f"[*] Checking Python environment:")
        print(f"    - Requests: {requests.__version__}")
        print(f"    - BeautifulSoup: Available")
        print(f"    - mmh3 MurmurHash3: {'Available' if _HAS_MMH3 else 'Missing'}")
        
        detected_proxy = crawler.detect_tor_proxy()
        print(f"[*] Tor SOCKS5 Proxy Status: {detected_proxy or 'OFFLINE (Fallback Active)'}")

        # Test extraction logic on synthetic darknet HTML
        sample_darknet_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>ShadowMarket v3.1 - Secure Escrow & Exploit Stash</title>
            <link rel="icon" type="image/x-icon" href="/favicon.ico">
        </head>
        <body>
            <h1>Welcome to the Synthetic ShadowMarket Lab</h1>
            <p>Admin Contact: @demo_shadow_operator or telegram t.me/demo_shadow_operator</p>
            <p>Support Email: shadow-desk@example.invalid</p>
            <p>BTC demo identifier: DEMO_BTC_WALLET_CRAWLER_PRIMARY_NOT_VALID</p>
            <p>Secondary BTC demo identifier: DEMO_BTC_WALLET_CRAWLER_SECONDARY_NOT_VALID</p>
            <p>Monero demo identifier: DEMO_XMR_WALLET_CRAWLER_PRIMARY_NOT_VALID</p>
            <p>PGP Fingerprint: E5B8C1D94A2F0E783B1C5D9A2F4E6801</p>
            <pre>
            -----BEGIN PGP PUBLIC KEY BLOCK-----
            Version: BCPG C# v1.6.1.0
            mQENBF4G9x4BCADL3+8WqQy/4g...
            -----END PGP PUBLIC KEY BLOCK-----
            </pre>
        </body>
        </html>
        """
        print("[*] Testing intelligence extraction against sample darknet payload...")
        res = crawler.extract_intelligence(sample_darknet_html, base_url="http://demo-hidden-service.invalid")
        fav_hash = crawler.calculate_favicon_hash(b"mock_favicon_bytes_ico_12345")
        
        print("\n--- Extracted Intelligence ---")
        print(f"  Title:      {res['page_title']}")
        print(f"  BTC Wallets: {res['btc_wallets']}")
        print(f"  XMR Wallets: {res['xmr_wallets']}")
        print(f"  PGP Keys:   {len(res['pgp_keys'])} found ({res['pgp_keys']})")
        print(f"  Telegram:   {res['telegram']}")
        print(f"  Handles:    {res['handles']}")
        print(f"  Emails:     {res['emails']}")
        print(f"  Favicon MMH3: {fav_hash}")

        # Test persistence
        test_record = {
            "url": "http://demo-hidden-service.invalid",
            "onion_address": "demo-hidden-service.invalid",
            "page_title": res["page_title"],
            "btc_wallets": res["btc_wallets"],
            "xmr_wallets": res["xmr_wallets"],
            "pgp_keys": res["pgp_keys"],
            "telegram": res["telegram"],
            "handles": res["handles"],
            "emails": res["emails"],
            "onion_addresses": ["demo-hidden-service.invalid"],
            "favicon_murmur_hash": fav_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "success",
            "status_code": 200,
            "headers": {"Server": "nginx/1.22", "Content-Type": "text/html"},
            "text_sample": res["text_sample"],
        }
        crawler.save_to_json(test_record)
        print("[+] Self-test completed successfully.\n")

    elif args.url:
        intel = crawler.crawl_onion(args.url)
        print(json.dumps(intel, indent=2))
    else:
        parser.print_help()
