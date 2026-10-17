"""Reproducible synthetic evaluation for baseline vs reliability gating.

Usage: python scripts/evaluate.py
The benchmark is synthetic and demonstrates failure-mode handling; it is not a
claim of real-world attribution accuracy.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.ai.reliability import ReliabilityEngine  # noqa: E402


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def evidence(case_id, suffix, kind, value, **extra):
    return {
        "evidence_id": f"{case_id}-{suffix}",
        "type": kind,
        "subject_a": f"{case_id}-a",
        "subject_b": f"{case_id}-b",
        "value": value,
        "quality": 1.0,
        "rarity": 1.0,
        **extra,
    }


def build_benchmark(seed=26151):
    rng = random.Random(seed)
    cases = []

    def add_family(family, count, truth, baseline_range, factory):
        for index in range(count):
            case_id = f"{family}-{index + 1:02d}"
            cases.append({
                "id": case_id,
                "family": family,
                "same_actor": truth,
                "baseline_score": round(rng.uniform(*baseline_range), 2),
                "evidence": factory(case_id, index),
            })

    add_family("true_strong", 12, True, (78, 96), lambda cid, i: [
        evidence(cid, "pgp", "pgp", f"unique-key-{i}", quality=0.7 + (i % 4) * 0.1),
        evidence(cid, "wallet", "wallet", f"private-wallet-{i}", quality=0.7 + (i % 4) * 0.1),
    ])
    add_family("shared_hosting", 8, False, (70, 91), lambda cid, i: [
        evidence(cid, "infra-a", "infra", f"cloudflare-shared-{i}", shared=True),
        evidence(cid, "infra-b", "infra", f"amazonaws.com-{i}", shared=True),
    ])
    add_family("copied_posts", 7, False, (72, 92), lambda cid, i: [
        evidence(cid, "copy-a", "semantic", f"Mirrored long announcement number {i} with the same signing phrase and content."),
        evidence(cid, "copy-b", "semantic", f"Mirrored long announcement number {i} with the same signing phrase and content."),
        evidence(cid, "copy-c", "semantic", f"Mirrored long announcement number {i} with the same signing phrase and content.!"),
    ])
    add_family("common_handle", 7, False, (66, 84), lambda cid, i: [
        evidence(cid, "handle", "handle", "admin", rarity=0.03),
        evidence(cid, "handle-2", "handle", "root", rarity=0.03),
    ])
    add_family("impersonation", 7, False, (82, 97), lambda cid, i: [
        evidence(cid, "key", "pgp", f"copied-key-{i}", deception_flags=["COPIED_IDENTIFIER"]),
        evidence(cid, "handle", "handle", f"lookalike-{i}", deception_flags=["LATER_CREATED_LOOKALIKE"]),
    ])
    add_family("conflicting", 7, False, (75, 94), lambda cid, i: [
        evidence(cid, "pgp", "pgp", f"key-{i}"),
        evidence(cid, "wallet", "wallet", f"wallet-{i}"),
        evidence(cid, "conflict", "temporal", "simultaneous-exclusive-control", direction="contradict", severity="strong", quality=0.65),
    ])
    add_family("same_community_writing", 7, False, (68, 88), lambda cid, i: [
        evidence(cid, "semantic", "semantic", f"topic-score-{i}", quality=0.9, rarity=0.4),
        evidence(cid, "style", "stylometry", f"style-score-{i}", quality=0.8, rarity=0.4),
    ])
    add_family("true_weak", 5, True, (45, 63), lambda cid, i: [
        evidence(cid, "handle", "handle", f"weak-handle-{i}", quality=0.7, rarity=0.5),
    ])
    return cases


def safe_div(numerator, denominator):
    return numerator / denominator if denominator else 0.0


def metrics(rows, prediction_key):
    asserted = [row for row in rows if row[prediction_key]]
    tp = sum(row["same_actor"] and row[prediction_key] for row in rows)
    fp = sum((not row["same_actor"]) and row[prediction_key] for row in rows)
    positives = sum(row["same_actor"] for row in rows)
    negatives = len(rows) - positives
    return {
        "precision": round(safe_div(tp, tp + fp), 4),
        "recall": round(safe_div(tp, positives), 4),
        "coverage": round(safe_div(len(asserted), len(rows)), 4),
        "abstention_rate": round(1 - safe_div(len(asserted), len(rows)), 4),
        "false_link_rate": round(safe_div(fp, negatives), 4),
        "true_positives": tp,
        "false_positives": fp,
    }


def run(seed=26151):
    engine = ReliabilityEngine()
    rows = []
    for case in build_benchmark(seed):
        result = engine.assess({}, {}, deepcopy(case["evidence"]), now=NOW)
        rows.append({
            **case,
            "baseline_supported": case["baseline_score"] >= 65,
            "engine_supported": result["decision"] == "SUPPORTED",
            "engine_support": result["support"],
            "decision": result["decision"],
            "abstain_reason": result["abstain_reason"],
        })

    by_family = {}
    for family in sorted({row["family"] for row in rows}):
        family_rows = [row for row in rows if row["family"] == family]
        by_family[family] = {
            "count": len(family_rows),
            "baseline_false_links": sum(not row["same_actor"] and row["baseline_supported"] for row in family_rows),
            "engine_false_links": sum(not row["same_actor"] and row["engine_supported"] for row in family_rows),
            "engine_supported": sum(row["engine_supported"] for row in family_rows),
            "dominant_reason": max(
                (reason for reason in {row["abstain_reason"] for row in family_rows} if reason),
                key=lambda reason: sum(row["abstain_reason"] == reason for row in family_rows),
                default=None,
            ),
        }

    curve = []
    for threshold in (0.8, 1.2, 1.4, 1.55, 1.7):
        selected = [row for row in rows if row["decision"] == "SUPPORTED" and row["engine_support"] >= threshold]
        tp = sum(row["same_actor"] for row in selected)
        curve.append({
            "minimum_support": threshold,
            "coverage": round(safe_div(len(selected), len(rows)), 4),
            "precision": round(safe_div(tp, len(selected)), 4),
        })

    ablations = {}
    for component in ("independence", "rarity", "shared_discount", "veto"):
        ablation_rows = []
        for case in build_benchmark(seed):
            result = engine.assess({}, {}, deepcopy(case["evidence"]), now=NOW, disabled_components=[component])
            ablation_rows.append({**case, "engine_supported": result["decision"] == "SUPPORTED"})
        ablations[f"without_{component}"] = metrics(ablation_rows, "engine_supported")

    return {
        "benchmark": {"seed": seed, "cases": len(rows), "synthetic": True},
        "baseline": metrics(rows, "baseline_supported"),
        "reliability_engine": metrics(rows, "engine_supported"),
        "per_family": by_family,
        "precision_coverage_curve": curve,
        "ablations": ablations,
    }


def markdown(result):
    lines = [
        "# Synthetic reliability benchmark",
        "",
        "> Caveat: this benchmark is synthetic and tests known failure modes. It does not estimate real-world attribution accuracy.",
        "",
        "| Model | Precision | Recall | Coverage | False-link rate |",
        "|---|---:|---:|---:|---:|",
    ]
    for label, key in (("Similarity baseline", "baseline"), ("Reliability engine", "reliability_engine")):
        row = result[key]
        lines.append(f"| {label} | {row['precision']:.1%} | {row['recall']:.1%} | {row['coverage']:.1%} | {row['false_link_rate']:.1%} |")
    lines += ["", "## Failure-family breakdown", "", "| Family | Cases | Baseline false links | Engine false links | Engine supported | Dominant abstention |", "|---|---:|---:|---:|---:|---|"]
    for family, row in result["per_family"].items():
        lines.append(f"| {family} | {row['count']} | {row['baseline_false_links']} | {row['engine_false_links']} | {row['engine_supported']} | {row['dominant_reason'] or '—'} |")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=26151)
    parser.add_argument("--json", type=Path, default=ROOT / "data" / "evaluation" / "results.json")
    parser.add_argument("--markdown", type=Path, default=ROOT / "docs" / "evaluation" / "results.md")
    args = parser.parse_args()
    result = run(args.seed)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(markdown(result), encoding="utf-8")
    print(markdown(result))


if __name__ == "__main__":
    main()
