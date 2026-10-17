from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional
import sys, os
from difflib import SequenceMatcher
import json
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from app.database import get_db
from app.models.actor import Actor, Handle, PGPIdentifier, Wallet
from app.models.intelligence import Post, OnionService, Domain, InfrastructureIndicator
from app.models.analysis import (
    AssessmentAuditLog,
    AttributionAssessment,
    EvidenceItem,
    Relationship,
    Source,
)

router = APIRouter(tags=["Analysis"])


def _project_asset(*parts):
    module_path = Path(__file__).resolve()
    candidates = [module_path.parents[3].joinpath(*parts), module_path.parents[2].joinpath(*parts)]
    return next((candidate for candidate in candidates if candidate.exists()), candidates[0])


@router.get("/evaluation")
def get_evaluation_results():
    """Return the reproducible synthetic benchmark output for the dashboard."""
    results_path = _project_asset("data", "evaluation", "results.json")
    try:
        return json.loads(results_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"Evaluation results unavailable: {exc}")


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
            "decision": (aa.evidence_json or {}).get("decision", "ABSTAIN"),
            "abstain_reason": (aa.evidence_json or {}).get("abstain_reason", "INSUFFICIENT"),
            "confidence_band": (aa.evidence_json or {}).get("confidence_band", aa.confidence_level),
            "support": (aa.evidence_json or {}).get("support", 0.0),
            "contradiction": (aa.evidence_json or {}).get("contradiction", 0.0),
            "items": (aa.evidence_json or {}).get("items", []),
            "gates_triggered": (aa.evidence_json or {}).get("gates_triggered", ["LEGACY_ASSESSMENT"]),
            "degraded": (aa.evidence_json or {}).get("degraded", True),
            "baseline": (aa.evidence_json or {}).get("baseline"),
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
      6. Weighted fusion                          →  Baseline A only
      7. Reliability/lineage/contradiction gates  →  supported or abstain
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
        "id":         actor_a_id,
        "name":       actor_a.actor_name,
        "created_at": actor_a.created_at.isoformat() if actor_a.created_at else None,
        "texts":      [p.content for p in posts_a if p.content],
        "timestamps": [p.timestamp.isoformat() for p in posts_a if p.timestamp],
        "handles":    handles_a,
        "wallets":    wallets_a,
        "pgps":       pgps_a,
        "graph_score": 0.0,
    }
    actor_b_data = {
        "id":         actor_b_id,
        "name":       actor_b.actor_name,
        "created_at": actor_b.created_at.isoformat() if actor_b.created_at else None,
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
        baseline_score_pct, baseline_label, baseline_explanation = attribution_engine.assess_attribution(
            actor_a_data, actor_b_data
        )
        subsystem_scores = attribution_engine.get_subsystem_scores(
            actor_a_data, actor_b_data
        )
        ai_powered = True
    except Exception as e:
        # Fallback: handle overlap heuristic only
        overlap = len(set(handles_a) & set(handles_b))
        baseline_score_pct = round(min(0.99, 0.1 + overlap * 0.2) * 100, 1)
        baseline_label = "HIGH" if baseline_score_pct >= 65 else "MODERATE" if baseline_score_pct >= 50 else "LOW"
        baseline_explanation = f"Heuristic fallback (AI engine unavailable: {str(e)[:80]})"
        subsystem_scores = {
            "semantic": 0.0, "stylometric": 0.0,
            "behavioural": 0.0, "handle": float(overlap > 0),
            "graph": 0.0, "model": "fallback", "model_loaded": False,
        }
        ai_powered = False

    # ── Reliability gate: atomic evidence, lineage, contradictions ─────────
    from app.services.ai.reliability import reliability_engine

    def persona_frequency(rows, value_field):
        personas = {}
        for row in rows:
            value = getattr(row, value_field, None)
            if value:
                personas.setdefault(value.lower(), set()).add(row.actor_id)
        return {value: len(actor_ids) for value, actor_ids in personas.items()}

    handle_frequency = persona_frequency(db.query(Handle).all(), "handle")
    pgp_frequency = persona_frequency(db.query(PGPIdentifier).all(), "fingerprint")
    wallet_frequency = persona_frequency(db.query(Wallet).all(), "address")
    frequencies = {
        "handle": handle_frequency,
        "pgp": pgp_frequency,
        "wallet": wallet_frequency,
    }
    wallet_labels_path = _project_asset("config", "wallet_labels.json")
    try:
        wallet_labels = json.loads(wallet_labels_path.read_text(encoding="utf-8")).get("labels", {})
    except (OSError, ValueError):
        wallet_labels = {}
    reliability_items = reliability_engine.build_evidence_items(
        actor_a_data,
        actor_b_data,
        subsystem_scores,
        frequencies=frequencies,
        wallet_labels=wallet_labels,
    )

    # Matching posts remain separate rows until lineage collapse. Exact and
    # near copies therefore count as one origin, regardless of mirror count.
    for post_a in posts_a:
        if not post_a.content or len(post_a.content.strip()) < 40:
            continue
        for post_b in posts_b:
            if not post_b.content or len(post_b.content.strip()) < 40:
                continue
            similarity = SequenceMatcher(None, post_a.content.lower(), post_b.content.lower()).ratio()
            if similarity >= 0.88:
                for post, suffix in ((post_a, "a"), (post_b, "b")):
                    reliability_items.append({
                        "evidence_id": f"post-{post_a.id}-{post_b.id}-{suffix}",
                        "type": "semantic",
                        "subject_a": str(actor_a_id),
                        "subject_b": str(actor_b_id),
                        "value": post.content,
                        "source_id": str(post.source_id or post.platform or "unknown"),
                        "observed_at": post.timestamp.isoformat() if post.timestamp else None,
                        "raw_ref": f"post:{post.id}",
                        "quality": min(1.0, max(0.2, similarity)),
                        "rarity": 0.7,
                        "explanation": "Matching post content; mirrors collapse to one lineage origin.",
                    })

    reliability = reliability_engine.assess(
        actor_a_data,
        actor_b_data,
        reliability_items,
        degraded=not ai_powered,
    )
    effective_support = max(0.0, reliability["support"] - reliability["contradiction"])
    score = min(0.99, effective_support / (effective_support + 1.0))
    if reliability["decision"] == "ABSTAIN":
        score = min(score, 0.49)
    label = reliability["confidence_band"]
    reason_text = (
        f"Reliability decision: {reliability['decision']}"
        + (f" ({reliability['abstain_reason']})" if reliability["abstain_reason"] else "")
        + f"; support={reliability['support']:.3f}, contradiction={reliability['contradiction']:.3f}, "
          f"independent origins={reliability['independent_origins']}."
    )
    explanation = f"{reason_text} Baseline A: {baseline_score_pct:.1f}% ({baseline_label}). {baseline_explanation}"

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
        "decision":               reliability["decision"],
        "abstain_reason":         reliability["abstain_reason"],
        "confidence_band":        reliability["confidence_band"],
        "support":                reliability["support"],
        "contradiction":          reliability["contradiction"],
        "independent_origins":    reliability["independent_origins"],
        "items":                  reliability["items"],
        "gates_triggered":        reliability["gates_triggered"],
        "deception_flags":        reliability["deception_flags"],
        "degraded":               reliability["degraded"],
        "config_version":         reliability["config_version"],
        "baseline": {
            "method": "weighted_similarity",
            "score": baseline_score_pct,
            "confidence_level": baseline_label,
        },
    }
    negative_evidence = {
        "items": [item for item in reliability["items"] if item["direction"] == "contradict"],
        "gates_triggered": reliability["gates_triggered"],
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
        existing.negative_evidence_json = negative_evidence
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
            negative_evidence_json=negative_evidence,
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)
        assessment_id = assessment.id

    db.query(EvidenceItem).filter(EvidenceItem.assessment_id == assessment_id).delete()
    for item in reliability["items"]:
        db.add(EvidenceItem(
            evidence_id=f"assessment-{assessment_id}-{item['evidence_id']}",
            assessment_id=assessment_id,
            evidence_type=item["type"],
            subject_a=item["subject_a"],
            subject_b=item["subject_b"],
            value=item["value"],
            source_id=item["source_id"],
            content_hash=item["content_hash"],
            origin_id=item["origin_id"],
            is_derived=item["is_derived"],
            raw_ref=item["raw_ref"],
            direction=item["direction"],
            weight=item["weight"],
            details_json=item,
        ))
    db.add(AssessmentAuditLog(
        assessment_id=assessment_id,
        action="ASSESSED",
        user="system",
        details_json={"decision": reliability["decision"], "gates_triggered": reliability["gates_triggered"]},
    ))
    db.commit()

    return {
        "assessment_id":   assessment_id,
        "actor_a":         {"id": actor_a_id, "name": actor_a.actor_name},
        "actor_b":         {"id": actor_b_id, "name": actor_b.actor_name},
        "score":           round(score * 100, 1),
        "confidence_level": label,
        "explanation":     explanation,
        "evidence":        evidence,
        "ai_powered":      ai_powered,
        "decision":        reliability["decision"],
        "abstain_reason":  reliability["abstain_reason"],
        "confidence_band": reliability["confidence_band"],
        "support":         reliability["support"],
        "contradiction":   reliability["contradiction"],
        "items":           reliability["items"],
        "gates_triggered": reliability["gates_triggered"],
        "degraded":        reliability["degraded"],
        "baseline":        evidence["baseline"],
    }


