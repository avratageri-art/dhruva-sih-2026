"""
seed_db_sqlite.py — Seeds the SQLite database with synthetic DARKTRACE demo data.
Run from the project root: python scripts/seed_db_sqlite.py
"""
import os
import sys
import random
from datetime import datetime, timedelta

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# ── Path setup ─────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BACKEND_DIR = os.path.join(PROJECT_ROOT, 'backend')

# Add backend to path FIRST so app.* imports resolve
sys.path.insert(0, BACKEND_DIR)

# Override DATABASE_URL to point at the backend's DB regardless of cwd
os.environ.setdefault('DATABASE_URL', f'sqlite:///{os.path.join(BACKEND_DIR, "darktrace.db")}')
# Provide dummy values for required neo4j settings so Settings() doesn't fail
os.environ.setdefault('NEO4J_URI', 'bolt://localhost:7687')
os.environ.setdefault('NEO4J_USERNAME', 'neo4j')
os.environ.setdefault('NEO4J_PASSWORD', 'DHRUVA_DEMO_ONLY_NOT_A_SECRET')

from app.database import engine, SessionLocal, Base
from app.models.actor import Actor, Handle, PGPIdentifier, Wallet
from app.models.intelligence import Post, OnionService, Domain, InfrastructureIndicator, Intelligence
from app.models.analysis import Source, Relationship, AttributionAssessment

# ─── Create all tables ────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

db = SessionLocal()

def rand_date(start_days_ago=730, end_days_ago=0):
    days = random.randint(end_days_ago, start_days_ago)
    return datetime.utcnow() - timedelta(days=days)

def generate_pgp():
    suffix = "".join(random.choices("0123456789ABCDEF", k=12))
    return f"DEMO_PGP_FINGERPRINT_{suffix}_NOT_VALID"

def generate_wallet(blockchain="BTC"):
    suffix = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=12))
    return f"DEMO_{blockchain}_WALLET_{suffix}_NOT_VALID"

def generate_onion():
    suffix = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=12))
    return f"demo-{suffix}.onion.invalid"

print("🌱 Seeding DARKTRACE demo database...")

# ─── Clear existing data ──────────────────────────────────────────────────────
print("  Clearing existing data...")
for model in [InfrastructureIndicator, Intelligence, Post, Domain, OnionService,
              AttributionAssessment, Relationship, Wallet, PGPIdentifier, Handle, Actor, Source]:
    db.query(model).delete()
db.commit()

# ─── Sources ──────────────────────────────────────────────────────────────────
print("  Creating sources...")
sources_data = [
    ("DarkMarket Forum", "forum", "tor://darkmarket.onion.invalid", 0.80),
    ("ExploitDB Forum", "forum", "tor://exploit-db.onion.invalid", 0.85),
    ("CryptoBazaar", "marketplace", "tor://cryptobazaar.onion.invalid", 0.75),
    ("0DayForum", "forum", "tor://0dayforum.onion.invalid", 0.90),
    ("Ransomwatch Feed", "osint", "https://ransomwatch.example.invalid", 0.95),
    ("TelegramMonitor", "messaging", "https://chat-monitor.example.invalid", 0.70),
    ("Paste Monitor", "osint", "https://paste-monitor.example.invalid", 0.60),
]
sources = []
for name, stype, ref, reliability in sources_data:
    s = Source(name=name, type=stype, reference=ref, reliability=reliability,
               collected_at=rand_date(30, 0))
    db.add(s)
    sources.append(s)
db.commit()
for s in sources:
    db.refresh(s)
print(f"  ✓ {len(sources)} sources created")

