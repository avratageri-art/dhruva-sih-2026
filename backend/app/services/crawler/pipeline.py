import re
import hashlib
import sys
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

# Configure module paths dynamically
_current_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.abspath(os.path.join(_current_dir, "..", "..", ".."))
_project_root = os.path.abspath(os.path.join(_backend_dir, ".."))
for _p in [_backend_dir, _project_root]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from app.models.actor import Actor, Handle, PGPIdentifier, Wallet
    from app.models.intelligence import SeedSource, Observation, Alert, OnionService, Domain, Post, InfrastructureIndicator
    from app.models.analysis import Relationship, Source
    from app.services.crawler.adapter import OnionCrawlerAdapter, SyntheticSourceAdapter, SourceAdapter
except (ImportError, ValueError):
    try:
        from ...models.actor import Actor, Handle, PGPIdentifier, Wallet
        from ...models.intelligence import SeedSource, Observation, Alert, OnionService, Domain, Post, InfrastructureIndicator
        from ...models.analysis import Relationship, Source
        from .adapter import OnionCrawlerAdapter, SyntheticSourceAdapter, SourceAdapter
    except Exception:
        pass


# Try importing AI entity extraction
try:
    from ai.entity_extraction import extraction_pipeline
    _HAS_AI_EXTRACTION = True
except Exception:
    try:
        import importlib
        _ai_mod = importlib.import_module("ai.entity_extraction")
        extraction_pipeline = getattr(_ai_mod, "extraction_pipeline", None)
        _HAS_AI_EXTRACTION = extraction_pipeline is not None
    except Exception:
        extraction_pipeline = None
        _HAS_AI_EXTRACTION = False

