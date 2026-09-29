"""
infra_scan.py — Infrastructure Fingerprinting Service for DarkTrace
Performs SSL/TLS certificate inspection and HTTP banner grabbing on target hosts.
Detects shared infrastructure across threat actors by fingerprinting cert hashes,
server banners, and HTTP headers.

Usage:
    from app.services.infra_scan import InfraScanner
    scanner = InfraScanner()
    result = scanner.scan_target("google.com")
"""

import ssl
import socket
import ipaddress
import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger("InfraScanner")


def validate_public_target(host: str, port: int) -> None:
    """Reject local/private targets before an unauthenticated outbound scan."""
    if port not in (80, 443):
        raise ValueError("Only ports 80 and 443 are allowed")
    if not host or len(host) > 253 or not re.fullmatch(r"[A-Za-z0-9.-]+", host):
        raise ValueError("Invalid host")
    if host.lower() == "localhost" or host.lower().endswith((".local", ".localhost", ".internal")):
        raise ValueError("Local and internal hosts are not allowed")

    try:
        addresses = {item[4][0].split("%", 1)[0] for item in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)}
    except socket.gaierror as exc:
        raise ValueError("Host could not be resolved") from exc
    if not addresses:
        raise ValueError("Host could not be resolved")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise ValueError("Private, loopback, link-local, and reserved targets are not allowed")


