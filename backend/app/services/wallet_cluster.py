"""
wallet_cluster.py — Bitcoin Wallet Clustering for DarkTrace
Implements the common-input-ownership heuristic:
  "Wallets that appear together in the same observations or transactions
   are likely controlled by the same actor."

Also optionally queries the Blockchain.info public API for on-chain co-occurrence.
"""

import hashlib
import logging
from collections import defaultdict
from typing import Dict, Any, List, Optional, Set, Tuple

logger = logging.getLogger("WalletCluster")

# BTC address regex (P2PKH/P2SH/bech32)
import re
BTC_PATTERN = re.compile(r'\b(bc1[a-zA-HJ-NP-Z0-9]{25,39}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b')
XMR_PATTERN = re.compile(r'\b4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}\b')


def extract_wallets_from_text(text: str) -> Dict[str, List[str]]:
    """Extract BTC and XMR wallet addresses from text."""
    btc = list(set(BTC_PATTERN.findall(text)))
    xmr = list(set(XMR_PATTERN.findall(text)))
    return {"btc": btc, "xmr": xmr}


def cluster_wallets_from_observations(observations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Group wallets that co-appear in the same set of observations.
    Uses union-find (disjoint set) to merge groups of co-occurring wallets.
    
    observations: list of dicts with 'extracted_entities' containing 'wallets'
    Returns list of clusters: [{wallets: [...], actor_ids: [...], confidence: float, ...}]
    """
    # Build co-occurrence graph
    # Each observation containing multiple wallets = those wallets share an actor
    parent: Dict[str, str] = {}
    obs_metadata: Dict[str, List[Dict]] = defaultdict(list)  # wallet -> observation info

    def find(x):
        if x not in parent:
            parent[x] = x
        while parent[x] != x:
            parent[x] = parent[parent[x]]  # path compression
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for obs in observations:
        entities = obs.get("extracted_entities") or {}
        wallets = entities.get("wallets", []) or []
        # Also check btc_wallets / btc field
        wallets += entities.get("btc_wallets", []) or []
        wallets += entities.get("btc", []) or []
        wallets = list(set(w for w in wallets if w and len(w) > 20))

        if not wallets:
            continue

        # Register all wallets
        for w in wallets:
            if w not in parent:
                parent[w] = w
            obs_metadata[w].append({
                "obs_id": obs.get("id"),
                "source": obs.get("source_name", obs.get("source", "unknown")),
                "candidate_actor_id": obs.get("candidate_actor_id"),
                "candidate_confidence": obs.get("candidate_confidence"),
            })

        # Union all wallets appearing in the same observation
        for i in range(1, len(wallets)):
            union(wallets[0], wallets[i])

    # Collect clusters
    clusters_map: Dict[str, Dict] = {}
    for wallet in parent:
        root = find(wallet)
        if root not in clusters_map:
            clusters_map[root] = {
                "cluster_id": hashlib.md5(root.encode()).hexdigest()[:8],
                "wallets": [],
                "actor_ids": set(),
                "sources": set(),
                "obs_ids": set(),
                "confidence": 0.0,
            }
        clusters_map[root]["wallets"].append(wallet)

        # Aggregate metadata
        for meta in obs_metadata.get(wallet, []):
            if meta.get("candidate_actor_id"):
                clusters_map[root]["actor_ids"].add(meta["candidate_actor_id"])
            if meta.get("source"):
                clusters_map[root]["sources"].add(meta["source"])
            if meta.get("obs_id"):
                clusters_map[root]["obs_ids"].add(meta["obs_id"])

    # Convert sets to lists and compute confidence
    result = []
    for root, cluster in clusters_map.items():
        n = len(cluster["wallets"])
        # More wallets co-appearing = higher confidence they share an actor
        confidence = min(0.95, 0.50 + (n - 1) * 0.10) if n > 1 else 0.40
        result.append({
            "cluster_id": cluster["cluster_id"],
            "wallets": sorted(cluster["wallets"]),
            "wallet_count": n,
            "actor_ids": sorted(cluster["actor_ids"]),
            "sources": sorted(cluster["sources"]),
            "observation_ids": sorted(cluster["obs_ids"]),
            "confidence": round(confidence, 2),
            "method": "common_co_occurrence",
            "note": (
                f"{n} address(es) co-appearing across {len(cluster['obs_ids'])} observation(s)"
                if n > 1 else "Single address — no clustering evidence"
            ),
        })

    # Sort by cluster size descending
    result.sort(key=lambda c: (c["wallet_count"], c["confidence"]), reverse=True)
    return result


def cluster_actor_wallets(actor_id: int, db_session) -> Dict[str, Any]:
    """
    Cluster wallets for a specific actor using their linked observations.
    """
    try:
        from app.models.intelligence import Observation
        from app.models.actor import Actor, Wallet

        # Get actor info
        actor = db_session.query(Actor).filter(Actor.id == actor_id).first()
        if not actor:
            return {"error": f"Actor {actor_id} not found", "clusters": []}

        # Get all known wallets for this actor
        db_wallets = db_session.query(Wallet).filter(
            Wallet.actor_id == actor_id
        ).all()
        known_wallets = [w.address for w in db_wallets if w.address]

        # Get observations linked to this actor
        observations = db_session.query(Observation).filter(
            Observation.candidate_actor_id == actor_id
        ).limit(200).all()

        obs_dicts = [
            {
                "id": o.id,
                "extracted_entities": o.extracted_entities or {},
                "source_name": o.source_name,
                "candidate_actor_id": o.candidate_actor_id,
                "candidate_confidence": o.candidate_confidence,
            }
            for o in observations
        ]

        clusters = cluster_wallets_from_observations(obs_dicts)

        # Enrich clusters with blockchain info (optional, rate-limited)
        enriched = []
        for cluster in clusters[:10]:  # limit API calls
            enriched_cluster = dict(cluster)
            if len(cluster["wallets"]) >= 2:
                enriched_cluster["blockchain_check"] = _check_blockchain_cooccurrence(
                    cluster["wallets"][:3]  # check up to 3 wallets
                )
            enriched.append(enriched_cluster)

        return {
            "actor_id": actor_id,
            "actor_name": actor.actor_name,
            "known_wallets": known_wallets,
            "total_observations_analyzed": len(observations),
            "clusters": enriched or clusters,
            "total_clusters": len(clusters),
            "summary": (
                f"Found {len(clusters)} wallet cluster(s) across {len(observations)} observations. "
                f"Actor has {len(known_wallets)} registered wallet(s)."
            ),
        }

    except Exception as e:
        logger.error(f"[WalletCluster] Actor {actor_id} clustering error: {e}")
        return {"error": str(e), "clusters": []}


def cluster_all_wallets(db_session) -> Dict[str, Any]:
    """
    Run wallet clustering across all observations in the database.
    Returns global clusters that may link wallets across different actors.
    """
    try:
        from app.models.intelligence import Observation

        observations = db_session.query(Observation).limit(500).all()
        obs_dicts = [
            {
                "id": o.id,
                "extracted_entities": o.extracted_entities or {},
                "source_name": o.source_name,
                "candidate_actor_id": o.candidate_actor_id,
                "candidate_confidence": o.candidate_confidence,
            }
            for o in observations
        ]

        clusters = cluster_wallets_from_observations(obs_dicts)

        # Flag cross-actor clusters (high value finding)
        cross_actor_clusters = [c for c in clusters if len(c["actor_ids"]) > 1]

        return {
            "total_observations_analyzed": len(observations),
            "total_clusters": len(clusters),
            "cross_actor_clusters": len(cross_actor_clusters),
            "clusters": clusters[:50],  # return top 50
            "high_value_findings": cross_actor_clusters[:10],
            "summary": (
                f"Analyzed {len(observations)} observations. "
                f"Found {len(clusters)} wallet cluster(s). "
                f"{len(cross_actor_clusters)} cluster(s) span multiple actors (shared infrastructure signal)."
            ),
        }

    except Exception as e:
        logger.error(f"[WalletCluster] Global clustering error: {e}")
        return {"error": str(e), "clusters": []}


def _check_blockchain_cooccurrence(wallets: List[str]) -> Dict[str, Any]:
    """
    Optionally check Blockchain.info API for address info (graceful degradation).
    This is informational only — does not block clustering.
    """
    result = {"checked": False, "addresses": {}}
    try:
        import httpx
        for wallet in wallets[:2]:  # limit API calls
            try:
                url = f"https://blockchain.info/rawaddr/{wallet}?limit=5"
                resp = httpx.get(url, timeout=5.0, headers={"User-Agent": "DarkTrace-WalletCluster/1.0"})
                if resp.status_code == 200:
                    data = resp.json()
                    result["checked"] = True
                    result["addresses"][wallet] = {
                        "final_balance": data.get("final_balance", 0),
                        "total_received": data.get("total_received", 0),
                        "n_tx": data.get("n_tx", 0),
                    }
            except Exception:
                pass
    except ImportError:
        pass
    return result