# ─── Actors ──────────────────────────────────────────────────────────────────
print("  Creating threat actors...")
actors_data = [
    ("ShadowFox",    "Ransomware Operator",  "Sophisticated ransomware operator specializing in double-extortion. Known to target healthcare and financial sectors. UTC+3 timezone signature.", "ACTIVE",   0.94),
    ("ZeroByte",     "Exploit Developer",    "Elite vulnerability researcher selling zero-day exploits. Suspected to have nation-state affiliation. Highly OPSEC-aware.", "ACTIVE",   0.87),
    ("CrimsonAdmin", "Data Broker",          "Large-scale stolen data broker operating across multiple darknet markets. Deals in financial data and PII dumps.", "ACTIVE",   0.82),
    ("NullRoot",     "Access Broker",        "Specializes in selling initial access to compromised enterprise networks. Primarily targets APAC region.", "ACTIVE",   0.79),
    ("PhantomStrike","DDoS-for-Hire",        "Operates a botnet-based DDoS service. Known for aggressive advertising and occasional data theft.", "ACTIVE",   0.76),
    ("DarkNinja",    "Carding Operator",     "High-volume carding operator. Maintains a semi-automated fraud infrastructure for card-not-present fraud.", "INACTIVE", 0.71),
    ("GhostNet",     "C2 Infrastructure",    "Operates shared command-and-control infrastructure rented to other threat actors. No direct criminal activity detected.", "ACTIVE",   0.68),
    ("RogueAdmin",   "Insider Threat",       "Former IT administrator suspected of facilitating access to former employer's systems. Limited corroborating evidence.", "SUSPECTED",0.55),
    ("XHax",         "Script Kiddie",        "Low-sophistication actor using commodity malware and publicly available exploits. Limited threat.", "INACTIVE", 0.42),
    ("AnonymousSec", "Hacktivist",           "Hacktivist collective targeting government and financial institutions. Politically motivated. Varying capability levels.", "ACTIVE",   0.63),
]
actors = []
for name, cat, desc, status, conf in actors_data:
    a = Actor(
        actor_name=name, category=cat, description=desc, status=status, confidence=conf,
        first_seen=rand_date(900, 400), last_seen=rand_date(30, 0),
    )
    db.add(a)
    actors.append(a)
db.commit()
for a in actors:
    db.refresh(a)
print(f"  ✓ {len(actors)} actors created")

# ─── Handles ─────────────────────────────────────────────────────────────────
print("  Creating handles...")
handles_data = [
    # ShadowFox
    (0, "@shadow_fox99",   "DarkMarket Forum", 0),
    (0, "@sf_exploit",     "ExploitDB Forum",  1),
    (0, "ShadowFox_RaaS",  "CryptoBazaar",     2),
    (0, "shadow.fox",      "TelegramMonitor",  5),
    # ZeroByte
    (1, "0xByte",          "ExploitDB Forum",  1),
    (1, "ZeroDay_Dev",     "0DayForum",        3),
    (1, "@zerobyte_off",   "TelegramMonitor",  5),
    # CrimsonAdmin
    (2, "crimson_dump",    "DarkMarket Forum", 0),
    (2, "CrimsonData",     "CryptoBazaar",     2),
    (2, "c_admin_99",      "Paste Monitor",    6),
    # NullRoot
    (3, "nullroot_acc",    "0DayForum",        3),
    (3, "null_r00t",       "ExploitDB Forum",  1),
    # PhantomStrike
    (4, "phantom_ddos",    "DarkMarket Forum", 0),
    (4, "PhantomStrike_BZ","CryptoBazaar",     2),
    # DarkNinja
    (5, "dark_ninja_crd",  "CryptoBazaar",     2),
    (5, "DarkNinja",       "DarkMarket Forum", 0),
    # GhostNet
    (6, "ghostnet_c2",     "0DayForum",        3),
    # AnonymousSec
    (9, "anonsec_ops",     "TelegramMonitor",  5),
    (9, "AnonSec_Official","Paste Monitor",    6),
]
handles = []
for actor_idx, handle, platform, source_idx in handles_data:
    h = Handle(
        actor_id=actors[actor_idx].id,
        handle=handle, platform=platform,
        source_id=sources[source_idx].id,
        first_seen=rand_date(800, 200),
        last_seen=rand_date(60, 0),
    )
    db.add(h)
    handles.append(h)