class InfraScanner:
    """
    SSL/TLS and HTTP banner fingerprinting for target hosts.
    Works on clearnet hosts. For .onion targets, requires a Tor proxy.
    """

    TIMEOUT = 8.0

    def scan_target(self, host: str, port: int = 443) -> Dict[str, Any]:
        """
        Scan a host for:
        - SSL/TLS certificate details (issuer, subject, SANs, fingerprint, validity)
        - HTTP response banner (server header, title, etc.)
        - Computed infrastructure fingerprint (SHA-256 of cert)

        Returns a structured InfraRecord dict.
        """
        validate_public_target(host, port)
        result: Dict[str, Any] = {
            "host": host,
            "port": port,
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "reachable": False,
            "ssl": None,
            "banner": None,
            "fingerprint": None,
            "indicators": [],
            "error": None,
        }

        # --- SSL scan ---
        try:
            ssl_info = self._grab_ssl_cert(host, port)
            result["ssl"] = ssl_info
            result["reachable"] = True

            if ssl_info.get("fingerprint_sha256"):
                fp = ssl_info["fingerprint_sha256"]
                result["fingerprint"] = fp
                result["indicators"].append({
                    "type": "TLS_CERT_HASH",
                    "value": fp,
                    "confidence": 0.97,
                })
            if ssl_info.get("issuer_org"):
                result["indicators"].append({
                    "type": "SSL_ISSUER",
                    "value": ssl_info["issuer_org"],
                    "confidence": 0.75,
                })
            for san in (ssl_info.get("san_domains") or []):
                result["indicators"].append({
                    "type": "SAN_DOMAIN",
                    "value": san,
                    "confidence": 0.88,
                })
        except Exception as e:
            result["ssl"] = {"error": str(e)}
            logger.debug(f"[InfraScanner] SSL error for {host}: {e}")

        # --- HTTP banner ---
        try:
            banner = self._grab_http_banner(host, port)
            result["banner"] = banner
            result["reachable"] = True

            if banner.get("server"):
                result["indicators"].append({
                    "type": "SERVER_BANNER",
                    "value": banner["server"],
                    "confidence": 0.80,
                })
            if banner.get("title"):
                result["indicators"].append({
                    "type": "PAGE_TITLE",
                    "value": banner["title"],
                    "confidence": 0.70,
                })
        except Exception as e:
            result["banner"] = {"error": str(e)}
            logger.debug(f"[InfraScanner] HTTP banner error for {host}: {e}")

        # Try plain HTTP if HTTPS failed
        if not result["reachable"] and port == 443:
            try:
                banner80 = self._grab_http_banner(host, 80)
                result["banner"] = banner80
                result["reachable"] = True
                if banner80.get("server"):
                    result["indicators"].append({
                        "type": "SERVER_BANNER",
                        "value": banner80["server"],
                        "confidence": 0.75,
                    })
            except Exception:
                pass

        if not result["reachable"]:
            result["error"] = "Host unreachable on ports 443 and 80"

        return result

    def _grab_ssl_cert(self, host: str, port: int = 443) -> Dict[str, Any]:
        """Extract SSL certificate details and compute fingerprint."""
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        with socket.create_connection((host, port), timeout=self.TIMEOUT) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                der_cert = ssock.getpeercert(binary_form=True)
                cert = ssock.getpeercert()
                protocol = ssock.version()

        # Compute fingerprints
        sha256_fp = hashlib.sha256(der_cert).hexdigest()
        sha1_fp = hashlib.sha1(der_cert).hexdigest()

        # Parse subject
        subject = {}
        for item in (cert.get("subject") or []):
            for k, v in item:
                subject[k] = v

        # Parse issuer
        issuer = {}
        for item in (cert.get("issuer") or []):
            for k, v in item:
                issuer[k] = v

        # Parse SANs
        san_domains = []
        for san_type, san_value in (cert.get("subjectAltName") or []):
            if san_type == "DNS":
                san_domains.append(san_value)

        # Parse validity
        not_before = cert.get("notBefore", "")
        not_after = cert.get("notAfter", "")

        return {
            "fingerprint_sha256": sha256_fp,
            "fingerprint_sha1": sha1_fp,
            "subject_cn": subject.get("commonName"),
            "subject_org": subject.get("organizationName"),
            "issuer_cn": issuer.get("commonName"),
            "issuer_org": issuer.get("organizationName"),
            "san_domains": san_domains[:20],  # limit for storage
            "valid_from": not_before,
            "valid_to": not_after,
            "protocol": protocol,
            "serial_number": cert.get("serialNumber"),
        }

    def _grab_http_banner(self, host: str, port: int = 443) -> Dict[str, Any]:
        """Send a minimal HTTP request and extract response headers + page title."""
        try:
            import httpx
            scheme = "https" if port == 443 else "http"
            url = f"{scheme}://{host}:{port}/" if port not in (80, 443) else f"{scheme}://{host}/"
            resp = httpx.get(
                url,
                timeout=self.TIMEOUT,
                follow_redirects=False,
                verify=False,
                headers={"User-Agent": "DarkTrace-InfraScanner/1.0"},
            )
            headers = dict(resp.headers)
            body = resp.text[:2000]

            # Extract page title
            title_match = re.search(r"<title[^>]*>(.*?)</title>", body, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip()[:200] if title_match else None

            return {
                "status_code": resp.status_code,
                "server": headers.get("server"),
                "x_powered_by": headers.get("x-powered-by"),
                "content_type": headers.get("content-type"),
                "title": title,
                "redirect_url": str(resp.url) if resp.url else None,
                "response_headers": {
                    k: v for k, v in headers.items()
                    if k.lower() in ("server", "x-powered-by", "via", "x-frame-options",
                                     "strict-transport-security", "content-security-policy",
                                     "x-generator", "x-drupal-cache", "x-varnish")
                },
            }
        except ImportError:
            # Fallback using raw socket
            return self._raw_http_banner(host, port)

    def _raw_http_banner(self, host: str, port: int) -> Dict[str, Any]:
        """Minimal raw socket HTTP banner grab (fallback without httpx)."""
        with socket.create_connection((host, port), timeout=self.TIMEOUT) as s:
            request = f"GET / HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
            s.sendall(request.encode())
            response = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                response += chunk
                if len(response) > 8192:
                    break

        headers_raw, _, body = response.partition(b"\r\n\r\n")
        headers_text = headers_raw.decode("utf-8", errors="replace")

        server = None
        for line in headers_text.split("\r\n"):
            if line.lower().startswith("server:"):
                server = line.split(":", 1)[1].strip()
                break

        return {"server": server, "raw_headers": headers_text[:500]}

    def check_shared_infrastructure(
        self, fingerprint: str, db_session=None
    ) -> List[Dict[str, Any]]:
        """
        Query the DB for other actors/observations sharing the same cert fingerprint.
        Returns list of actor matches.
        """
        if not db_session:
            return []

        try:
            from app.models.intelligence import Observation
            from app.models.actor import Actor

            # Find observations that have this fingerprint in their metadata
            matching = db_session.query(Observation).filter(
                Observation.metadata_json.contains(fingerprint)
            ).limit(20).all()

            results = []
            seen_actors = set()
            for obs in matching:
                if obs.candidate_actor_id and obs.candidate_actor_id not in seen_actors:
                    actor = db_session.query(Actor).filter(
                        Actor.id == obs.candidate_actor_id
                    ).first()
                    if actor:
                        seen_actors.add(actor.id)
                        results.append({
                            "actor_id": actor.id,
                            "actor_name": actor.actor_name,
                            "confidence": obs.candidate_confidence or 0.0,
                            "shared_via": "TLS_CERT_HASH",
                            "fingerprint": fingerprint,
                        })
            return results
        except Exception as e:
            logger.error(f"[InfraScanner] Shared infra check error: {e}")
            return []


# Module-level singleton
_scanner_instance: Optional[InfraScanner] = None


def get_scanner() -> InfraScanner:
    global _scanner_instance
    if _scanner_instance is None:
        _scanner_instance = InfraScanner()
    return _scanner_instance