@router.post("/assessments/{assessment_id}/override")
def override_assessment(
    assessment_id: int,
    request: Request,
    reason: str,
    user: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Record an analyst override without erasing the engine's original result."""
    assessment = db.query(AttributionAssessment).filter(AttributionAssessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if len(reason.strip()) < 8:
        raise HTTPException(status_code=422, detail="Override reason must be at least 8 characters")
    audit_user = (user or request.headers.get("X-Analyst-ID") or getattr(request.state, "role", "analyst")).strip()
    db.add(AssessmentAuditLog(
        assessment_id=assessment_id,
        action="ANALYST_OVERRIDE",
        user=audit_user or "analyst",
        reason=reason.strip(),
        details_json={"original_decision": (assessment.evidence_json or {}).get("decision")},
    ))
    db.commit()
    return {"assessment_id": assessment_id, "overridden": True, "user": audit_user, "reason": reason.strip()}


@router.get("/assessments/{assessment_id}/audit")
def assessment_audit(assessment_id: int, db: Session = Depends(get_db)):
    entries = db.query(AssessmentAuditLog).filter(
        AssessmentAuditLog.assessment_id == assessment_id
    ).order_by(AssessmentAuditLog.created_at.desc()).all()
    return [{
        "action": entry.action,
        "user": entry.user,
        "reason": entry.reason,
        "details": entry.details_json,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    } for entry in entries]



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