db.commit()
print(f"  ✓ {len(handles)} handles created")

# ─── PGP Keys ────────────────────────────────────────────────────────────────
print("  Creating PGP identifiers...")
pgps = []
for i, a in enumerate(actors[:7]):
    for _ in range(random.randint(1, 3)):
        p = PGPIdentifier(
            actor_id=a.id,
            fingerprint=generate_pgp(),
            source_id=random.choice(sources).id,
            first_seen=rand_date(700, 300),
            last_seen=rand_date(90, 0),
        )
        db.add(p)
        pgps.append(p)
db.commit()
print(f"  ✓ {len(pgps)} PGP identifiers created")

# ─── Wallets ─────────────────────────────────────────────────────────────────
print("  Creating wallets...")
wallets = []
wallet_actor_map = [
    (0, "BTC"), (0, "XMR"), (0, "BTC"),
    (1, "ETH"), (1, "BTC"),
    (2, "BTC"), (2, "BTC"), (2, "ETH"),
    (3, "XMR"), (3, "BTC"),
    (4, "BTC"),
    (5, "BTC"), (5, "ETH"),
    (6, "ETH"),
]
for actor_idx, blockchain in wallet_actor_map:
    w = Wallet(
        actor_id=actors[actor_idx].id,
        address=generate_wallet(blockchain),
        blockchain=blockchain,
        source_id=random.choice(sources).id,
        first_seen=rand_date(600, 100),
        last_seen=rand_date(30, 0),
    )
    db.add(w)
    wallets.append(w)
db.commit()
print(f"  ✓ {len(wallets)} wallets created")

# ─── Posts ───────────────────────────────────────────────────────────────────
print("  Creating intelligence posts...")
post_templates = {
    "Ransomware Operator": [
        "Synthetic victim scenario posted. {days}h exercise timer. Invalid BTC marker only.",
        "RaaS affiliates - 20% commission. Contact via jabber only.",
        "Selling access to encrypted corp network. 5 figure ransom potential.",
        "Decryptor ready. Pay within {days}h to restore your files.",
        "New strain deployment successful. AV detection rate: 0/67.",
    ],
    "Exploit Developer": [
        "Synthetic exploit exercise - {product} RCE scenario - no working code.",
        "PoC ready. Tested against latest patch. Interested parties DM.",
        "Buying RCE exploits for web apps. 5-figure budget. Escrow available.",
        "Technical writeup posted on private forum. Members only.",
        "New LPE found in {product} - combining with existing N-day.",
    ],
    "Data Broker": [
        "Fabricated bank-record exercise x{count}k - no real PII. Demo pricing.",
        "Selling {country} cards with PIN. 80% valid rate guaranteed.",
        "Premium credit pack - Visa Infinite x500. Tested working.",
        "New database drop: {company} - {count}M records. PII+financial.",
        "Cards refreshed daily. Auto shop running 24/7.",
    ],
    "Access Broker": [
        "Synthetic VPN access - {country} Acme Labs. Lab directory available.",
        "Demo RDP access x3 - fictional clinic. {count}k simulated endpoints.",
        "Training shell - fictional finance lab - {country}. Isolated environment.",
        "New batch of accesses. 10% off for bulk purchase. DM for details.",
        "Selling domain admin credentials - medium enterprise. TOR only.",
    ],
    "DDoS-for-Hire": [
        "Layer 7 DDoS starting at $50/day. Amplification available.",
        "Booter updated. New reflection vectors. Gbps capacity increased.",
        "Taking contracts. Up to 2Tbps. Payment in XMR only.",
        "Stresser test: {target} down for 4 hours. Proof available.",
        "Free trial - 10 minutes. Join channel for full service.",
    ],
}