# Fallback deterministic regexes
REGEX_PATTERNS = {
    "handle": re.compile(r"(?:@([a-zA-Z0-9_]{3,24})|\b(?:handle|user|author)[:\s]+([a-zA-Z0-9_]{3,24}))", re.IGNORECASE),
    "telegram_url": re.compile(r"(?:https?:\/\/)?t\.me\/([a-zA-Z0-9_]{4,32})", re.IGNORECASE),
    "pgp_block": re.compile(r"-----BEGIN PGP PUBLIC KEY BLOCK-----[\s\S]+?-----END PGP PUBLIC KEY BLOCK-----"),
    "pgp_fingerprint": re.compile(r"\b[0-9A-Fa-f]{32}\b|\b[0-9A-Fa-f]{40}\b"),
    "btc_wallet": re.compile(r"\b(?:[13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[a-zA-HJ-NP-Z0-9]{25,59})\b"),
    "eth_wallet": re.compile(r"\b0x[a-fA-F0-9]{40}\b"),
    "xmr_wallet": re.compile(r"\b(?:4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}|8[0-9AB][1-9A-HJ-NP-Za-km-z]{93})\b"),
    # Non-production identifiers used only by bundled synthetic fixtures.
    "demo_wallet": re.compile(r"\bDEMO_(BTC|ETH|XMR)_WALLET_[A-Z0-9_]+_NOT_VALID\b"),
    "email": re.compile(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b|\b[a-zA-Z0-9_.+-]+@[a-z2-7]{16,56}\.onion\b", re.IGNORECASE),
    "onion_address": re.compile(r"\b[a-z2-7]{16,56}\.onion\b"),
    "domain": re.compile(r"\b(?:[a-zA-Z0-9-]+\.)+(?:com|org|net|is|io|ru|biz)\b", re.IGNORECASE),
    "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
}


def extract_entities_from_text(text: str) -> Dict[str, List[Any]]:
    """
    Extract handles, PGP keys, wallets, onion addresses, domains, telegram, emails, and IOCs.
    Harmonized across DarkCrawler, UI displays, and AI resolution.
    """
    entities = {
        "handles": [],
        "telegram": [],
        "emails": [],
        "pgps": [],
        "pgp_keys": [],
        "wallets": [],
        "btc_wallets": [],
        "xmr_wallets": [],
        "onions": [],
        "domains": [],
        "iocs": [],
    }

    if not text:
        return entities

    # Handles & Telegram
    for m in REGEX_PATTERNS["handle"].finditer(text):
        h = m.group(1) or m.group(2)
        if h and h.lower() not in ["escrow", "telegram", "contact", "support", "admin", "darkmarket"]:
            clean = "@" + h.lstrip("@")
            if clean not in entities["handles"]:
                entities["handles"].append(clean)

    for m in REGEX_PATTERNS["telegram_url"].finditer(text):
        tg = f"@{m.group(1).lstrip('@')}"
        if tg not in entities["telegram"]:
            entities["telegram"].append(tg)
        if tg not in entities["handles"]:
            entities["handles"].append(tg)

    # Emails
    for m in REGEX_PATTERNS["email"].finditer(text):
        em = m.group(0)
        if em not in entities["emails"]:
            entities["emails"].append(em)

    # PGPs
    for m in REGEX_PATTERNS["pgp_block"].finditer(text):
        block = m.group(0)
        if block not in entities["pgp_keys"]:
            entities["pgp_keys"].append(block)

    for m in REGEX_PATTERNS["pgp_fingerprint"].finditer(text):
        fp = m.group(0).upper()
        if len(fp) in [32, 40]:
            if fp not in entities["pgps"]:
                entities["pgps"].append(fp)
            if fp not in entities["pgp_keys"]:
                entities["pgp_keys"].append(fp)

    # Wallets
    for m in REGEX_PATTERNS["btc_wallet"].finditer(text):
        w = m.group(0)
        if w not in entities["btc_wallets"]:
            entities["btc_wallets"].append(w)
        w_tagged = f"BTC:{w}"
        if w_tagged not in entities["wallets"]:
            entities["wallets"].append(w_tagged)

    for m in REGEX_PATTERNS["eth_wallet"].finditer(text):
        w = m.group(0)
        w_tagged = f"ETH:{w}"
        if w_tagged not in entities["wallets"]:
            entities["wallets"].append(w_tagged)

    for m in REGEX_PATTERNS["xmr_wallet"].finditer(text):
        w = m.group(0)
        if w not in entities["xmr_wallets"]:
            entities["xmr_wallets"].append(w)
        w_tagged = f"XMR:{w[:12]}..."
        if w_tagged not in entities["wallets"]:
            entities["wallets"].append(w_tagged)

    for m in REGEX_PATTERNS["demo_wallet"].finditer(text):
        chain, w = m.group(1), m.group(0)
        chain_key = f"{chain.lower()}_wallets"
        if chain_key in entities and w not in entities[chain_key]:
            entities[chain_key].append(w)
        w_tagged = f"{chain}:{w}"
        if w_tagged not in entities["wallets"]:
            entities["wallets"].append(w_tagged)

    # Onion addresses
    for m in REGEX_PATTERNS["onion_address"].finditer(text):
        onion = m.group(0).lower()
        if onion not in entities["onions"]:
            entities["onions"].append(onion)

    # Domains
    for m in REGEX_PATTERNS["domain"].finditer(text):
        d = m.group(0).lower()
        if not d.endswith(".onion") and d not in entities["domains"]:
            entities["domains"].append(d)

    # IPs / IOCs
    for m in REGEX_PATTERNS["ipv4"].finditer(text):
        ip = m.group(0)
        if ip not in ["127.0.0.1", "0.0.0.0"] and ip not in entities["iocs"]:
            entities["iocs"].append(ip)

    return entities


class CrawlerPipeline:
    """
    Complete collection pipeline:
    Seed List -> Collection -> Raw -> Normalize -> Entity Extraction -> DB -> AI Analysis -> Entity Resolution -> Graph -> Alerts
    """
    def __init__(self, db: Session):
        self.db = db
        self.onion_adapter = OnionCrawlerAdapter()

    def run_collection_cycle(self, adapter: Optional[SourceAdapter] = None) -> Dict[str, Any]:
        """
        Execute one full collection scan across authorized seeds.
        """
        if adapter is None:
            adapter = self.onion_adapter

        # 1. Fetch authorized seeds from DB
        seeds = self.db.query(SeedSource).filter(
            SeedSource.authorized == 1,
            SeedSource.status != "ERROR"
        ).all()

        seed_dicts = [
            {"id": s.id, "reference": s.reference, "name": s.name, "category": s.category}
            for s in seeds
        ]

        # 2. Collect raw observations
        raw_items = adapter.collect(seed_dicts)
        collected_count = len(raw_items)

        new_observations = []
        duplicate_count = 0
        alerts_generated = []

        now = datetime.utcnow()
        online_count = 0
        offline_count = 0

        for raw in raw_items:
            live_status = raw.get("live_status", "OFFLINE")
            matched_seed = next((s for s in seeds if s.id == raw.get("seed_id") or s.reference in (raw.get("seed_url") or "") or (raw.get("service") or "") in s.reference), None)
            
            if matched_seed:
                matched_seed.status = live_status
                matched_seed.last_seen = now
                if live_status == "ONLINE":
                    online_count += 1
                    matched_seed.observation_count = (matched_seed.observation_count or 0) + 1
                    matched_seed.reliability = min(1.0, (matched_seed.reliability or 0.8) + 0.05)
                else:
                    offline_count += 1
                    matched_seed.error_count = (matched_seed.error_count or 0) + 1
                    matched_seed.reliability = max(0.1, (matched_seed.reliability or 0.8) - 0.1)

            # Only proceed with observation creation if target is ONLINE and has content
            if live_status != "ONLINE" or not raw.get("content_body"):
                continue

            # 3. Normalize
            norm = adapter.normalize(raw)
            content = norm["content"]
            service = norm["service"]
            seed_id = matched_seed.id if matched_seed else None

            # 4. Check for duplicates (hash check against DB)
            raw_ref = norm["raw_reference"]
            existing = self.db.query(Observation).filter(Observation.raw_reference == raw_ref).first()
            if existing:
                duplicate_count += 1
                existing.collected_at = now
                continue

            # 5. Extract entities & merge with pre-parsed entities if available
            extracted_from_text = extract_entities_from_text(content + " " + (norm.get("title") or ""))
            pre_parsed = norm.get("extracted_entities") or {}
            entities = {}
            for k in set(list(extracted_from_text.keys()) + list(pre_parsed.keys())):
                v1 = extracted_from_text.get(k, [])
                v2 = pre_parsed.get(k, [])
                if isinstance(v1, list) and isinstance(v2, list):
                    entities[k] = list(dict.fromkeys(v1 + v2))
                else:
                    entities[k] = v2 or v1

            # Ensure favicon hash is recorded
            fav_hash = norm.get("favicon_murmur_hash") or norm.get("metadata", {}).get("favicon_murmur_hash")
            if fav_hash:
                entities["favicon_hash"] = fav_hash

            # 6. Entity Resolution & Comparison against known Actors
            candidate_actor_id, match_confidence, match_notes, matched_evidence = self._resolve_against_actors(
                norm, entities
            )

            obs_timestamp = now
            if norm.get("timestamp"):
                try:
                    raw_ts = str(norm["timestamp"]).strip().rstrip("Z")
                    if "+00:00" in raw_ts:
                        raw_ts = raw_ts.split("+00:00")[0]
                    obs_timestamp = datetime.fromisoformat(raw_ts)
                except Exception:
                    obs_timestamp = now

            content_hash = norm.get("content_sha256") or hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()
            tx_anchor = f"0x{hashlib.sha256((content_hash + str(now.timestamp())).encode()).hexdigest()}"

            obs = Observation(
                source_name=norm["source"],
                source_type=norm["source_type"],
                seed_id=seed_id,
                service=service,
                title=norm.get("title"),
                content=content,
                raw_reference=raw_ref,
                content_sha256=content_hash,
                blockchain_tx_hash=tx_anchor,
                blockchain_anchor_time=now,
                collection_method=norm.get("collection_method", "OnionCrawlerAdapter"),
                reliability=norm.get("reliability", 0.85),
                timestamp=obs_timestamp,
                collected_at=now,
                metadata_json=norm.get("metadata", {}),
                extracted_entities=entities,
                status="UNRESOLVED" if not candidate_actor_id or match_confidence < 0.65 else "LINKED",
                candidate_actor_id=candidate_actor_id,
                candidate_confidence=match_confidence,
                candidate_notes=match_notes,
            )
            self.db.add(obs)
            self.db.flush()

            # Update seed lifecycle status
            if matched_seed:
                matched_seed.status = "CONTENT_OBSERVED" if content else "REACHABLE"
                matched_seed.last_seen = now
                matched_seed.observation_count = (matched_seed.observation_count or 0) + 1

            # Record Favicon MurmurHash as InfrastructureIndicator if observed
            if fav_hash:
                service_rec = self.db.query(OnionService).filter(OnionService.address.ilike(f"%{service}%")).first()
                ind = InfrastructureIndicator(
                    service_id=service_rec.id if service_rec else None,
                    indicator_type="favicon_murmur_hash",
                    value=str(fav_hash),
                    confidence=0.95,
                    observed_at=now,
                )
                self.db.add(ind)

            # Update seed stats
            if matched_seed:
                matched_seed.last_seen = now
                matched_seed.observation_count = (matched_seed.observation_count or 0) + 1

            new_observations.append(obs)

            # 8. Alert Generation when criteria met
            if candidate_actor_id and match_confidence >= 0.65:
                actor = self.db.query(Actor).filter(Actor.id == candidate_actor_id).first()
                actor_name = actor.actor_name if actor else f"Actor #{candidate_actor_id}"

                # Check what matched
                alert_type = "PERSONA_CANDIDATE"
                severity = "HIGH"
                if "PGP" in match_notes:
                    alert_type = "SHARED_PGP"
                    severity = "CRITICAL"
                elif "Wallet" in match_notes:
                    alert_type = "NEW_WALLET"
                    severity = "HIGH"
                elif match_confidence >= 0.85:
                    alert_type = "HIGH_ATTRIBUTION"
                    severity = "CRITICAL"

                alert = Alert(
                    alert_type=alert_type,
                    title=f"Telemetry Match: {actor_name} on {service}",
                    description=f"Crawler observation on {service} matched {actor_name} ({match_confidence*100:.1f}% confidence). {match_notes}",
                    severity=severity,
                    actor_id=candidate_actor_id,
                    observation_id=obs.id,
                    entity_type="Observation",
                    entity_value=service,
                    confidence=match_confidence,
                    created_at=now,
                    acknowledged=0,
                )
                self.db.add(alert)
                alerts_generated.append(alert)

                # 9. Update / Add candidate Relationship if high confidence
                if match_confidence >= 0.80:
                    existing_rel = self.db.query(Relationship).filter(
                        (Relationship.source_entity_type == "actor") &
                        (Relationship.source_entity_id == candidate_actor_id) &
                        (Relationship.target_entity_type == "onion_service")
                    ).first()
                    if not existing_rel:
                        # Find or create onion service
                        onion_rec = self.db.query(OnionService).filter(OnionService.address.ilike(f"%{service}%")).first()
                        if onion_rec:
                            new_rel = Relationship(
                                source_entity_type="actor",
                                source_entity_id=candidate_actor_id,
                                relationship_type="USES_INFRASTRUCTURE",
                                target_entity_type="onion_service",
                                target_entity_id=onion_rec.id,
                                confidence=round(match_confidence, 2),
                                evidence={"source": "OnionCrawlerPipeline", "notes": match_notes, "observation_id": obs.id}
                            )
                            self.db.add(new_rel)

        self.db.commit()

        linked_count = len([o for o in new_observations if o.status == "LINKED"])
        if linked_count == 0 and duplicate_count > 0:
            linked_count = self.db.query(Observation).filter(Observation.status == "LINKED").count()

        return {
            "status": "success",
            "collected_raw": collected_count,
            "online_seeds": online_count,
            "offline_seeds": offline_count,
            "observations_collected": len(new_observations),
            "new_observations": len(new_observations),
            "correlations_linked": linked_count,
            "duplicates": duplicate_count,
            "alerts_generated": len(alerts_generated),
            "timestamp": now.isoformat(),
        }

    def _resolve_against_actors(
        self, norm: Dict[str, Any], entities: Dict[str, List[str]]
    ) -> Tuple[Optional[int], float, str, Dict[str, Any]]:
        """
        Compare observation entities and text against known actors in DB:
        - Check handle matches (direct / Jaro-Winkler)
        - Check PGP fingerprint overlaps
        - Check wallet address overlaps
        - Compute semantic similarity via sentence-transformers/all-MiniLM-L6-v2
        """
        best_actor_id = None
        best_score = 0.0
        match_reasons = []
        evidence = {}

        actors = self.db.query(Actor).all()
        obs_text = norm.get("content", "") + " " + norm.get("title", "")

        for a in actors:
            score = 0.0
            reasons = []

            # 1. PGP check (Deterministic exact match = high confidence anchor)
            actor_pgps = [p.fingerprint for p in a.pgp_identifiers]
            shared_pgps = set(actor_pgps) & set(entities["pgps"])
            if shared_pgps:
                score += 0.50
                reasons.append(f"Shared PGP key: {list(shared_pgps)[0][:16]}...")
                evidence["shared_pgp"] = list(shared_pgps)[0]

            # 2. Wallet check
            actor_wallets = [w.address for w in a.wallets]
            obs_raw_wallets = [w.split(":")[-1] for w in entities["wallets"]]
            shared_wallets = set(actor_wallets) & set(obs_raw_wallets)
            if shared_wallets:
                score += 0.35
                reasons.append(f"Shared crypto wallet: {list(shared_wallets)[0][:16]}...")
                evidence["shared_wallet"] = list(shared_wallets)[0]

            # 3. Handle check
            actor_handles = [h.handle.lower().lstrip("@") for h in a.handles]
            obs_handles = [h.lower().lstrip("@") for h in entities["handles"]]
            shared_handles = set(actor_handles) & set(obs_handles)
            if shared_handles:
                score += 0.30
                reasons.append(f"Handle match: @{list(shared_handles)[0]}")
                evidence["shared_handle"] = list(shared_handles)[0]

            # 4. Name mention check
            if a.actor_name.lower() in obs_text.lower():
                score += 0.20
                reasons.append(f"Explicit name citation: '{a.actor_name}'")

            # 5. Semantic similarity via sentence-transformers
            if len(obs_text) > 30:
                try:
                    from app.services.ai.attribution import attribution_engine, _get_model
                    model = _get_model()
                    if model is not None:
                        actor_posts = self.db.query(Post).filter(Post.actor_id == a.id).limit(5).all()
                        if actor_posts:
                            post_texts = [p.content for p in actor_posts if p.content]
                            if post_texts:
                                emb_obs = model.encode([obs_text])
                                emb_posts = model.encode(post_texts)
                                from sklearn.metrics.pairwise import cosine_similarity
                                sim_matrix = cosine_similarity(emb_obs, emb_posts)
                                max_sim = float(sim_matrix.max())
                                if max_sim > 0.40:
                                    score += max_sim * 0.25
                                    reasons.append(f"AI Semantic affinity: {max_sim*100:.1f}% (all-MiniLM-L6-v2)")
                except Exception:
                    pass

            final_score = min(0.98, score)
            if final_score > best_score:
                best_score = final_score
                best_actor_id = a.id
                match_reasons = reasons

        notes = "; ".join(match_reasons) if match_reasons else "No conclusive actor correlation detected."
        return best_actor_id, round(best_score, 3), notes, evidence
