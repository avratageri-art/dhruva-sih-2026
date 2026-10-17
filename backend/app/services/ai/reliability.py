"""Explainable, reliability-gated attribution decisions.

The similarity model remains available as a baseline.  This module decides
whether the available evidence is safe to assert, or whether the system must
abstain.  It deliberately uses transparent rules and a versioned config.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


_MODULE_PATH = Path(__file__).resolve()
_CONFIG_CANDIDATES = (
    _MODULE_PATH.parents[4] / "config" / "reliability.yaml",  # repository checkout
    _MODULE_PATH.parents[3] / "config" / "reliability.yaml",  # container /app
)
CONFIG_PATH = next((candidate for candidate in _CONFIG_CANDIDATES if candidate.exists()), _CONFIG_CANDIDATES[0])


def load_config(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load the JSON-compatible YAML config without adding a runtime dependency."""
    with (path or CONFIG_PATH).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _utc(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()


@dataclass
class EvidenceItem:
    evidence_id: str
    type: str
    subject_a: str
    subject_b: str
    value: str
    source_id: str = "derived"
    observed_at: Optional[str] = None
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    content_hash: Optional[str] = None
    origin_id: Optional[str] = None
    is_derived: bool = False
    raw_ref: Optional[str] = None
    direction: str = "support"
    quality: float = 0.8
    rarity: float = 1.0
    freshness: float = 1.0
    independence: float = 1.0
    weight: float = 0.0
    shared: bool = False
    severity: Optional[str] = None
    explanation: str = ""
    deception_flags: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any], index: int = 0) -> "EvidenceItem":
        data = dict(raw)
        data.setdefault("evidence_id", f"ev-{index + 1}")
        data.setdefault("subject_a", str(data.pop("actor_a", "actor-a")))
        data.setdefault("subject_b", str(data.pop("actor_b", "actor-b")))
        data.setdefault("value", "")
        allowed = cls.__dataclass_fields__.keys()
        return cls(**{key: value for key, value in data.items() if key in allowed})


def collapse_lineage(items: Iterable[EvidenceItem], near_duplicate: float = 0.88) -> List[EvidenceItem]:
    """Assign origin roots and mark exact/near copies as derived evidence."""
    materialized = list(items)
    roots: List[EvidenceItem] = []
    for item in sorted(materialized, key=lambda row: _utc(row.observed_at) or datetime.min.replace(tzinfo=timezone.utc)):
        item.content_hash = item.content_hash or _hash(item.value.strip().lower())
        root = next((candidate for candidate in roots if candidate.type == item.type and candidate.content_hash == item.content_hash), None)
        if root is None and len(item.value) >= 40:
            root = next(
                (
                    candidate for candidate in roots
                    if candidate.type == item.type
                    and len(candidate.value) >= 40
                    and SequenceMatcher(None, candidate.value.lower(), item.value.lower()).ratio() >= near_duplicate
                ),
                None,
            )
        if root is None:
            item.origin_id = item.origin_id or item.evidence_id
            roots.append(item)
        else:
            item.origin_id = root.origin_id or root.evidence_id
            item.is_derived = True
            item.independence = 0.0
            if not item.explanation:
                item.explanation = f"Derived from {item.origin_id}; excluded from independent support."
    return materialized