posts = []
platforms_list = ["DarkMarket Forum", "ExploitDB Forum", "CryptoBazaar", "0DayForum"]
for a in actors:
    template_list = post_templates.get(a.category, [
        "New activity detected from this actor.",
        "Contact via secure channel for details.",
        "Updates coming soon. Stay tuned.",
    ])
    for i in range(random.randint(8, 18)):
        template = random.choice(template_list).format(
            days=random.randint(24, 96),
            product=random.choice(["AcmeOS", "DemoBrowser", "ExampleServer", "LabProxy", "SampleVM"]),
            count=random.randint(1, 100),
            country=random.choice(["US", "UK", "DE", "AU", "CA", "FR"]),
            company=random.choice(["TechCorp", "HealthNet", "FinBank", "GlobalLogistics"]),
            target=random.choice(["target-site.example.invalid", "bank-portal.example.invalid", "gov-portal.example.invalid"]),
        )
        p = Post(
            actor_id=a.id,
            platform=random.choice(platforms_list),
            content=template,
            timestamp=rand_date(500, 0),
            language="en",
            source_id=random.choice(sources).id,
        )
        db.add(p)
        posts.append(p)
db.commit()
print(f"  ✓ {len(posts)} posts created")

# ─── Onion Services ──────────────────────────────────────────────────────────
print("  Creating onion services...")
onion_templates = [
    ("DarkMarket v4",        "ACTIVE",   {"type": "marketplace", "listings": 12400}),
    ("ExploitDB Forum",      "ACTIVE",   {"type": "forum", "members": 8900}),
    ("CryptoBazaar",         "ACTIVE",   {"type": "marketplace", "listings": 6700}),
    ("Shadow RaaS Panel",    "ACTIVE",   {"type": "raas_panel", "affiliates": 47}),
    ("ZeroByte Private Hub", "ACTIVE",   {"type": "private_forum", "invite_only": True}),
    ("NullRoot Escrow",      "ACTIVE",   {"type": "escrow_service", "transactions": 892}),
    ("Ghost C2 Dashboard",   "ACTIVE",   {"type": "c2_panel", "bots": 15420}),
    ("AnonymousSec Leak",    "ACTIVE",   {"type": "leak_site", "total_leaks": 234}),
    ("CardShop Pro",         "OFFLINE",  {"type": "carding_shop", "takedown": "2024-03"}),
    ("StresserHub",          "ACTIVE",   {"type": "booter_service", "clients": 1240}),
    ("PGP Keyserver Dark",   "ACTIVE",   {"type": "key_server", "keys": 34200}),
    ("IntelForum Premium",   "INACTIVE", {"type": "forum", "note": "migrated"}),
]
onion_services = []
for title, status, meta in onion_templates:
    s = OnionService(
        address=generate_onion(),
        title=title,
        status=status,
        metadata_=meta,
        first_seen=rand_date(1000, 300),
        last_seen=rand_date(10, 0) if status != "OFFLINE" else rand_date(400, 200),
        source_id=random.choice(sources).id,
    )
    db.add(s)
    onion_services.append(s)
db.commit()
for s in onion_services:
    db.refresh(s)
print(f"  ✓ {len(onion_services)} onion services created")

# ─── Infrastructure Indicators ───────────────────────────────────────────────
print("  Creating infrastructure indicators...")
indicator_types = ["IP_ADDRESS", "HOSTING_ASN", "TLS_CERT_HASH", "SERVER_BANNER", "FAVICON_HASH"]
indicators = []
for service in onion_services[:8]:
    for _ in range(random.randint(2, 5)):
        ind_type = random.choice(indicator_types)
        if ind_type == "IP_ADDRESS":
            prefix = random.choice(["192.0.2", "198.51.100", "203.0.113"])
            value = f"{prefix}.{random.randint(1, 254)}"
        elif ind_type == "HOSTING_ASN":
            value = f"AS{random.randint(64496, 64511)}"
        elif ind_type == "TLS_CERT_HASH":
            value = "".join(random.choices("0123456789abcdef", k=64))
        elif ind_type == "SERVER_BANNER":
            value = random.choice(["Apache/2.4.41", "nginx/1.18.0", "lighttpd/1.4.55"])
        else:
            value = "".join(random.choices("0123456789abcdef", k=16))

        i = InfrastructureIndicator(
            service_id=service.id,
            indicator_type=ind_type,
            value=value,
            confidence=round(random.uniform(0.6, 0.98), 2),
            observed_at=rand_date(200, 0),
            source_id=random.choice(sources).id,
        )
        db.add(i)
        indicators.append(i)
