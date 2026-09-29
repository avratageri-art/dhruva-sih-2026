"""
End-to-end test:
deepdarkCTI source → DarkTrace registry → Enable → Tor → Collect → Observation → AI → Alert → UI
"""
import sys, json
sys.path.insert(0, '.')

from datetime import datetime, timezone
from app.database import SessionLocal
from app.models.intelligence import SeedSource, Observation, Alert

db = SessionLocal()

# ── STEP 1: Pick a test source ────────────────────────────────────────────
# Choose any catalogue source explicitly marked ONLINE. This opt-in integration
# script does not embed or prefer a real-world operational endpoint.
test_source = db.query(SeedSource).filter(
    SeedSource.notes.like('%deepdarkCTI%'),
    SeedSource.notes.like('%catalogue_status=ONLINE%'),
    SeedSource.reference.like('%.onion%'),
).first()

# Final fallback: any clearnet source marked ONLINE
if not test_source:
    test_source = db.query(SeedSource).filter(
        SeedSource.notes.like('%deepdarkCTI%'),
        SeedSource.notes.like('%catalogue_status=ONLINE%'),
    ).first()

if not test_source:
    print("ERROR: No deepdarkCTI source found to test!")
    db.close()
    exit(1)

print(f"=== STEP 1: TEST SOURCE SELECTED ===")
print(f"  ID:        {test_source.id}")
print(f"  Name:      {test_source.name}")
print(f"  URL:       {test_source.reference}")
print(f"  Category:  {test_source.category}")
print(f"  Status:    {test_source.status} (pre-enable)")
print(f"  Notes:     {(test_source.notes or '')[:120]}")
print()

# ── STEP 2: Analyst enables the source ──────────────────────────────────
test_source.status = "ENABLED"
test_source.authorized = 1
db.commit()
print(f"=== STEP 2: SOURCE ENABLED BY ANALYST ===")
print(f"  Status:    {test_source.status}")
print()

# ── STEP 3: Run collection ──────────────────────────────────────────────
from app.services.crawler.deepdarkcti_collector import collect_one_source, check_tor_alive

tor_alive, proxy_url = check_tor_alive()
print(f"=== STEP 3: TOR STATUS ===")
print(f"  Tor alive: {tor_alive}")
print(f"  Proxy:     {proxy_url}")
print()

print(f"=== STEP 4: RUNNING COLLECTION ===")
result = collect_one_source(test_source, db)
print(f"  Collection status:  {result['status']}")
print(f"  HTTP status:        {result['http_status']}")
print(f"  Error:              {result.get('error')}")
print(f"  Observation ID:     {result.get('observation_id')}")
print(f"  Entities:           {result.get('entities_summary')}")
print(f"  New entities:       {result.get('new_entities')}")
print()

# ── STEP 5: Verify observation in DB ──────────────────────────────────
if result.get('observation_id'):
    obs = db.query(Observation).filter(Observation.id == result['observation_id']).first()
    if obs:
        print(f"=== STEP 5: OBSERVATION IN DATABASE ===")
        print(f"  Observation ID:       {obs.id}")
        print(f"  Source:               {obs.source_name}")
        print(f"  Collector:            {obs.collection_method}")
        print(f"  Collected At:         {obs.collected_at}")
        print(f"  Content SHA-256:      {obs.content_sha256}")
        print(f"  Blockchain TX Hash:   {obs.blockchain_tx_hash}")
        print(f"  Status:               {obs.status}")
        print(f"  Candidate Actor:      {obs.candidate_actor_id} (conf={obs.candidate_confidence})")
        print(f"  Extracted Entities:   {json.dumps({k: len(v) for k, v in (obs.extracted_entities or {}).items() if isinstance(v, list) and v})}")
        print()

# ── STEP 6: Check alerts ──────────────────────────────────────────────
alerts = db.query(Alert).filter(
    Alert.observation_id == result.get('observation_id')
).all() if result.get('observation_id') else []

print(f"=== STEP 6: ALERTS GENERATED ===")
print(f"  Alerts created: {len(alerts)}")
for a in alerts:
    print(f"  [{a.severity}] {a.alert_type}: {a.title}")
print()

# ── STEP 7: Seed status after collection ──────────────────────────────
db.refresh(test_source)
print(f"=== STEP 7: SEED STATUS AFTER COLLECTION ===")
print(f"  Final status:             {test_source.status}")
print(f"  Observation count:        {test_source.observation_count}")
print(f"  Error count:              {test_source.error_count}")
print()

print("=== END-TO-END TEST COMPLETE ===")
db.close()
