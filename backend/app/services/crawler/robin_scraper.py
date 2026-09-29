"""Robin-inspired OSINT search and entity-extraction pipeline.

No operational search endpoint is built in. Analysts may supply explicitly
authorized HTTP(S) ``.onion`` search endpoints through
``ROBIN_SEARCH_ENGINES_JSON``. A fresh local setup therefore performs no Robin
network activity and can use the synthetic seed job for demonstrations.
"""

import os
import json
import re
import time
import random
import hashlib
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

logger = logging.getLogger("RobinScraper")

# ─────────────────────────────────────────────────────────────────────────────
# Analyst-configured search engines
# ─────────────────────────────────────────────────────────────────────────────

def _load_authorized_search_engines() -> List[Dict[str, str]]:
    try:
        from app.config import settings
        raw = settings.ROBIN_SEARCH_ENGINES_JSON
        configured = json.loads(raw)
    except Exception as exc:
        logger.warning(f"[Robin] Invalid ROBIN_SEARCH_ENGINES_JSON: {exc}")
        return []

    if not isinstance(configured, list):
        logger.warning("[Robin] ROBIN_SEARCH_ENGINES_JSON must be a JSON array")
        return []

    engines: List[Dict[str, str]] = []
    for item in configured:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()[:80]
        url = str(item.get("url", "")).strip()
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        if name and parsed.scheme in ("http", "https") and hostname.endswith(".onion") and "{query}" in url:
            engines.append({"name": name, "url": url})
        else:
            logger.warning("[Robin] Ignored an invalid or non-onion configured search endpoint")
    return engines


ONION_SEARCH_ENGINES = _load_authorized_search_engines()
CLEARNET_SEARCH_ENGINES: List[Dict[str, str]] = []

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.7; rv:137.0) Gecko/20100101 Firefox/137.0",
]

ONION_URL_RE = re.compile(r'https?://[a-z2-7]{16,56}\.onion[^\s"\'<>]*', re.IGNORECASE)

# ─────────────────────────────────────────────────────────────────────────────
# Entity Extraction Patterns
# ─────────────────────────────────────────────────────────────────────────────

BTC_PATTERN    = re.compile(r'\b(bc1[a-zA-Z0-9]{25,87}|[13][a-zA-Z0-9]{25,34})\b')
XMR_PATTERN    = re.compile(r'\b4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}\b')
PGP_PATTERN    = re.compile(r'-----BEGIN PGP PUBLIC KEY BLOCK-----.*?-----END PGP PUBLIC KEY BLOCK-----', re.DOTALL)
PGP_FP_PATTERN = re.compile(r'\b[0-9A-Fa-f]{40}\b')
EMAIL_PATTERN  = re.compile(r'\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b')
ONION_PATTERN  = re.compile(r'(?:https?://)?([a-z2-7]{16,56}\.onion)(?:[/\w.?=&%-]*)?', re.IGNORECASE)
TG_PATTERN     = re.compile(r'(?:t\.me|telegram\.me)/([a-zA-Z0-9_]{5,})')
HANDLE_PATTERN = re.compile(r'(?:^|\s)@([a-zA-Z0-9_]{3,30})')

# ─────────────────────────────────────────────────────────────────────────────
# In-memory job tracking (real-time polling)
# ─────────────────────────────────────────────────────────────────────────────

_ROBIN_JOBS: Dict[str, Any] = {}
_ROBIN_LOCK = threading.Lock()
_LATEST_RESULTS: List[Dict[str, Any]] = []
_LATEST_RESULTS_LOCK = threading.Lock()


def _find_jobs_file() -> str:
    candidates = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data", "robin_jobs.json")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "robin_jobs.json")),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[0]


def _save_jobs_to_disk():
    try:
        fpath = _find_jobs_file()
        os.makedirs(os.path.dirname(fpath), exist_ok=True)
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(_ROBIN_JOBS, f, indent=2)
    except Exception as e:
        logger.warning(f"[Robin] Could not save jobs to disk: {e}")


def _load_jobs_from_disk():
    try:
        fpath = _find_jobs_file()
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    _ROBIN_JOBS.update(data)
                    logger.info(f"[Robin] Restored {len(data)} jobs from {fpath}")
    except Exception as e:
        logger.warning(f"[Robin] Could not load jobs from disk: {e}")


