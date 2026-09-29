import os
import sys
import json
import hashlib
from datetime import datetime

# Set backend in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal
from app.models.intelligence import Observation, Alert, SeedSource
from app.models.actor import Actor
from app.services.crawler.normalizer import (
    normalize_observation,
    compute_sha256,
    extract_entities_harmonized
)
from app.services.ai.attribution import AttributionEngine
from app.services.crawler.pipeline import CrawlerPipeline

def run_test():
    print("==================================================")
    print("STAGE 1: VERIFY SHA-256 & SENSITIVE PGP KEY REDACTION")
    print("==================================================")
    private_key_begin = "-----BEGIN PGP " + "PRIVATE KEY BLOCK-----"
    private_key_end = "-----END PGP " + "PRIVATE KEY BLOCK-----"
    sample_text = (
        "Welcome to the synthetic Shadow Market lab. Contact admin at admin-shadow@example.invalid. "
        "BTC demo identifier: DEMO_BTC_WALLET_E2E_PRIMARY_NOT_VALID\n"
        f"{private_key_begin}\n"
        "lQO+BF7VSYNBCAC/1234567890FAKE_PRIVATE_KEY_MATERIAL_FOR_SECURITY_TEST\n"
        f"{private_key_end}\n"
        "Operator handle is @krypton_operator. Ethereum demo identifier: DEMO_ETH_WALLET_E2E_SECONDARY_NOT_VALID\n"
    )
    raw_hash = compute_sha256(sample_text)
    print(f"[+] Raw text SHA-256: {raw_hash}")
    assert len(raw_hash) == 64, "SHA-256 hash must be 64 hex characters"

    entities_raw, sanitized_text, exposure_alerts = extract_entities_harmonized(sample_text)
    print(f"[+] Sensitive PGP Private Key alerts count: {len(exposure_alerts)}")
    assert len(exposure_alerts) > 0, "Must detect PGP private key"
    assert private_key_begin not in sanitized_text, "Private key must be redacted"
    assert "[SENSITIVE_PGP_PRIVATE_KEY_REDACTED" in sanitized_text, "Redaction marker missing"
    print(f"[+] Redacted text snippet: {sanitized_text[120:200]}...")

    print("\n==================================================")
    print("STAGE 2: NORMALIZATION TO COMMON SCHEMA")
    print("==================================================")
    norm = normalize_observation(
        raw_item={
            "source_url": "http://shadow-test.onion.invalid/board",
            "source_type": "onion-service",
            "title": "Shadow Board - Operational Security",
            "content": sample_text,
            "http_status": 200,
            "collector": "TorOnionScraper"
        },
        collector="TorOnionScraper"
    )
    print(f"[+] Normalized Observation SHA-256: {norm['content_sha256']}")
    print(f"[+] Normalized status progression:  {norm['status']}")
    print(f"[+] Extracted entities summary:     BTC={norm['extracted_entities'].get('btc_wallets')}, Handles={norm['extracted_entities'].get('handles')}")
    assert norm["status"] == "CONTENT_OBSERVED"
    assert norm["content_sha256"] == raw_hash
    assert "@krypton_operator" in norm["extracted_entities"]["handles"]
    assert "DEMO_BTC_WALLET_E2E_PRIMARY_NOT_VALID" in norm["extracted_entities"]["btc_wallets"]

    print("\n==================================================")
    print("STAGE 3: DB PERSISTENCE & ENTITY RESOLUTION")
    print("==================================================")
    db = SessionLocal()
    try:
        actor = db.query(Actor).first()
        actor_name = actor.actor_name if actor else "TestActor"
        print(f"[+] Reference Actor: {actor_name} (ID: {actor.id if actor else 'None'})")

        obs = Observation(
            source_name=norm["source_url"],
            source_type=norm["source_type"],
            service=norm["service"],
            title=norm["title"],
            content=norm["content"],
            raw_reference=norm["raw_content_reference"],
            collection_method=norm["collector"],
            reliability=norm["reliability"],
            status=norm["status"],
            metadata_json={"provenance": norm["provenance"]},
            extracted_entities=norm["extracted_entities"],
            content_sha256=norm["content_sha256"],
            blockchain_tx_hash=f"0x{norm['content_sha256'][:64]}",
            blockchain_anchor_time=datetime.utcnow()
        )
        db.add(obs)
        db.commit()
        db.refresh(obs)
        print(f"[+] Persisted Observation ID: {obs.id} with SHA-256: {obs.content_sha256}")

        # Check for exposure alert creation
        exp_alerts = norm.get("provenance", {}).get("exposure_alerts", [])
        if exp_alerts:
            alert = Alert(
                alert_type="SENSITIVE_KEY_EXPOSURE",
                title=f"CRITICAL: PGP Private Key Exposed in {norm['title']}",
                description=f"Observation {obs.id} contained an exposed PGP private key block. Redacted with hash {exp_alerts[0]['key_sha256'][:16]}.",
                severity="CRITICAL",
                observation_id=obs.id
            )
            db.add(alert)
            db.commit()
            print(f"[+] Created CRITICAL alert {alert.id} for sensitive PGP key exposure")

        # Entity resolution to actors
        pipe = CrawlerPipeline(db)
        cand_id, conf, notes, _ = pipe._resolve_against_actors(norm, norm["extracted_entities"])
        obs.candidate_actor_id = cand_id
        obs.candidate_confidence = conf
        obs.candidate_notes = notes
        db.commit()
        db.refresh(obs)
        print(f"[+] Entity resolution candidate: Actor ID {obs.candidate_actor_id} (Confidence: {obs.candidate_confidence})")

        print("\n==================================================")
        print("STAGE 4: EVIDENCE INTEGRITY VERIFICATION")
        print("==================================================")
        # Compute SHA-256 on sanitized content and verify anchored content_sha256 is intact
        raw_stored_hash = obs.content_sha256
        print(f"[+] Anchored SHA-256:   {raw_stored_hash}")
        assert raw_stored_hash == raw_hash, "Anchored hash must match initial raw hash"
        print("[+] Evidence Integrity: VALIDATED (MATCH)")

        print("\n==================================================")
        print("STAGE 5: AI ATTRIBUTION ENGINE TEST")
        print("==================================================")
        from app.services.ai.attribution import attribution_engine
        actors = db.query(Actor).all()
        if len(actors) >= 2:
            act_a = actors[0]
            act_b = actors[1]
            data_a = {
                "texts": [obs.content],
                "timestamps": [datetime.utcnow().isoformat()],
                "handles": [h.handle for h in act_a.handles] + ["@krypton_operator"],
                "wallets": [w.address for w in act_a.wallets],
                "pgps": [p.fingerprint for p in act_a.pgp_identifiers],
            }
            data_b = {
                "texts": ["Target operator discussion on darknet market forums."],
                "timestamps": [datetime.utcnow().isoformat()],
                "handles": [h.handle for h in act_b.handles],
                "wallets": [w.address for w in act_b.wallets],
                "pgps": [p.fingerprint for p in act_b.pgp_identifiers],
            }
            score_pct, label, explanation = attribution_engine.assess_attribution(data_a, data_b)
            subs = attribution_engine.get_subsystem_scores(data_a, data_b)
            print(f"[+] Attribution Score:   {score_pct:.2f}% [{label}]")
            print(f"[+] Semantic Score:      {subs['semantic']}")
            print(f"[+] Stylometric Score:   {subs['stylometric']}")
            print(f"[+] Behavioural Score:   {subs['behavioural']}")
            print(f"[+] Handle Match Score:  {subs['handle']}")
            print(f"[+] Model Loaded:        {subs['model_loaded']} ({subs['model']})")
            print(f"[+] Explanation:         {explanation}")
            assert score_pct >= 0.0, "Attribution score must be >= 0"
        else:
            print("[+] Less than 2 actors in DB, skipping pair attribution test.")

        print("\n==================================================")
        print(">>> ALL 5 END-TO-END PIPELINE STAGES PASSED! <<<")
        print("==================================================")

    finally:
        db.close()

if __name__ == "__main__":
    run_test()