db.commit()
print(f"  ✓ {len(indicators)} infrastructure indicators created")

# ─── Domains ─────────────────────────────────────────────────────────────────
print("  Creating domains...")
domain_entries = [
    ("shadowfox-raas.example.invalid", 0), ("sf-decrypt.example.invalid", 0), ("sf-exfil-data.example.invalid", 0),
    ("zerobyte-exploits.example.invalid", 1), ("zb-private.example.invalid", 1),
    ("crimsondata-market.example.invalid", 2), ("cda-autoshop.example.invalid", 2),
    ("nullroot-access.example.invalid", 3),
    ("phantom-stresser.example.invalid", 4),
    ("ghost-c2.example.invalid", 6),
]
domains = []
for domain_name, actor_idx in domain_entries:
    d = Domain(
        domain=domain_name,
        actor_id=actors[actor_idx].id,
        source_id=random.choice(sources).id,
    )
    db.add(d)
    domains.append(d)
db.commit()
print(f"  ✓ {len(domains)} domains created")

# ─── Attribution Assessments (Computed with actual sentence-transformers AI model) ───
print("  Running AI attribution engine on actor pairs...")
from app.services.ai.attribution import attribution_engine

assessment_pair_indices = [(0, 1), (2, 5), (3, 6), (0, 4), (1, 3), (9, 4)]
assessments = []

for a_idx, b_idx in assessment_pair_indices:
    act_a = actors[a_idx]
    act_b = actors[b_idx]
    
    # Gather real generated posts, timestamps, handles, wallets, PGPs
    act_a_posts = [p for p in posts if p.actor_id == act_a.id]
    act_b_posts = [p for p in posts if p.actor_id == act_b.id]
    act_a_handles = [h.handle for h in handles if h.actor_id == act_a.id]
    act_b_handles = [h.handle for h in handles if h.actor_id == act_b.id]
    act_a_wallets = [w.address for w in wallets if w.actor_id == act_a.id]
    act_b_wallets = [w.address for w in wallets if w.actor_id == act_b.id]
    act_a_pgps = [p.fingerprint for p in pgps if p.actor_id == act_a.id]
    act_b_pgps = [p.fingerprint for p in pgps if p.actor_id == act_b.id]

    # For known related pairs, add some shared infrastructure / cross-posting correlation
    if (a_idx, b_idx) == (0, 1):  # ShadowFox and ZeroByte
        # Shared PGP / wallet connection as noted in intelligence
        act_b_wallets.append(act_a_wallets[0] if act_a_wallets else "DEMO_BTC_WALLET_SHARED_FALLBACK_NOT_VALID")
        graph_score = 0.85
    elif (a_idx, b_idx) == (3, 6):  # NullRoot and GhostNet
        graph_score = 0.80
    else:
        graph_score = 0.10

    actor_a_data = {
        "texts": [p.content for p in act_a_posts],
        "timestamps": [p.timestamp.isoformat() for p in act_a_posts if p.timestamp],
        "handles": act_a_handles,
        "wallets": act_a_wallets,
        "pgps": act_a_pgps,
        "graph_score": graph_score,
    }
    actor_b_data = {
        "texts": [p.content for p in act_b_posts],
        "timestamps": [p.timestamp.isoformat() for p in act_b_posts if p.timestamp],
        "handles": act_b_handles,
        "wallets": act_b_wallets,
        "pgps": act_b_pgps,
        "graph_score": graph_score,
    }

    # Execute actual AI model pipeline
    score_pct, label, explanation = attribution_engine.assess_attribution(actor_a_data, actor_b_data)
    subsystem_scores = attribution_engine.get_subsystem_scores(actor_a_data, actor_b_data)
    norm_score = round(score_pct / 100.0, 4)

    evidence = {
        "semantic_similarity": subsystem_scores.get("semantic", 0),
        "stylometric_similarity": subsystem_scores.get("stylometric", 0),
        "behavioural_similarity": subsystem_scores.get("behavioural", 0),
        "handle_overlap": subsystem_scores.get("handle", 0),
        "graph_correlation": subsystem_scores.get("graph", 0),
        "texts_compared": len(act_a_posts) + len(act_b_posts),
        "model": subsystem_scores.get("model", "sentence-transformers/all-MiniLM-L6-v2"),
        "model_loaded": subsystem_scores.get("model_loaded", True),
        "ai_powered": True,
    }

    aa = AttributionAssessment(
        actor_a=act_a.id,
        actor_b=act_b.id,
        score=norm_score,
        confidence_level=label,
        explanation=explanation,
        evidence_json=evidence,
        negative_evidence_json={"timezone_mismatch": norm_score < 0.65, "different_platforms": norm_score < 0.55},
        created_at=rand_date(60, 0),
    )
    db.add(aa)
    assessments.append(aa)
    print(f"    Assessment {act_a.actor_name} ↔ {act_b.actor_name}: {score_pct:.1f}% [{label}] via AI model")

