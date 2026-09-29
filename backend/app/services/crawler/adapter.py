from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib
import random

class SourceAdapter(ABC):
    """
    Standard interface for all DarkTrace intelligence collection adapters.
    Any new crawler or telemetry source must implement this contract.
    """
    def __init__(self, name: str, source_type: str):
        self.name = name
        self.source_type = source_type

    @abstractmethod
    def collect(self, seeds: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Collect raw observations from the source/seeds.
        Returns a list of raw observation payloads.
        """
        pass

    @abstractmethod
    def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a raw observation dictionary into DarkTrace's normalized observation schema:
        {
            "source": str,
            "source_type": str,
            "timestamp": isoformat str,
            "service": str,
            "title": str,
            "content": str,
            "metadata": dict,
            "reference": str,
            "reliability": float,
            "collection_method": str,
            "raw_reference": str
        }
        """
        pass


import logging
logger = logging.getLogger("OnionCrawlerAdapter")

try:
    from app.services.crawler.dark_crawler import DarkCrawler
    _HAS_DARK_CRAWLER = True
except Exception:
    _HAS_DARK_CRAWLER = False


class OnionCrawlerAdapter(SourceAdapter):
    """
    Onion-Service Crawler Adapter with DarkCrawler Tor SOCKS5 Integration.
    Routes requests through local Tor proxy when online; gracefully falls back
    to controlled demonstration pool when Tor daemon is offline.
    """
    def __init__(self, name: str = "Tor Onion Crawler"):
        super().__init__(name=name, source_type="onion-service")
        self.dark_crawler = DarkCrawler() if _HAS_DARK_CRAWLER else None

    def collect(self, seeds: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        raw_items = []
        now = datetime.utcnow()

        # Check if Tor daemon is live or can be auto-started
        tor_proxy = None
        if self.dark_crawler:
            tor_proxy = self.dark_crawler.ensure_tor_daemon() if hasattr(self.dark_crawler, "ensure_tor_daemon") else self.dark_crawler.detect_tor_proxy()

        if seeds and len(seeds) > 0:
            import concurrent.futures

            def _crawl_single(s):
                ref = s.get("reference", "")
                name = s.get("name", "Unknown Service")
                seed_id = s.get("id")
                is_onion = ".onion" in ref

                clean_url = ref.replace("tor://", "http://")
                if not clean_url.startswith("http"):
                    clean_url = f"http://{clean_url}"

                onion_host = clean_url.split("://")[-1].split("/")[0].split(":")[0]

                if tor_proxy:
                    try:
                        logger.info(f"[+] Tor crawling seed {name}: {clean_url}")
                        intel = self.dark_crawler.crawl_onion(clean_url, save_records=True)
                        if intel.get("status") == "success" and (intel.get("status_code", 0) >= 200 and intel.get("status_code", 0) < 400):
                            return {
                                "seed_id": seed_id,
                                "seed_url": intel.get("url", clean_url),
                                "service": intel.get("onion_address", onion_host),
                                "page_title": intel.get("page_title") or f"{name} - Live Onion Service",
                                "content_body": (intel.get("text_sample") or "") + f" BTC: {intel.get('btc_wallets', [])} XMR: {intel.get('xmr_wallets', [])} PGP: {intel.get('pgp_keys', [])} Telegram: {intel.get('telegram', [])}",
                                "headers": intel.get("headers", {}),
                                "status_code": intel.get("status_code", 200),
                                "tls_cipher": "Tor SOCKS5 Circuit",
                                "favicon_murmur_hash": intel.get("favicon_murmur_hash"),
                                "live_status": "ONLINE",
                                "extracted_entities": {
                                    "btc_wallets": intel.get("btc_wallets", []),
                                    "xmr_wallets": intel.get("xmr_wallets", []),
                                    "wallets": [f"BTC:{w}" for w in intel.get("btc_wallets", [])] + [f"XMR:{w[:12]}..." for w in intel.get("xmr_wallets", [])],
                                    "pgp_keys": intel.get("pgp_keys", []),
                                    "pgps": [k for k in intel.get("pgp_keys", []) if not str(k).startswith("-----BEGIN")],
                                    "handles": intel.get("handles", []),
                                    "telegram": intel.get("telegram", []),
                                    "emails": intel.get("emails", []),
                                    "favicon_hash": intel.get("favicon_murmur_hash"),
                                },
                                "timestamp": intel.get("timestamp") or now.isoformat(),
                            }
                        else:
                            return {
                                "seed_id": seed_id,
                                "seed_url": clean_url,
                                "service": onion_host,
                                "page_title": f"{name} - Unreachable ({onion_host})",
                                "content_body": "",
                                "headers": {},
                                "status_code": intel.get("status_code", 0),
                                "tls_cipher": "Tor SOCKS5 Circuit (Unreachable)",
                                "live_status": "OFFLINE",
                                "error": intel.get("error") or "Connection timed out over Tor circuit",
                                "extracted_entities": {},
                                "timestamp": now.isoformat(),
                            }
                    except Exception as e:
                        logger.warning(f"Live crawl error for {clean_url}: {e}")
                        return {
                            "seed_id": seed_id,
                            "seed_url": clean_url,
                            "service": onion_host,
                            "page_title": f"{name} - Offline",
                            "content_body": "",
                            "headers": {},
                            "status_code": 0,
                            "tls_cipher": "Tor SOCKS5 Circuit (Failed)",
                            "live_status": "OFFLINE",
                            "error": str(e),
                            "extracted_entities": {},
                            "timestamp": now.isoformat(),
                        }
                else:
                    return {
                        "seed_id": seed_id,
                        "seed_url": clean_url,
                        "service": onion_host,
                        "page_title": f"{name} - Tor Daemon Offline",
                        "content_body": "",
                        "headers": {},
                        "status_code": 0,
                        "tls_cipher": "Offline",
                        "live_status": "OFFLINE",
                        "error": "Tor daemon not listening on 127.0.0.1:9050",
                        "extracted_entities": {},
                        "timestamp": now.isoformat(),
                    }

            with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(seeds), 6)) as executor:
                raw_items = list(executor.map(_crawl_single, seeds))
        else:
            raw_items = []

        return raw_items

    def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert crawler output into normalized DarkTrace schema."""
        now = datetime.utcnow().isoformat()
        service = raw_data.get("service") or raw_data.get("seed_url", "unknown.onion")
        title = raw_data.get("page_title") or "Hidden Service Observation"
        content = raw_data.get("content_body") or ""
        timestamp = raw_data.get("timestamp") or now
        fav_hash = raw_data.get("favicon_murmur_hash")

        metadata = {
            "headers": raw_data.get("headers", {}),
            "status_code": raw_data.get("status_code", 200),
            "tls_cipher": raw_data.get("tls_cipher", "N/A"),
            "favicon_murmur_hash": fav_hash,
            "hash": hashlib.sha256((service + content).encode("utf-8")).hexdigest()[:16],
            "controlled_environment": False,
        }

        return {
            "source": self.name,
            "source_type": self.source_type,
            "timestamp": timestamp,
            "service": service,
            "title": title,
            "content": content,
            "metadata": metadata,
            "reference": raw_data.get("seed_url", f"tor://{service}"),
            "reliability": 0.92 if fav_hash else 0.88,
            "collection_method": "TorSocks5LiveCrawler",
            "raw_reference": f"sha256:{metadata['hash']}",
            "extracted_entities": raw_data.get("extracted_entities"),
            "favicon_murmur_hash": fav_hash,
        }


class SyntheticSourceAdapter(SourceAdapter):
    """
    Deprecated: Retained only for interface backward compatibility; returns no synthetic records.
    """
    def __init__(self, name: str = "Decommissioned Synthetic Telemetry"):
        super().__init__(name=name, source_type="deprecated-source")

    def collect(self, seeds: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        return []

    def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        return {}