class ReliabilityEngine:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or load_config()

    def _freshness(self, item: EvidenceItem, now: datetime) -> float:
        observed = _utc(item.last_seen or item.observed_at)
        if observed is None:
            return 0.8
        age_days = max(0.0, (now - observed).total_seconds() / 86400)
        half_life = float(self.config["freshness_half_life_days"].get(item.type, 365))
        return round(math.pow(0.5, age_days / max(half_life, 1.0)), 4)

    def _is_shared_infra(self, item: EvidenceItem) -> bool:
        value = item.value.lower()
        return item.shared or any(signature in value for signature in self.config["known_shared_services"])

    def assess(
        self,
        actor_a: Dict[str, Any],
        actor_b: Dict[str, Any],
        evidence_items: Iterable[Dict[str, Any] | EvidenceItem],
        *,
        degraded: bool = False,
        now: Optional[datetime] = None,
        disabled_components: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        cfg = self.config
        thresholds = cfg["thresholds"]
        current = now or datetime.now(timezone.utc)
        disabled = set(disabled_components or [])
        items = [item if isinstance(item, EvidenceItem) else EvidenceItem.from_dict(item, index) for index, item in enumerate(evidence_items)]
        collapse_lineage(items, thresholds["near_duplicate_similarity"])
        if "independence" in disabled:
            for item in items:
                item.origin_id = item.evidence_id
                item.is_derived = False
                item.independence = 1.0

        roots_seen = set()
        deception_flags = []
        for item in items:
            item.quality = max(0.0, min(1.0, float(item.quality)))
            item.rarity = 1.0 if "rarity" in disabled else max(0.0, min(1.0, float(item.rarity)))
            item.freshness = self._freshness(item, current)
            lineage_key = (item.direction, item.origin_id)
            if lineage_key in roots_seen:
                item.is_derived = True
                item.independence = 0.0
            else:
                roots_seen.add(lineage_key)
                item.independence = 1.0

            base = float(cfg["base_weights"].get(item.type, 0.4))
            item.shared = item.type == "infra" and self._is_shared_infra(item)
            if item.shared and "shared_discount" not in disabled:
                base *= float(cfg["shared_infrastructure_cap"])
                item.explanation = item.explanation or "Known shared infrastructure; contribution capped."
            if item.direction == "contradict":
                base = float(
                    cfg["strong_contradiction_weight"]
                    if item.severity == "strong"
                    else cfg["weak_contradiction_weight"]
                )
            item.weight = round(base * item.quality * item.independence * item.rarity * item.freshness, 4)
            deception_flags.extend(item.deception_flags)

        support_items = [item for item in items if item.direction == "support"]
        contradiction_items = [item for item in items if item.direction == "contradict"]
        support = round(sum(item.weight for item in support_items), 4)
        contradiction = round(sum(item.weight for item in contradiction_items), 4)
        independent_origins = len({item.origin_id for item in support_items if item.independence > 0 and item.weight > 0})
        strong_veto = "veto" not in disabled and any(item.severity == "strong" and item.weight > 0 for item in contradiction_items)
        weighted_support_items = [item for item in support_items if item.weight > 0]
        infra_only = (
            "shared_discount" not in disabled
            and bool(weighted_support_items)
            and all(item.type == "infra" for item in weighted_support_items)
        )
        ratio = contradiction / max(support, 0.0001)
        dominant_tainted = any(
            item.deception_flags and item.weight >= support * thresholds["dominant_evidence"]
            for item in support_items
        )
        tainted = len(set(deception_flags)) >= 2 or dominant_tainted

        gates = []
        if independent_origins < thresholds["minimum_independent_origins"]:
            gates.append("MINIMUM_INDEPENDENT_ORIGINS")
        if support < thresholds["minimum_support"]:
            gates.append("MINIMUM_WEIGHTED_SUPPORT")
        if infra_only:
            gates.append("SHARED_INFRA_ONLY")
        if strong_veto:
            gates.append("STRONG_CONTRADICTION_VETO")
        elif contradiction and ratio >= thresholds["contested_ratio"]:
            gates.append("CONTRADICTION_RATIO")
        if tainted:
            gates.append("DECEPTION_RISK")
        if degraded:
            gates.append("DEGRADED_MODEL")

        if tainted:
            reason = "TAINTED"
        elif strong_veto or "CONTRADICTION_RATIO" in gates:
            reason = "CONTESTED"
        elif infra_only:
            reason = "SHARED_INFRA_ONLY"
        elif independent_origins < thresholds["minimum_independent_origins"] or support < thresholds["minimum_support"]:
            reason = "INSUFFICIENT"
        else:
            reason = None
        decision = "SUPPORTED" if reason is None else "ABSTAIN"

        effective = max(0.0, support - contradiction)
        if effective >= thresholds["high_confidence"]:
            band = "HIGH"
        elif effective >= thresholds["medium_confidence"]:
            band = "MEDIUM"
        else:
            band = "LOW"
        if degraded and band == "HIGH":
            band = "MEDIUM"

        return {
            "decision": decision,
            "abstain_reason": reason,
            "confidence_band": band,
            "support": support,
            "contradiction": contradiction,
            "independent_origins": independent_origins,
            "items": [asdict(item) for item in items],
            "gates_triggered": gates,
            "deception_flags": sorted(set(deception_flags)),
            "degraded": degraded,
            "config_version": cfg["version"],
        }

    def build_evidence_items(
        self,
        actor_a: Dict[str, Any],
        actor_b: Dict[str, Any],
        subsystem_scores: Dict[str, float],
        frequencies: Optional[Dict[str, Dict[str, int]]] = None,
        wallet_labels: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """Convert aggregate actor data into atomic, explainable evidence."""
        frequencies = frequencies or {}
        wallet_labels = {key.lower(): value.lower() for key, value in (wallet_labels or {}).items()}
        a_name = str(actor_a.get("id", actor_a.get("name", "actor-a")))
        b_name = str(actor_b.get("id", actor_b.get("name", "actor-b")))
        result: List[Dict[str, Any]] = []

        def rarity(kind: str, value: str) -> float:
            count = max(1, int(frequencies.get(kind, {}).get(value.lower(), 1)))
            return round(1.0 / count, 4)

        def add(kind: str, value: str, **extra: Any) -> None:
            result.append({
                "evidence_id": f"{kind}-{len(result) + 1}",
                "type": kind,
                "subject_a": a_name,
                "subject_b": b_name,
                "value": value,
                "source_id": str(extra.pop("source_id", "derived-comparison")),
                "observed_at": extra.pop("observed_at", None),
                "raw_ref": extra.pop("raw_ref", None),
                **extra,
            })

        for kind, key in (("handle", "handles"), ("pgp", "pgps"), ("wallet", "wallets"), ("infra", "onion_services")):
            values_a = {str(value).strip() for value in actor_a.get(key, []) if str(value).strip()}
            values_b = {str(value).strip() for value in actor_b.get(key, []) if str(value).strip()}
            for value in sorted(values_a & values_b):
                label = wallet_labels.get(value.lower()) if kind == "wallet" else None
                is_service_wallet = label in self.config["service_wallet_labels"]
                add(
                    kind,
                    value,
                    rarity=rarity(kind, value),
                    shared=is_service_wallet,
                    direction="contradict" if is_service_wallet else "support",
                    severity="strong" if is_service_wallet else None,
                    explanation=(
                        f"Known {label} wallet is shared infrastructure, not identity proof."
                        if is_service_wallet else f"Exact shared {kind} indicator."
                    ),
                )

        text_chars = min(
            sum(len(str(text)) for text in actor_a.get("texts", [])),
            sum(len(str(text)) for text in actor_b.get("texts", [])),
        )
        semantic = float(subsystem_scores.get("semantic", 0.0))
        stylometric = float(subsystem_scores.get("stylometric", 0.0))
        behavioural = float(subsystem_scores.get("behavioural", 0.0))
        handle_score = float(subsystem_scores.get("handle", 0.0))
        corpus_origin = f"corpus-{a_name}-{b_name}"

        if semantic >= 0.65:
            add("semantic", f"population-adjusted-score:{semantic:.4f}", origin_id=corpus_origin, quality=semantic, rarity=max(0.1, (semantic - 0.5) * 2), explanation="Weak topic/semantic similarity signal; capped by design.")
        if text_chars >= self.config["thresholds"]["minimum_stylometry_characters"]:
            if stylometric >= 0.7:
                add("stylometry", f"stylometric-score:{stylometric:.4f}", origin_id=corpus_origin, quality=stylometric, rarity=max(0.1, (stylometric - 0.5) * 2), explanation=f"Writing-style similarity across at least {text_chars} characters.")
            elif stylometric <= 0.35:
                add("stylometry", f"stylometric-score:{stylometric:.4f}", origin_id=corpus_origin, direction="contradict", severity="strong", quality=1 - stylometric, explanation="Strong linguistic mismatch with sufficient text.")
        if behavioural >= 0.7:
            add("temporal", f"behavioural-score:{behavioural:.4f}", origin_id=corpus_origin, quality=behavioural, explanation="Similar activity-window distribution.")
        elif actor_a.get("timestamps") and actor_b.get("timestamps") and behavioural <= 0.2:
            add("temporal", f"behavioural-score:{behavioural:.4f}", origin_id=corpus_origin, direction="contradict", severity="strong", quality=1 - behavioural, explanation="Incompatible activity-window distributions.")

        shared_handles = {
            str(value).lower().lstrip("@") for value in actor_a.get("handles", [])
        } & {
            str(value).lower().lstrip("@") for value in actor_b.get("handles", [])
        }
        if not shared_handles and handle_score >= 0.88:
            created_a = _utc(actor_a.get("created_at"))
            created_b = _utc(actor_b.get("created_at"))
            flags = ["HANDLE_TYPOSQUAT"]
            if created_a and created_b:
                flags.append("LATER_CREATED_LOOKALIKE")
            add("handle", f"similar-handle-score:{handle_score:.4f}", quality=handle_score, rarity=0.4, deception_flags=flags, explanation="Close handle variant without an exact shared identifier.")

        # Callers and the synthetic benchmark may supply explicit rule findings.
        for contradiction in actor_a.get("contradictions", []) + actor_b.get("contradictions", []):
            add(
                contradiction.get("type", "temporal"),
                str(contradiction.get("value", contradiction.get("type", "conflict"))),
                direction="contradict",
                severity=contradiction.get("severity", "weak"),
                quality=float(contradiction.get("quality", 1.0)),
                raw_ref=contradiction.get("raw_ref"),
                explanation=contradiction.get("explanation", "Explicit contradiction rule matched."),
            )
        return result


reliability_engine = ReliabilityEngine()