db.commit()
print(f"  ✓ {len(assessments)} real AI-evaluated attribution assessments created")


# ─── Relationships ────────────────────────────────────────────────────────────
print("  Creating entity relationships...")
rel_data = [
    ("actor", actors[0].id, "USES_INFRASTRUCTURE", "onion_service", onion_services[3].id, 0.92),
    ("actor", actors[1].id, "USES_INFRASTRUCTURE", "onion_service", onion_services[4].id, 0.88),
    ("actor", actors[3].id, "USES_INFRASTRUCTURE", "onion_service", onion_services[6].id, 0.85),
    ("actor", actors[0].id, "POSSIBLE_SAME_ACTOR",  "actor", actors[1].id, 0.88),
    ("actor", actors[2].id, "POSSIBLE_SAME_ACTOR",  "actor", actors[5].id, 0.71),
    ("actor", actors[3].id, "COLLABORATES_WITH",    "actor", actors[6].id, 0.83),
    ("actor", actors[0].id, "TRANSACTION",          "actor", actors[2].id, 0.75),
]
for src_type, src_id, rel_type, tgt_type, tgt_id, conf in rel_data:
    r = Relationship(
        source_entity_type=src_type, source_entity_id=src_id,
        relationship_type=rel_type,
        target_entity_type=tgt_type, target_entity_id=tgt_id,
        confidence=conf,
        evidence={"method": "multi-source correlation"},
    )
    db.add(r)
db.commit()
print(f"  ✓ {len(rel_data)} relationships created")

# ─── Summary ─────────────────────────────────────────────────────────────────
print("\n✅ Database seeded successfully!")
print(f"   Actors:          {len(actors)}")
print(f"   Handles:         {len(handles)}")
print(f"   PGP Keys:        {len(pgps)}")
print(f"   Wallets:         {len(wallets)}")
print(f"   Posts:           {len(posts)}")
print(f"   Onion Services:  {len(onion_services)}")
print(f"   Indicators:      {len(indicators)}")
print(f"   Domains:         {len(domains)}")
print(f"   Assessments:     {len(assessments)}")
print(f"   Relationships:   {len(rel_data)}")
print(f"\n   API:      http://localhost:8000/docs")
print(f"   Frontend: http://localhost:5173")

db.close()
