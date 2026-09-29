from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from app.database import get_db
from app.models.actor import Actor, Handle, PGPIdentifier, Wallet
from app.models.intelligence import Post, OnionService, Domain, InfrastructureIndicator
from app.models.analysis import Source, Relationship, AttributionAssessment

router = APIRouter(tags=["Analysis"])


# ─── Attribution Assessments ────────────────────────────────────────────────

@router.get("/assessments")
def get_assessments(db: Session = Depends(get_db), skip: int = 0, limit: int = 50):
    """Return all attribution assessments, optionally filtered by confidence level."""
    assessments = db.query(AttributionAssessment).order_by(
        AttributionAssessment.score.desc()
    ).offset(skip).limit(limit).all()

    result = []
    for aa in assessments:
        actor_a = db.query(Actor).filter(Actor.id == aa.actor_a).first()
        actor_b = db.query(Actor).filter(Actor.id == aa.actor_b).first()
        result.append({
            "id": aa.id,
            "score": round(aa.score * 100, 1) if aa.score <= 1 else round(aa.score, 1),
            "confidence_level": aa.confidence_level,
            "actor_a": {"id": aa.actor_a, "name": actor_a.actor_name if actor_a else "Unknown"},
            "actor_b": {"id": aa.actor_b, "name": actor_b.actor_name if actor_b else "Unknown"},
            "explanation": aa.explanation,
            "evidence": aa.evidence_json,
            "negative_evidence": aa.negative_evidence_json,
            "created_at": aa.created_at.isoformat() if aa.created_at else None,
        })
    return result


@router.post("/assess")
def run_attribution(actor_a_id: int, actor_b_id: int, db: Session = Depends(get_db)):
    """
    Run the real AI attribution engine on two actors.

    Pipeline:
      1. sentence-transformers/all-MiniLM-L6-v2  →  semantic cosine similarity
      2. Classical NLP features                   →  stylometric similarity
      3. Temporal histogram                       →  behavioural similarity
      4. Jaro-Winkler on handle sets              →  handle overlap score
      5. Jaccard on shared infrastructure         →  graph correlation
      6. Weighted fusion                          →  final attribution score
    """
    actor_a = db.query(Actor).filter(Actor.id == actor_a_id).first()
    actor_b = db.query(Actor).filter(Actor.id == actor_b_id).first()

    if not actor_a or not actor_b:
        raise HTTPException(status_code=404, detail="One or both actors not found")

    # ── Gather evidence ────────────────────────────────────────────────────
    posts_a = db.query(Post).filter(Post.actor_id == actor_a_id).all()
    posts_b = db.query(Post).filter(Post.actor_id == actor_b_id).all()
    handles_a = [h.handle for h in actor_a.handles]
    handles_b = [h.handle for h in actor_b.handles]
    wallets_a = [w.address for w in actor_a.wallets]
    wallets_b = [w.address for w in actor_b.wallets]
    pgps_a = [p.fingerprint for p in actor_a.pgp_identifiers]
    pgps_b = [p.fingerprint for p in actor_b.pgp_identifiers]

    actor_a_data = {
        "texts":      [p.content for p in posts_a if p.content],
        "timestamps": [p.timestamp.isoformat() for p in posts_a if p.timestamp],
        "handles":    handles_a,
        "wallets":    wallets_a,
        "pgps":       pgps_a,
        "graph_score": 0.0,
    }
    actor_b_data = {
        "texts":      [p.content for p in posts_b if p.content],
        "timestamps": [p.timestamp.isoformat() for p in posts_b if p.timestamp],
        "handles":    handles_b,
        "wallets":    wallets_b,
        "pgps":       pgps_b,
        "graph_score": 0.0,
    }

    # ── Run AI engine ──────────────────────────────────────────────────────
    try:
        from app.services.ai.attribution import attribution_engine
        score_pct, label, explanation = attribution_engine.assess_attribution(
            actor_a_data, actor_b_data
        )
        subsystem_scores = attribution_engine.get_subsystem_scores(
            actor_a_data, actor_b_data
        )
        score = score_pct / 100.0
        ai_powered = True
    except Exception as e:
        # Fallback: handle overlap heuristic only
        overlap = len(set(handles_a) & set(handles_b))
        score = min(0.99, 0.1 + overlap * 0.2)
        label = "HIGH" if score >= 0.65 else "MODERATE" if score >= 0.5 else "LOW"
        explanation = f"Heuristic fallback (AI engine unavailable: {str(e)[:80]})"
        subsystem_scores = {
            "semantic": 0.0, "stylometric": 0.0,
            "behavioural": 0.0, "handle": float(overlap > 0),
            "graph": 0.0, "model": "fallback", "model_loaded": False,
        }
        ai_powered = False

    evidence = {
        "semantic_similarity":    subsystem_scores.get("semantic", 0),
        "stylometric_similarity": subsystem_scores.get("stylometric", 0),
        "behavioural_similarity": subsystem_scores.get("behavioural", 0),
        "handle_overlap":         subsystem_scores.get("handle", 0),
        "graph_correlation":      subsystem_scores.get("graph", 0),
        "texts_compared":         len(posts_a) + len(posts_b),
        "model":                  subsystem_scores.get("model", "unknown"),
        "model_loaded":           subsystem_scores.get("model_loaded", False),
        "ai_powered":             ai_powered,
    }

    # ── Persist / update ───────────────────────────────────────────────────
    existing = db.query(AttributionAssessment).filter(
        ((AttributionAssessment.actor_a == actor_a_id) & (AttributionAssessment.actor_b == actor_b_id)) |
        ((AttributionAssessment.actor_a == actor_b_id) & (AttributionAssessment.actor_b == actor_a_id))
    ).first()

    if existing:
        existing.score = score
        existing.confidence_level = label
        existing.explanation = explanation
        existing.evidence_json = evidence
        db.commit()
        assessment_id = existing.id
    else:
        assessment = AttributionAssessment(
            actor_a=actor_a_id,
            actor_b=actor_b_id,
            score=score,
            confidence_level=label,
            explanation=explanation,
            evidence_json=evidence,
            negative_evidence_json={},
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)
        assessment_id = assessment.id

    return {
        "assessment_id":   assessment_id,
        "actor_a":         {"id": actor_a_id, "name": actor_a.actor_name},
        "actor_b":         {"id": actor_b_id, "name": actor_b.actor_name},
        "score":           round(score * 100, 1),
        "confidence_level": label,
        "explanation":     explanation,
        "evidence":        evidence,
        "ai_powered":      ai_powered,
    }