_load_jobs_from_disk()


def get_all_jobs() -> List[Dict[str, Any]]:
    with _ROBIN_LOCK:
        return sorted(_ROBIN_JOBS.values(), key=lambda j: j.get("started_at", ""), reverse=True)


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    with _ROBIN_LOCK:
        job = _ROBIN_JOBS.get(job_id)
        if not job:
            return None
        # Enrich scraped_pages with text and entities from observations if missing
        obs_by_ref = {o.get("raw_reference"): o for o in job.get("observations", [])}
        for p in job.get("scraped_pages", []):
            if not p.get("text") and p.get("url") in obs_by_ref:
                obs = obs_by_ref[p["url"]]
                p["text"] = obs.get("content", "")
                p["entities"] = obs.get("extracted_entities", {})
        return job


def get_latest_results(limit: int = 50) -> List[Dict[str, Any]]:
    with _LATEST_RESULTS_LOCK:
        return _LATEST_RESULTS[-limit:]


def get_robin_status() -> Dict[str, Any]:
    """Return overall Robin scraper status."""
    with _ROBIN_LOCK:
        jobs = list(_ROBIN_JOBS.values())
    running = [j for j in jobs if j.get("status") in ("queued", "searching", "scraping")]
    done = [j for j in jobs if j.get("status") == "done"]
    errors = [j for j in jobs if j.get("status") == "error"]
    tor_up = check_tor_available()
    engines = ONION_SEARCH_ENGINES if tor_up else []
    return {
        "tor_available": tor_up,
        "mode": "TOR" if tor_up and engines else "UNCONFIGURED",
        "total_engines": len(ONION_SEARCH_ENGINES),
        "active_engines": engines,
        "total_jobs": len(jobs),
        "running_jobs": len(running),
        "completed_jobs": len(done),
        "failed_jobs": len(errors),
        "recent_jobs": jobs[:10],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Session Builders
# ─────────────────────────────────────────────────────────────────────────────

def _build_session(use_tor: bool = False, timeout: int = 20):
    try:
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
    except ImportError:
        raise RuntimeError("requests not installed. Run: pip install requests")

    session = requests.Session()
    retry = Retry(total=2, read=2, connect=2, backoff_factor=0.5,
                  status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,*/*",
        "Accept-Language": "en-US,en;q=0.9",
    })
    if use_tor:
        try:
            from app.config import settings
            proxy_url = settings.TOR_SOCKS_PROXY
        except Exception:
            proxy_url = "socks5h://127.0.0.1:9050"
        session.proxies = {
            "http": proxy_url,
            "https": proxy_url,
        }
    return session


def check_tor_available() -> bool:
    try:
        from app.config import settings
        host = settings.TOR_SOCKS_HOST
        port = settings.TOR_SOCKS_PORT
    except Exception:
        host, port = "127.0.0.1", 9050
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Robin-style Dark Web Search
# ─────────────────────────────────────────────────────────────────────────────

def _extract_links_from_html(html: str, source_engine: str, engine_url: str = "") -> List[Dict[str, Any]]:
    """Extract real onion result links from search engine HTML, filtering out self/navigation links."""
    engine_host = urlparse(engine_url).netloc.lower() if engine_url else ""
    results = []
    seen = set()
    bad_words = {"child", "cp", "rape", "pedophil"}

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")

        for a in soup.find_all("a", href=True):
            href = a.get("href", "").strip()
            if "dom=" in href or "url=" in href:
                m = re.search(r'(?:dom|url)=([a-z2-7]{16,56}\.onion)', href, re.I)
                if m:
                    href = f"http://{m.group(1)}/"

            if ".onion" not in href:
                continue

            parsed = urlparse(href if href.startswith("http") else f"http://{href}")
            link_host = parsed.netloc.lower()

            if not link_host or link_host == engine_host:
                continue

            full_url = f"{parsed.scheme or 'http'}://{parsed.netloc}{parsed.path or '/'}"
            if parsed.query and "q=" not in parsed.query and "search=" not in parsed.query:
                full_url += f"?{parsed.query}"

            title = a.get_text(strip=True) or link_host
            if any(bw in title.lower() for bw in bad_words):
                continue

            if link_host not in seen:
                seen.add(link_host)
                parent = a.parent
                snippet = parent.get_text(strip=True)[:250] if parent else ""
                results.append({
                    "link": full_url,
                    "title": title[:120],
                    "snippet": snippet,
                    "engine": source_engine,
                })
        return results
    except Exception as e:
        logger.warning(f"[Robin] Extraction error: {e}")
        return []


def search_dark_web(query: str, num_engines: int = 3, use_tor: bool = True, timeout: int = 25) -> List[Dict[str, Any]]:
    """
    Query dark web search engines in real time.
    Requires Tor SOCKS5 (127.0.0.1:9050). No fake fallback data is returned.
    """
    if not ONION_SEARCH_ENGINES:
        raise RuntimeError(
            "No authorized Robin search engines are configured. "
            "Use the synthetic demo seed or set ROBIN_SEARCH_ENGINES_JSON to approved research sources."
        )

    tor_up = check_tor_available() if use_tor else False
    if not tor_up:
        raise RuntimeError("Tor SOCKS5 daemon is offline on 127.0.0.1:9050. Start Tor to fetch real-time Darknet data.")

    logger.info("[Robin] Tor active — querying live .onion search engines")
    # Prioritize top live responsive engines first
    selected_engines = ONION_SEARCH_ENGINES[:max(num_engines, 1)]
    session = _build_session(use_tor=True, timeout=timeout)

    all_results: List[Dict[str, Any]] = []
    seen_links: set = set()

    def _search_one(engine: Dict[str, str]) -> List[Dict[str, Any]]:
        url = engine["url"].format(query=query.replace(" ", "+"))
        try:
            resp = session.get(url, timeout=timeout)
            if resp.status_code == 200:
                links = _extract_links_from_html(resp.text, engine["name"], engine["url"])
                logger.info(f"[Robin] {engine['name']}: {len(links)} results found")
                return links
        except Exception as e:
            logger.warning(f"[Robin] {engine['name']} query error: {e}")
        return []

    with ThreadPoolExecutor(max_workers=min(len(selected_engines), 4)) as pool:
        futures = {pool.submit(_search_one, eng): eng for eng in selected_engines}
        try:
            for future in as_completed(futures, timeout=timeout + 5):
                try:
                    for item in future.result():
                        if item["link"] not in seen_links:
                            seen_links.add(item["link"])
                            all_results.append(item)
                except Exception as ex:
                    logger.debug(f"[Robin] Engine future error: {ex}")
        except TimeoutError:
            logger.info(f"[Robin] Search completed with {len(all_results)} real-time results (timeout reached on slower engines)")
        except Exception as e:
            logger.warning(f"[Robin] Search exception caught: {e}")

    return all_results


# ─────────────────────────────────────────────────────────────────────────────
# Robin-style Page Scraper
# ─────────────────────────────────────────────────────────────────────────────

MAX_DOWNLOAD_BYTES = 500_000
MAX_TEXT_CHARS = 20_000


def scrape_onion_page(url: str, use_tor: bool = True, timeout: int = 30) -> Dict[str, Any]:
    """Scrape an onion/clearnet page and extract threat intel entities."""
    result = {
        "url": url,
        "title": "",
        "text": "",
        "status": "error",
        "error": None,
        "entities": {},
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }
    tor_up = check_tor_available() if use_tor else False
    session = _build_session(use_tor=tor_up, timeout=timeout)
    try:
        resp = session.get(url, timeout=timeout, stream=True)
        content_type = resp.headers.get("content-type", "")
        if not any(ct in content_type for ct in ("text/html", "text/plain", "application/xhtml")):
            result["error"] = f"Unsupported content-type: {content_type}"
            return result
        raw = b""
        for chunk in resp.iter_content(8192):
            raw += chunk
            if len(raw) >= MAX_DOWNLOAD_BYTES:
                break
        html = raw.decode("utf-8", errors="replace")
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            title_tag = soup.find("title")
            result["title"] = title_tag.get_text(strip=True) if title_tag else ""
            result["text"] = soup.get_text(separator=" ", strip=True)[:MAX_TEXT_CHARS]
        except Exception:
            result["text"] = html[:MAX_TEXT_CHARS]
        result["entities"] = extract_entities(result["text"] + " " + html)
        result["status"] = "success"
    except Exception as e:
        result["error"] = str(e)[:200]
        logger.warning(f"[Robin] Scrape failed {url}: {e}")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Entity Extraction
# ─────────────────────────────────────────────────────────────────────────────

def extract_entities(text: str) -> Dict[str, Any]:
    """Extract BTC, XMR, PGP, emails, onions, Telegram handles from text."""
    entities: Dict[str, Any] = {}
    btc = list(set(BTC_PATTERN.findall(text)))
    if btc:
        entities["btc_wallets"] = btc[:20]
    xmr = list(set(XMR_PATTERN.findall(text)))
    if xmr:
        entities["xmr_wallets"] = xmr[:10]
    pgp_full = PGP_PATTERN.findall(text)
    pgp_fp = [fp for fp in PGP_FP_PATTERN.findall(text) if len(fp) == 40]
    if pgp_full or pgp_fp:
        entities["pgp_keys"] = pgp_full[:5]
        entities["pgp_fingerprints"] = list(set(pgp_fp))[:20]
    emails = [e for e in set(EMAIL_PATTERN.findall(text))
              if not e.endswith((".png", ".jpg", ".css", ".js"))]
    if emails:
        entities["emails"] = emails[:20]
    onions = list(set(m.group(0) for m in ONION_PATTERN.finditer(text)))
    if onions:
        entities["onion_addresses"] = onions[:20]
    tg = list(set(TG_PATTERN.findall(text)))
    if tg:
        entities["telegram"] = [f"@{h}" for h in tg[:10]]
    handles = [h for h in set(HANDLE_PATTERN.findall(text)) if len(h) >= 3]
    if handles:
        entities["handles"] = handles[:20]
    return entities


# ─────────────────────────────────────────────────────────────────────────────
# Full Robin Pipeline
# ─────────────────────────────────────────────────────────────────────────────

def run_robin_search(
    query: str,
    num_engines: int = 3,
    max_pages_to_scrape: int = 5,
    use_tor: bool = True,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Full Robin pipeline: Search → Scrape → Extract → Return results."""
    if job_id is None:
        job_id = hashlib.md5(f"{query}{time.time()}".encode()).hexdigest()[:12]

    started_at = datetime.now(timezone.utc)
    with _ROBIN_LOCK:
        _ROBIN_JOBS[job_id] = {
            "job_id": job_id,
            "query": query,
            "status": "searching",
            "started_at": started_at.isoformat(),
            "finished_at": None,
            "tor_used": False,
            "search_results": [],
            "scraped_pages": [],
            "all_entities": {},
            "error": None,
        }

    logger.info(f"[Robin] Job {job_id}: searching '{query}'")

    try:
        tor_up = check_tor_available() if use_tor else False
        with _ROBIN_LOCK:
            _ROBIN_JOBS[job_id]["tor_used"] = tor_up

        search_results = search_dark_web(query=query, num_engines=num_engines, use_tor=use_tor)
        with _ROBIN_LOCK:
            _ROBIN_JOBS[job_id]["status"] = "scraping"
            _ROBIN_JOBS[job_id]["search_results"] = search_results

        logger.info(f"[Robin] Job {job_id}: {len(search_results)} URLs found, scraping {max_pages_to_scrape}")

        scraped_pages = []
        target_items = search_results[:max_pages_to_scrape]

        def _scrape_worker(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            url = item.get("link", "")
            if not url:
                return None
            try:
                page_data = scrape_onion_page(url, use_tor=use_tor, timeout=18)
                page_data["search_title"] = item.get("title", "")
                page_data["search_snippet"] = item.get("snippet", "")
                page_data["engine"] = item.get("engine", "")
                return page_data
            except Exception as pe:
                return {
                    "url": url, "title": item.get("title", ""), "text": "",
                    "status": "error", "error": str(pe)[:200], "entities": {},
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                    "search_title": item.get("title", ""), "search_snippet": item.get("snippet", ""),
                    "engine": item.get("engine", "")
                }

        with ThreadPoolExecutor(max_workers=min(max(len(target_items), 1), 5)) as scrape_pool:
            scrape_futures = [scrape_pool.submit(_scrape_worker, it) for it in target_items]
            for fut in scrape_futures:
                try:
                    res = fut.result(timeout=22)
                    if res:
                        scraped_pages.append(res)
                except Exception as fe:
                    logger.debug(f"[Robin] Page scrape future error: {fe}")

        # Aggregate entities
        agg: Dict[str, set] = {k: set() for k in
            ["btc_wallets", "xmr_wallets", "pgp_fingerprints", "emails",
             "onion_addresses", "telegram", "handles"]}
        for page in scraped_pages:
            for k in agg:
                for v in page.get("entities", {}).get(k, []):
                    agg[k].add(str(v))
        agg_lists = {k: list(v) for k, v in agg.items() if v}

        # Build observation records
        obs_records = []
        for page in scraped_pages:
            if page.get("status") != "success":
                continue
            obs_records.append({
                "source": "RobinDarkWebSearch",
                "source_type": "robin-osint",
                "service": urlparse(page["url"]).netloc,
                "title": page.get("title") or page.get("search_title", ""),
                "content": page.get("text", "")[:2000],
                "raw_reference": page["url"],
                "reliability": 0.70,
                "collection_method": "RobinSearchScrape",
                "timestamp": page["scraped_at"],
                "extracted_entities": page.get("entities", {}),
                "query": query,
                "engine": page.get("engine", ""),
                "tor_used": tor_up,
            })

        finished_at = datetime.now(timezone.utc)
        elapsed = (finished_at - started_at).total_seconds()

        result = {
            "job_id": job_id,
            "query": query,
            "status": "done",
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "elapsed_seconds": round(elapsed, 1),
            "tor_used": tor_up,
            "search_results_count": len(search_results),
            "pages_scraped": len(scraped_pages),
            "observations": obs_records,
            "all_entities": agg_lists,
            "search_results": search_results,
            "scraped_pages": [
                {
                    "url": p["url"],
                    "title": p.get("title", ""),
                    "status": p.get("status", ""),
                    "entity_count": sum(len(v) for v in p.get("entities", {}).values()),
                    "engine": p.get("engine", ""),
                    "text": p.get("text", "")[:4000],
                    "entities": p.get("entities", {}),
                    "scraped_at": p.get("scraped_at", ""),
                    "status_code": p.get("status_code", 200),
                    "error": p.get("error", ""),
                }
                for p in scraped_pages
            ],
            "error": None,
        }

        with _ROBIN_LOCK:
            _ROBIN_JOBS[job_id].update(result)
            _save_jobs_to_disk()

        with _LATEST_RESULTS_LOCK:
            _LATEST_RESULTS.extend(obs_records)
            del _LATEST_RESULTS[:-500]

        logger.info(
            f"[Robin] Job {job_id}: done in {elapsed:.1f}s — "
            f"{len(search_results)} links, {len(scraped_pages)} scraped, "
            f"{len(obs_records)} observations"
        )
        return result

    except Exception as e:
        logger.error(f"[Robin] Job {job_id} error: {e}", exc_info=True)
        with _ROBIN_LOCK:
            _ROBIN_JOBS[job_id].update({
                "status": "error",
                "error": str(e),
                "finished_at": datetime.now(timezone.utc).isoformat(),
            })
            _save_jobs_to_disk()
        return {"job_id": job_id, "status": "error", "error": str(e)}


def run_robin_search_async(
    query: str,
    num_engines: int = 3,
    max_pages_to_scrape: int = 5,
    use_tor: bool = True,
) -> str:
    """Launch Robin search in background thread, return job_id immediately."""
    job_id = hashlib.md5(f"{query}{time.time()}".encode()).hexdigest()[:12]
    with _ROBIN_LOCK:
        _ROBIN_JOBS[job_id] = {
            "job_id": job_id,
            "query": query,
            "status": "queued",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
            "tor_used": False,
            "search_results": [],
            "scraped_pages": [],
            "all_entities": {},
            "error": None,
        }
    thread = threading.Thread(
        target=run_robin_search,
        kwargs={
            "query": query,
            "num_engines": num_engines,
            "max_pages_to_scrape": max_pages_to_scrape,
            "use_tor": use_tor,
            "job_id": job_id,
        },
        daemon=True,
        name=f"robin-{job_id}",
    )
    thread.start()
    logger.info(f"[Robin] Launched async job {job_id} for query: '{query}'")
    return job_id


def ingest_robin_results_to_db(db_session, job_id: str) -> Dict[str, Any]:
    """Ingest completed Robin job observations into DarkTrace database."""
    from app.models.intelligence import Observation
    from app.services.crawler.pipeline import extract_entities_from_text, CrawlerPipeline

    job = get_job(job_id)
    if not job:
        return {"error": f"Job {job_id} not found"}
    if job.get("status") != "done":
        return {"error": f"Job {job_id} not complete (status: {job.get('status')})"}

    pipeline = CrawlerPipeline(db_session)
    now = datetime.now(timezone.utc)
    created = 0
    skipped = 0

    from app.services.crawler.normalizer import normalize_observation, compute_sha256
    from app.models.intelligence import Alert, OnionService
    from app.models.analysis import Relationship
    from app.models.actor import Actor

    for rec in job.get("observations", []):
        norm = normalize_observation(rec, collector="RobinDarkWebSearch")
        raw_ref = norm["raw_content_reference"]
        content = norm["content"]
        content_hash = norm["content_sha256"]

        existing = db_session.query(Observation).filter(Observation.raw_reference == raw_ref).first()
        if existing:
            skipped += 1
            continue

        entities = norm["extracted_entities"]
        try:
            candidate_actor_id, conf, notes, _ = pipeline._resolve_against_actors(norm, entities)
        except Exception:
            candidate_actor_id, conf, notes = None, 0.0, ""

        tx_anchor = f"0x{hashlib.sha256((content_hash + str(now.timestamp())).encode()).hexdigest()}"

        obs = Observation(
            source_name="RobinDarkWebSearch",
            source_type="robin-osint",
            service=norm.get("service", ""),
            title=norm.get("title", ""),
            content=content,
            raw_reference=raw_ref,
            content_sha256=content_hash,
            blockchain_tx_hash=tx_anchor,
            blockchain_anchor_time=now,
            collection_method="RobinSearchScrape",
            reliability=norm.get("reliability", 0.70),
            timestamp=now,
            collected_at=now,
            metadata_json=norm.get("provenance", {}),
            extracted_entities=entities,
            status="UNRESOLVED" if not candidate_actor_id or conf < 0.65 else "LINKED",
            candidate_actor_id=candidate_actor_id,
            candidate_confidence=conf,
            candidate_notes=notes,
        )
        db_session.add(obs)
        db_session.flush()

        # If candidate actor matched with high confidence, dispatch Alert
        if candidate_actor_id and conf >= 0.65:
            actor = db_session.query(Actor).filter(Actor.id == candidate_actor_id).first()
            actor_name = actor.actor_name if actor else f"Actor #{candidate_actor_id}"
            alert = Alert(
                alert_type="ROBIN_OSINT_MATCH",
                title=f"Darknet Correlation: {actor_name} on {norm.get('service')}",
                description=f"Robin dark web search observation matched {actor_name} ({conf*100:.1f}% confidence). {notes}",
                severity="CRITICAL" if conf >= 0.85 else "HIGH",
                actor_id=candidate_actor_id,
                observation_id=obs.id,
                entity_type="Observation",
                entity_value=norm.get("service"),
                confidence=conf,
                created_at=now,
                acknowledged=0,
            )
            db_session.add(alert)

            # Auto-create relationship if high confidence
            if conf >= 0.80:
                onion_rec = db_session.query(OnionService).filter(OnionService.address.ilike(f"%{norm.get('service')}%")).first()
                if onion_rec:
                    new_rel = Relationship(
                        source_entity_type="actor",
                        source_entity_id=candidate_actor_id,
                        relationship_type="USES_INFRASTRUCTURE",
                        target_entity_type="onion_service",
                        target_entity_id=onion_rec.id,
                        confidence=round(conf, 2),
                        evidence={"source": "RobinDarkWebSearch", "notes": notes, "observation_id": obs.id}
                    )
                    db_session.add(new_rel)

        created += 1

    db_session.commit()
    return {
        "status": "ingested",
        "job_id": job_id,
        "query": job.get("query", ""),
        "observations_created": created,
        "duplicates_skipped": skipped,
    }
