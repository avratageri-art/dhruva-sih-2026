from copy import deepcopy
from datetime import datetime, timezone

import pytest

from app.services.ai.reliability import EvidenceItem, ReliabilityEngine, collapse_lineage, load_config


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def item(evidence_id, kind, value, **extra):
    return {
        "evidence_id": evidence_id,
        "type": kind,
        "subject_a": "a",
        "subject_b": "b",
        "value": value,
        "quality": 1.0,
        "rarity": 1.0,
        **extra,
    }


def test_exact_and_near_copies_collapse_but_distinct_sources_do_not():
    original = "The same long forum announcement with a unique phrase and signing instructions."
    rows = [
        EvidenceItem.from_dict(item("one", "semantic", original, source_id="forum-a")),
        EvidenceItem.from_dict(item("two", "semantic", original, source_id="mirror-b")),
        EvidenceItem.from_dict(item("three", "semantic", original + "!", source_id="mirror-c")),
        EvidenceItem.from_dict(item("four", "semantic", "A genuinely distinct observation from an unrelated source and author.")),
    ]
    collapse_lineage(rows, 0.88)
    assert len({row.origin_id for row in rows}) == 2
    assert sum(not row.is_derived for row in rows) == 2


def test_shared_infrastructure_alone_never_supports():
    result = ReliabilityEngine().assess({}, {}, [
        item("infra-1", "infra", "cloudflare shared edge", shared=True),
        item("infra-2", "infra", "amazonaws.com shared host", shared=True),
    ], now=NOW)
    assert result["decision"] == "ABSTAIN"
    assert result["abstain_reason"] == "SHARED_INFRA_ONLY"
    assert "SHARED_INFRA_ONLY" in result["gates_triggered"]


@pytest.mark.parametrize("contradiction_type", [
    "temporal", "pgp", "infra", "stylometry", "wallet"
])
def test_each_strong_contradiction_vetoes(contradiction_type):
    rows = [
        item("pgp-support", "pgp", "unique-key"),
        item("wallet-support", "wallet", "private-wallet"),
        item("conflict", contradiction_type, "verified-conflict", direction="contradict", severity="strong"),
    ]
    result = ReliabilityEngine().assess({}, {}, rows, now=NOW)
    assert result["decision"] == "ABSTAIN"
    assert result["abstain_reason"] == "CONTESTED"
    assert "STRONG_CONTRADICTION_VETO" in result["gates_triggered"]


def test_three_gate_reasons_and_supported_case():
    engine = ReliabilityEngine()
    insufficient = engine.assess({}, {}, [item("only", "pgp", "one")], now=NOW)
    contested = engine.assess({}, {}, [
        item("a", "pgp", "key"), item("b", "wallet", "wallet"),
        item("c", "temporal", "impossible", direction="contradict", severity="strong"),
    ], now=NOW)
    tainted = engine.assess({}, {}, [
        item("a", "pgp", "key", deception_flags=["COPIED_IDENTIFIER"]),
        item("b", "wallet", "wallet", deception_flags=["LOW_RELIABILITY_SOURCE"]),
    ], now=NOW)
    supported = engine.assess({}, {}, [
        item("a", "pgp", "unique-key"), item("b", "wallet", "private-wallet")
    ], now=NOW)
    assert insufficient["abstain_reason"] == "INSUFFICIENT"
    assert contested["abstain_reason"] == "CONTESTED"
    assert tainted["abstain_reason"] == "TAINTED"
    assert supported["decision"] == "SUPPORTED"


def test_breakdown_sums_and_config_changes_output():
    config = load_config()
    rows = [item("a", "pgp", "key"), item("b", "wallet", "wallet")]
    first = ReliabilityEngine(config).assess({}, {}, rows, now=NOW)
    assert first["support"] == pytest.approx(sum(row["weight"] for row in first["items"] if row["direction"] == "support"))

    changed = deepcopy(config)
    changed["base_weights"]["pgp"] = 0.1
    second = ReliabilityEngine(changed).assess({}, {}, rows, now=NOW)
    assert second["support"] < first["support"]


def test_degraded_mode_caps_high_confidence():
    result = ReliabilityEngine().assess({}, {}, [
        item("a", "pgp", "key"), item("b", "wallet", "wallet"), item("c", "handle", "rare")
    ], degraded=True, now=NOW)
    assert result["confidence_band"] != "HIGH"
    assert "DEGRADED_MODEL" in result["gates_triggered"]


def test_response_contract_is_always_complete():
    result = ReliabilityEngine().assess({}, {}, [], now=NOW)
    assert {
        "decision", "abstain_reason", "confidence_band", "support",
        "contradiction", "items", "gates_triggered", "degraded",
    }.issubset(result)
    assert result["decision"] == "ABSTAIN"


def test_multiple_models_over_one_corpus_are_not_independent_sources():
    engine = ReliabilityEngine()
    actor_a = {"id": "a", "texts": ["x" * 300], "timestamps": ["2025-01-01T10:00:00"]}
    actor_b = {"id": "b", "texts": ["x" * 300], "timestamps": ["2025-01-02T10:00:00"]}
    rows = engine.build_evidence_items(actor_a, actor_b, {
        "semantic": 0.95, "stylometric": 0.95, "behavioural": 0.95, "handle": 0.0,
    })
    result = engine.assess(actor_a, actor_b, rows, now=NOW)
    assert result["independent_origins"] == 1
    assert result["decision"] == "ABSTAIN"