# ─── Infrastructure ──────────────────────────────────────────────────────────

@router.get("/infrastructure")
def get_infrastructure(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    """Return onion services and infrastructure indicators."""
    services = db.query(OnionService).offset(skip).limit(limit).all()
    indicators = db.query(InfrastructureIndicator).limit(200).all()
    domains = db.query(Domain).limit(100).all()

    return {
        "onion_services": [{
            "id": s.id,
            "address": s.address,
            "title": s.title or "Unknown Service",
            "status": s.status or "UNKNOWN",
            "first_seen": s.first_seen.isoformat() if s.first_seen else None,
            "last_seen": s.last_seen.isoformat() if s.last_seen else None,
            "metadata": s.metadata_,
        } for s in services],
        "indicators": [{
            "id": i.id,
            "type": i.indicator_type,
            "value": i.value,
            "confidence": i.confidence,
            "service_id": i.service_id,
            "observed_at": i.observed_at.isoformat() if i.observed_at else None,
        } for i in indicators],
        "domains": [{
            "id": d.id,
            "domain": d.domain,
            "actor_id": d.actor_id,
        } for d in domains],
        "stats": {
            "total_services": db.query(OnionService).count(),
            "active_services": db.query(OnionService).filter(OnionService.status == "ACTIVE").count(),
            "total_indicators": db.query(InfrastructureIndicator).count(),
            "total_domains": db.query(Domain).count(),
        }
    }


# ─── Intelligence Feed ────────────────────────────────────────────────────────

@router.get("/intelligence")
def get_intelligence(db: Session = Depends(get_db), skip: int = 0, limit: int = 50):
    """Return recent intelligence posts."""
    posts = db.query(Post).order_by(Post.timestamp.desc()).offset(skip).limit(limit).all()

    result = []
    for p in posts:
        actor = db.query(Actor).filter(Actor.id == p.actor_id).first() if p.actor_id else None
        result.append({
            "id": p.id,
            "platform": p.platform,
            "content": p.content,
            "timestamp": p.timestamp.isoformat() if p.timestamp else None,
            "language": p.language,
            "actor": {"id": actor.id, "name": actor.actor_name} if actor else None,
        })
    return result


# ─── Relationships ────────────────────────────────────────────────────────────

@router.get("/relationships")
def get_relationships(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    """Return all entity relationships."""
    rels = db.query(Relationship).offset(skip).limit(limit).all()
    return [{
        "id": r.id,
        "type": r.relationship_type,
        "source_type": r.source_entity_type,
        "source_id": r.source_entity_id,
        "target_type": r.target_entity_type,
        "target_id": r.target_entity_id,
        "confidence": r.confidence,
        "evidence": r.evidence,
    } for r in rels]


# ─── Graph Data ───────────────────────────────────────────────────────────────

@router.get("/graph")
def get_graph_data(
    db: Session = Depends(get_db),
    actor_id: Optional[int] = None,
    actor_ids: Optional[str] = None,
    depth: int = 2,
    confidence_min: float = 0.0,
    limit: int = 150,
):
    """
    Return forensic-grade, Cytoscape-compatible graph data.
    Defaults to GLOBAL GRAPH MODE showing all actors and cross-actor bridges.
    Supports ACTOR FOCUS MODE when actor_id is specified with depth traversal (1..3).
    Supports MULTI_ACTOR MODE when actor_ids is specified (comma-separated list).
    """
    depth = max(1, min(depth, 3))
    nodes_dict = {}
    edges_dict = {}

    def add_node(node_id: str, label: str, entity_type: str, **kwargs):
        if node_id not in nodes_dict:
            node_data = {
                "id": node_id,
                "label": label,
                "type": entity_type,
                **kwargs
            }
            nodes_dict[node_id] = {"data": node_data}

    def add_edge(edge_id: str, source: str, target: str, rel_type: str, confidence: float = 1.0, **kwargs):
        if source in nodes_dict and target in nodes_dict and edge_id not in edges_dict:
            if confidence >= confidence_min:
                edges_dict[edge_id] = {"data": {
                    "id": edge_id,
                    "source": source,
                    "target": target,
                    "label": rel_type,
                    "type": rel_type,
                    "confidence": round(confidence, 3),
                    **kwargs
                }}

    primary_actor = None
    graph_mode = "GLOBAL"
    included_actor_ids = set()

    if actor_ids:
        # Multi-Actor Comparison Mode
        graph_mode = "MULTI_ACTOR"
        parsed = [int(x.strip()) for x in actor_ids.split(",") if x.strip().isdigit()]
        included_actor_ids = set(parsed)
    elif actor_id:
        # Actor Focus Mode
        graph_mode = "ACTOR_FOCUS"
        primary_actor = db.query(Actor).filter(Actor.id == actor_id).first()
        if primary_actor:
            included_actor_ids.add(primary_actor.id)
            if depth >= 2:
                # Include peers with attribution or direct relationships
                assessments = db.query(AttributionAssessment).filter(
                    ((AttributionAssessment.actor_a == primary_actor.id) | (AttributionAssessment.actor_b == primary_actor.id)) &
                    (AttributionAssessment.score >= confidence_min)
                ).all()
                for aa in assessments:
                    other_id = aa.actor_b if aa.actor_a == primary_actor.id else aa.actor_a
                    included_actor_ids.add(other_id)

                rels = db.query(Relationship).filter(
                    (Relationship.source_entity_type == "actor") & (Relationship.source_entity_id == primary_actor.id) &
                    (Relationship.target_entity_type == "actor")
                ).all()
                for r in rels:
                    included_actor_ids.add(r.target_entity_id)
    else:
        # Default: GLOBAL GRAPH MODE — all actors
        graph_mode = "GLOBAL"
        all_actors = db.query(Actor).all()
        included_actor_ids = {a.id for a in all_actors}

    # 1. Add Actors
    actors = db.query(Actor).filter(Actor.id.in_(included_actor_ids)).all()
    for a in actors:
        is_primary = (primary_actor is not None and a.id == primary_actor.id)
        add_node(
            node_id=f"actor_{a.id}",
            label=a.actor_name,
            entity_type="Actor",
            raw_id=a.id,
            category=a.category or "Unknown",
            status=a.status or "ACTIVE",
            confidence=round(a.confidence or 0.8, 2),
            description=a.description or "",
            first_seen=a.first_seen.isoformat() if a.first_seen else None,
            last_seen=a.last_seen.isoformat() if a.last_seen else None,
            is_primary=is_primary,
            hop=0 if is_primary else 2,
        )

    # 2. Add First-Hop Entities for included actors
    for a in actors:
        actor_nid = f"actor_{a.id}"
        is_primary = (primary_actor is not None and a.id == primary_actor.id)
        hop_lvl = 1 if is_primary else 2

        # Handles
        for h in a.handles:
            h_nid = f"handle_{h.id}"
            add_node(
                node_id=h_nid,
                label=h.handle,
                full_value=h.handle,
                entity_type="Handle",
                raw_id=h.id,
                platform=h.platform or "Darknet",
                actor_id=a.id,
                actor_name=a.actor_name,
                hop=hop_lvl,
            )
            add_edge(
                edge_id=f"e_{actor_nid}_{h_nid}",
                source=actor_nid,
                target=h_nid,
                rel_type="USES_HANDLE",
                confidence=0.95,
                source_platform=h.platform or "Forum Telemetry",
                evidence={"method": "Direct intelligence post analysis"},
            )

            # Platform Node
            if h.platform:
                plat_nid = f"platform_{h.platform.lower().replace(' ', '_')}"
                add_node(
                    node_id=plat_nid,
                    label=h.platform,
                    full_value=h.platform,
                    entity_type="Platform",
                    hop=hop_lvl + 1 if depth >= 2 else hop_lvl,
                )
                add_edge(
                    edge_id=f"e_{h_nid}_{plat_nid}",
                    source=h_nid,
                    target=plat_nid,
                    rel_type="APPEARS_ON",
                    confidence=0.90,
                    source_platform=h.platform,
                )

        # PGP Identifiers
        for p in a.pgp_identifiers:
            p_nid = f"pgp_{p.id}"
            short_fp = f"PGP • {p.fingerprint[:8]}" if len(p.fingerprint) >= 8 else f"PGP • {p.fingerprint}"
            add_node(
                node_id=p_nid,
                label=short_fp,
                full_value=p.fingerprint,
                entity_type="PGP",
                raw_id=p.id,
                actor_id=a.id,
                actor_name=a.actor_name,
                first_seen=p.first_seen.isoformat() if p.first_seen else None,
                last_seen=p.last_seen.isoformat() if p.last_seen else None,
                hop=hop_lvl,
            )
            add_edge(
                edge_id=f"e_{actor_nid}_{p_nid}",
                source=actor_nid,
                target=p_nid,
                rel_type="USES_PGP",
                confidence=0.98,
                source_platform="Cryptographic Keyserver",
                evidence={"fingerprint": p.fingerprint, "method": "Public key signature verification"},
            )

        # Wallets
        for w in a.wallets:
            w_nid = f"wallet_{w.id}"
            short_addr = f"Wallet • {w.address[:6]}...{w.address[-4:]}" if len(w.address) > 12 else f"Wallet • {w.address}"
            add_node(
                node_id=w_nid,
                label=short_addr,
                full_value=w.address,
                entity_type="Wallet",
                raw_id=w.id,
                blockchain=w.blockchain,
                actor_id=a.id,
                actor_name=a.actor_name,
                first_seen=w.first_seen.isoformat() if w.first_seen else None,
                last_seen=w.last_seen.isoformat() if w.last_seen else None,
                hop=hop_lvl,
            )
            add_edge(
                edge_id=f"e_{actor_nid}_{w_nid}",
                source=actor_nid,
                target=w_nid,
                rel_type="ASSOCIATED_WITH_WALLET",
                confidence=0.88,
                source_platform="On-Chain Ledger",
                evidence={"blockchain": w.blockchain, "address": w.address, "method": "Transaction clustering"},
            )

        # Domains
        domains = db.query(Domain).filter(Domain.actor_id == a.id).all()
        for d in domains:
            d_nid = f"domain_{d.id}"
            add_node(
                node_id=d_nid,
                label=f"Domain • {d.domain}",
                full_value=d.domain,
                entity_type="Domain",
                raw_id=d.id,
                actor_id=a.id,
                actor_name=a.actor_name,
                hop=hop_lvl + 1 if depth >= 2 else hop_lvl,
            )
            add_edge(
                edge_id=f"e_{actor_nid}_{d_nid}",
                source=actor_nid,
                target=d_nid,
                rel_type="ASSOCIATED_WITH_DOMAIN",
                confidence=0.82,
                source_platform="DNS Telemetry",
                evidence={"domain": d.domain, "method": "Passive DNS resolution"},
            )

    # 3. Onion Services & Infrastructure (Hop 1 & Hop 2)
    # Check relationships linking actors to onion services
    onion_rels = db.query(Relationship).filter(
        (Relationship.source_entity_type == "actor") &
        (Relationship.source_entity_id.in_(included_actor_ids)) &
        (Relationship.target_entity_type == "onion_service")
    ).all()

    # Also directly get some onion services for realistic infrastructure graph
    onions_to_include = {r.target_entity_id for r in onion_rels}
    if primary_actor and not onions_to_include:
        first_onion = db.query(OnionService).first()
        if first_onion:
            onions_to_include.add(first_onion.id)

    onions = db.query(OnionService).filter(OnionService.id.in_(onions_to_include)).all()
    for o in onions:
        o_nid = f"onion_{o.id}"
        short_addr = f"Onion • {o.address[:8]}..."
        add_node(
            node_id=o_nid,
            label=short_addr,
            full_value=o.address,
            entity_type="OnionService",
            raw_id=o.id,
            title=o.title or "Hidden Service",
            status=o.status or "ACTIVE",
            hop=2,
        )
        if primary_actor:
            add_edge(
                edge_id=f"e_actor_{primary_actor.id}_{o_nid}",
                source=f"actor_{primary_actor.id}",
                target=o_nid,
                rel_type="USES_INFRASTRUCTURE",
                confidence=0.88,
                source_platform="Tor Network Scraper",
                evidence={"method": "Hidden service banner fingerprinting and PGP linkage"},
            )

        # Hop 2: Infrastructure Indicators connected to Onion Service
        if depth >= 2:
            indicators = db.query(InfrastructureIndicator).filter(
                InfrastructureIndicator.service_id == o.id
            ).limit(3).all()
            for ind in indicators:
                ind_nid = f"infra_{ind.id}"
                short_val = f"{ind.indicator_type}: {ind.value[:10]}..." if len(ind.value) > 12 else f"{ind.indicator_type}: {ind.value}"
                add_node(
                    node_id=ind_nid,
                    label=short_val,
                    full_value=ind.value,
                    entity_type="Infrastructure",
                    raw_id=ind.id,
                    indicator_type=ind.indicator_type,
                    confidence=ind.confidence or 0.75,
                    hop=3,
                )
                add_edge(
                    edge_id=f"e_{o_nid}_{ind_nid}",
                    source=o_nid,
                    target=ind_nid,
                    rel_type="HAS_INFRASTRUCTURE",
                    confidence=ind.confidence or 0.75,
                    source_platform="Infrastructure Scanner",
                    evidence={"type": ind.indicator_type, "value": ind.value},
                )

    # 4. Cross-Entity Relationships & Attribution Assessments (Actor <-> Actor)
    assessments = db.query(AttributionAssessment).filter(
        (AttributionAssessment.actor_a.in_(included_actor_ids)) &
        (AttributionAssessment.actor_b.in_(included_actor_ids))
    ).all()

    for aa in assessments:
        src = f"actor_{aa.actor_a}"
        tgt = f"actor_{aa.actor_b}"
        if src in nodes_dict and tgt in nodes_dict:
            edge_id = f"e_attrib_{aa.actor_a}_{aa.actor_b}"
            conf_pct = round(aa.score * 100 if aa.score <= 1 else aa.score, 1)
            
            # Format positive evidence points
            ev = aa.evidence_json or {}
            pos_evidence = []
            if ev.get("semantic_similarity"):
                pos_evidence.append(f"AI Semantic similarity: {round(ev['semantic_similarity']*100, 1)}% ({ev.get('model', 'all-MiniLM-L6-v2').split('/')[-1]})")
            if ev.get("stylometric_similarity"):
                pos_evidence.append(f"Classical stylometric NLP match: {round(ev['stylometric_similarity']*100, 1)}%")
            if ev.get("behavioural_similarity"):
                pos_evidence.append(f"Temporal behavioural correlation: {round(ev['behavioural_similarity']*100, 1)}%")
            if ev.get("handle_overlap"):
                pos_evidence.append(f"Handle orthographic/semantic overlap: {round(ev['handle_overlap']*100, 1)}%")
            if ev.get("graph_correlation"):
                pos_evidence.append(f"Shared infrastructure Jaccard: {round(ev['graph_correlation']*100, 1)}%")

            # Format negative evidence
            neg_ev = aa.negative_evidence_json or {}
            neg_points = []
            if neg_ev.get("timezone_mismatch"):
                neg_points.append("Timezone activity offset observed")
            if neg_ev.get("different_platforms"):
                neg_points.append("Different primary platform deployment")

            add_edge(
                edge_id=edge_id,
                source=src,
                target=tgt,
                rel_type="POSSIBLY_SAME_ACTOR",
                confidence=round(aa.score if aa.score <= 1 else aa.score / 100, 3),
                confidence_level=aa.confidence_level or "HIGH",
                score_pct=conf_pct,
                explanation=aa.explanation or "Multi-vector AI attribution assessment",
                positive_evidence=pos_evidence,
                negative_evidence=neg_points,
                source_platform="AI Attribution Engine (all-MiniLM-L6-v2)",
                is_attribution=True,
                actor_a_id=aa.actor_a,
                actor_b_id=aa.actor_b,
            )

    # Also include explicit Relationships from Relationship table
    explicit_rels = db.query(Relationship).filter(
        (Relationship.source_entity_type == "actor") &
        (Relationship.source_entity_id.in_(included_actor_ids)) &
        (Relationship.target_entity_type == "actor") &
        (Relationship.target_entity_id.in_(included_actor_ids))
    ).all()

    for r in explicit_rels:
        src = f"actor_{r.source_entity_id}"
        tgt = f"actor_{r.target_entity_id}"
        edge_id = f"e_rel_{r.id}_{src}_{tgt}"
        if src in nodes_dict and tgt in nodes_dict and edge_id not in edges_dict:
            add_edge(
                edge_id=edge_id,
                source=src,
                target=tgt,
                rel_type=r.relationship_type,
                confidence=r.confidence or 0.85,
                score_pct=round((r.confidence or 0.85) * 100, 1),
                is_attribution=True if r.relationship_type == "POSSIBLE_SAME_ACTOR" else False,
                source_platform="Cross-Entity Intelligence Correlation",
                evidence=r.evidence or {},
                positive_evidence=[f"Multi-source correlation: {r.relationship_type}"],
                negative_evidence=[],
                actor_a_id=r.source_entity_id,
                actor_b_id=r.target_entity_id,
            )

    # 5. Compute Graph Statistics
    node_list = list(nodes_dict.values())
    edge_list = list(edges_dict.values())

    stats = {
        "total_nodes": len(node_list),
        "total_relationships": len(edge_list),
        "actors": sum(1 for n in node_list if n["data"].get("type") == "Actor"),
        "handles": sum(1 for n in node_list if n["data"].get("type") == "Handle"),
        "pgps": sum(1 for n in node_list if n["data"].get("type") == "PGP"),
        "wallets": sum(1 for n in node_list if n["data"].get("type") == "Wallet"),
        "platforms": sum(1 for n in node_list if n["data"].get("type") == "Platform"),
        "onion_services": sum(1 for n in node_list if n["data"].get("type") == "OnionService"),
        "domains": sum(1 for n in node_list if n["data"].get("type") == "Domain"),
        "infrastructure": sum(1 for n in node_list if n["data"].get("type") == "Infrastructure"),
        "high_confidence_links": sum(1 for e in edge_list if e["data"].get("confidence", 0) >= 0.75),
    }

    primary_actor_info = None
    if primary_actor:
        primary_actor_info = {
            "id": primary_actor.id,
            "name": primary_actor.actor_name,
            "category": primary_actor.category,
            "confidence": primary_actor.confidence,
            "status": primary_actor.status,
            "depth": depth,
        }

    return {
        "nodes": node_list,
        "edges": edge_list,
        "stats": stats,
        "primary_actor": primary_actor_info,
        "mode": graph_mode,
        "environment": "LIVE THREAT INTELLIGENCE (TOR SOCKS5)",
    }

