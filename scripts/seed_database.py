"""
DARKTRACE - Comprehensive Synthetic Demo Database Seeder
Creates the ShadowFox investigation scenario and supporting actors.
Run from darktrace root: python scripts/seed_database.py
"""
import os
import sys
import random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Must set env before importing app modules
os.environ.setdefault("DATABASE_URL", "sqlite:///./darktrace.db")
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_USERNAME", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "DHRUVA_DEMO_ONLY_NOT_A_SECRET")
os.environ.setdefault("MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
os.environ.setdefault("API_URL", "http://localhost:8000")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.actor import Actor, Handle, PGPIdentifier, Wallet
from app.models.intelligence import Post, OnionService, Domain, InfrastructureIndicator, Intelligence, SeedSource
from app.models.analysis import Source, Relationship, AttributionAssessment

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./darktrace.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(bind=engine)

def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("[+] Database reset and tables recreated.")

def seed():
    db = SessionLocal()
    try:
        # ===================== SOURCES =====================
        sources = [
            Source(name="DarkMarket Forum", type="forum", reference="synthetic://darkmarket", reliability=0.85),
            Source(name="ExploitDB Underground", type="forum", reference="synthetic://exploitdb", reliability=0.80),
            Source(name="TorLeaks Archive", type="archive", reference="synthetic://torleaks", reliability=0.70),
            Source(name="Pastebin Monitor", type="paste", reference="synthetic://pastebin", reliability=0.60),
            Source(name="OSINT Feed A", type="osint", reference="synthetic://osintvault", reliability=0.90),
            Source(name="CryptoTrace", type="blockchain", reference="synthetic://cryptotrace", reliability=0.95),
            Source(name="Hacker Forum B", type="forum", reference="synthetic://hackforum", reliability=0.75),
            Source(name="Ransomwatch", type="telemetry", reference="synthetic://ransomwatch", reliability=0.88),
        ]
        db.add_all(sources)
        db.commit()
        for s in sources: db.refresh(s)
        src = {s.name: s for s in sources}
        print(f"[+] Seeded {len(sources)} sources.")

        # ===================== CRAWLER SEED SOURCES =====================
        # Seed sources are loaded directly from fastfire/deepdarkCTI registry
        print("[+] Seed sources managed via deepdarkCTI integration.")


        # ===================== ACTORS =====================
        base_dt = datetime(2022, 1, 1)

        # === Actor 1: ShadowFox (Key actor for demo) ===
        shadowfox = Actor(
            actor_name="ShadowFox",
            category="Ransomware Operator",
            description=(
                "Threat actor persona observed across multiple dark web forums. "
                "Specializes in ransomware deployment and initial access brokering. "
                "Known for distinctive writing style and consistent operational security patterns."
            ),
            status="ACTIVE",
            first_seen=base_dt + timedelta(days=30),
            last_seen=base_dt + timedelta(days=900),
            confidence=0.94,
        )
        db.add(shadowfox)

        # === Actor 2: ZeroByte (Potential same actor) ===
        zerobyte = Actor(
            actor_name="ZeroByte",
            category="Initial Access Broker",
            description=(
                "Persona observed on ExploitDB Underground. Sells RDP access and VPN credentials. "
                "Stylometric analysis shows strong similarity to ShadowFox persona. "
                "Potential persona migration detected after DarkMarket takedown."
            ),
            status="ACTIVE",
            first_seen=base_dt + timedelta(days=400),
            last_seen=base_dt + timedelta(days=920),
            confidence=0.84,
        )
        db.add(zerobyte)

        # === Other actors for richness ===
        other_actors_data = [
            ("GhostNet", "Malware Developer", "ACTIVE", 0.75),
            ("CrimsonRoot", "Carding Operator", "ACTIVE", 0.68),
            ("PhantomBlade", "DDoS Operator", "INACTIVE", 0.55),
            ("NullAdmin", "Credential Broker", "ACTIVE", 0.82),
            ("DarkWolf", "Exploit Seller", "ACTIVE", 0.71),
            ("ShadowNet", "Infrastructure Provider", "SUSPECTED", 0.50),
            ("ByteKnight", "Ransomware Affiliate", "ACTIVE", 0.88),
            ("AnonStrike", "Hacktivism", "INACTIVE", 0.60),
            ("RogueBot", "Botnet Operator", "ACTIVE", 0.73),
            ("NightHax", "Data Broker", "ACTIVE", 0.65),
            ("XCypher", "Crypter Developer", "ACTIVE", 0.79),
            ("VoidSec", "Vulnerability Researcher", "ACTIVE", 0.85),
            ("GlitchRoot", "Webshell Distributor", "INACTIVE", 0.45),
            ("SerpentByte", "RAT Developer", "ACTIVE", 0.77),
            ("IronMask", "Money Mule Coordinator", "SUSPECTED", 0.58),
            ("CobraNet", "C2 Infrastructure", "ACTIVE", 0.83),
            ("ZeroSec", "Zero-Day Broker", "ACTIVE", 0.91),
            ("RedPhantom", "Ransomware Group", "ACTIVE", 0.87),
            ("NullByte47", "Forum Moderator", "ACTIVE", 0.62),
            ("DarkAdmin", "Marketplace Admin", "INACTIVE", 0.70),
            ("CipherGhost", "Encryption Specialist", "ACTIVE", 0.74),
            ("XRat99", "RAT Operator", "ACTIVE", 0.69),
            ("HexBlade", "Payload Developer", "ACTIVE", 0.78),
        ]
        other_actors = []
        for name, cat, status, conf in other_actors_data:
            a = Actor(
                actor_name=name, category=cat, status=status,
                confidence=conf,
                first_seen=base_dt + timedelta(days=random.randint(10, 500)),
                last_seen=base_dt + timedelta(days=random.randint(600, 950)),
                description=f"Synthetic threat actor persona observed on dark web forums. Category: {cat}."
            )
            db.add(a)
            other_actors.append(a)

        db.commit()
        db.refresh(shadowfox)
        db.refresh(zerobyte)
        for a in other_actors: db.refresh(a)
        all_actors = [shadowfox, zerobyte] + other_actors
        print(f"[+] Seeded {len(all_actors)} actors.")

        # ===================== PGP IDENTIFIERS =====================
        # CRITICAL: ShadowFox and ZeroByte share PGP key — this is main evidence
        shared_pgp_fp = "3A9F2B1C4D5E6F7A8B9C0D1E2F3A4B5C6D7E8F9A"
        
        pgp_shadowfox_1 = PGPIdentifier(
            fingerprint=shared_pgp_fp,
            actor_id=shadowfox.id,
            source_id=src["DarkMarket Forum"].id,
            first_seen=base_dt + timedelta(days=35),
            last_seen=base_dt + timedelta(days=650),
        )
        pgp_shadowfox_2 = PGPIdentifier(
            fingerprint="1B2C3D4E5F6A7B8C9D0E1F2A3B4C5D6E7F8A9B0C",
            actor_id=shadowfox.id,
            source_id=src["DarkMarket Forum"].id,
            first_seen=base_dt + timedelta(days=200),
            last_seen=base_dt + timedelta(days=900),
        )
        # ZeroByte uses the same PGP — key attribution link
        pgp_zerobyte_1 = PGPIdentifier(
            fingerprint=shared_pgp_fp,   # SAME as shadowfox!
            actor_id=zerobyte.id,
            source_id=src["ExploitDB Underground"].id,
            first_seen=base_dt + timedelta(days=405),
            last_seen=base_dt + timedelta(days=900),
        )
        pgp_zerobyte_2 = PGPIdentifier(
            fingerprint="9F8E7D6C5B4A3928171615141312111009080706",
            actor_id=zerobyte.id,
            source_id=src["ExploitDB Underground"].id,
            first_seen=base_dt + timedelta(days=500),
            last_seen=base_dt + timedelta(days=920),
        )
        db.add_all([pgp_shadowfox_1, pgp_shadowfox_2, pgp_zerobyte_1, pgp_zerobyte_2])

        # PGPs for other actors
        pgps = []
        for a in other_actors:
            for _ in range(random.randint(1, 3)):
                fp = "".join(random.choices("0123456789ABCDEF", k=40))
                pgps.append(PGPIdentifier(
                    fingerprint=fp, actor_id=a.id,
                    source_id=random.choice(sources).id,
                    first_seen=base_dt + timedelta(days=random.randint(50, 400)),
                    last_seen=base_dt + timedelta(days=random.randint(500, 900)),
                ))
        db.add_all(pgps)
        db.commit()
        print(f"[+] Seeded PGP identifiers (including shared key evidence).")

        # ===================== WALLETS =====================
        # ShadowFox wallets
        w_sf1 = Wallet(
            address="DEMO_BTC_WALLET_SHADOWFOX_PRIMARY_NOT_VALID",
            blockchain="BTC", actor_id=shadowfox.id,
            source_id=src["CryptoTrace"].id,
            first_seen=base_dt + timedelta(days=40),
            last_seen=base_dt + timedelta(days=700),
        )
        w_sf2 = Wallet(
            address="DEMO_ETH_WALLET_SHADOWFOX_SECONDARY_NOT_VALID",
            blockchain="ETH", actor_id=shadowfox.id,
            source_id=src["CryptoTrace"].id,
            first_seen=base_dt + timedelta(days=300),
            last_seen=base_dt + timedelta(days=900),
        )
        # ZeroByte wallet — DIFFERENT from ShadowFox (negative evidence)
        w_zb1 = Wallet(
            address="DEMO_BTC_WALLET_ZEROBYTE_PRIMARY_NOT_VALID",
            blockchain="BTC", actor_id=zerobyte.id,
            source_id=src["CryptoTrace"].id,
            first_seen=base_dt + timedelta(days=410),
            last_seen=base_dt + timedelta(days=920),
        )
        w_zb2 = Wallet(
            address="DEMO_ETH_WALLET_ZEROBYTE_SECONDARY_NOT_VALID",
            blockchain="ETH", actor_id=zerobyte.id,
            source_id=src["ExploitDB Underground"].id,
            first_seen=base_dt + timedelta(days=500),
            last_seen=base_dt + timedelta(days=920),
        )
        db.add_all([w_sf1, w_sf2, w_zb1, w_zb2])

        # Wallets for other actors
        wallets = []
        for a in other_actors:
            for wallet_index in range(random.randint(2, 4)):
                bc = random.choice(["BTC", "ETH", "XMR"])
                addr = f"DEMO_{bc}_WALLET_ACTOR_{a.id}_{wallet_index}_NOT_VALID"
                wallets.append(Wallet(
                    address=addr, blockchain=bc, actor_id=a.id,
                    source_id=random.choice(sources).id,
                    first_seen=base_dt + timedelta(days=random.randint(50, 400)),
                    last_seen=base_dt + timedelta(days=random.randint(500, 900)),
                ))
        db.add_all(wallets)
        db.commit()
        print("[+] Seeded wallets.")

        # ===================== HANDLES =====================
        # ShadowFox handles
        handles_sf = [
            Handle(actor_id=shadowfox.id, handle="@shadow_fox99", platform="DarkMarket Forum",
                   source_id=src["DarkMarket Forum"].id,
                   first_seen=base_dt + timedelta(days=30), last_seen=base_dt + timedelta(days=600)),
            Handle(actor_id=shadowfox.id, handle="shadow.fox", platform="DarkMarket Forum",
                   source_id=src["DarkMarket Forum"].id,
                   first_seen=base_dt + timedelta(days=30), last_seen=base_dt + timedelta(days=400)),
            Handle(actor_id=shadowfox.id, handle="sf_ransom", platform="TorLeaks Archive",
                   source_id=src["TorLeaks Archive"].id,
                   first_seen=base_dt + timedelta(days=100), last_seen=base_dt + timedelta(days=380)),
        ]
        # ZeroByte handles
        handles_zb = [
            Handle(actor_id=zerobyte.id, handle="0xByte", platform="ExploitDB Underground",
                   source_id=src["ExploitDB Underground"].id,
                   first_seen=base_dt + timedelta(days=400), last_seen=base_dt + timedelta(days=920)),
            Handle(actor_id=zerobyte.id, handle="z3r0_byte", platform="ExploitDB Underground",
                   source_id=src["ExploitDB Underground"].id,
                   first_seen=base_dt + timedelta(days=420), last_seen=base_dt + timedelta(days=900)),
            Handle(actor_id=zerobyte.id, handle="ZeroByte", platform="Hacker Forum B",
                   source_id=src["Hacker Forum B"].id,
                   first_seen=base_dt + timedelta(days=450), last_seen=base_dt + timedelta(days=920)),
        ]
        db.add_all(handles_sf + handles_zb)

        # Handles for other actors
        prefixes = ["Shadow", "Dark", "Cyber", "Ghost", "Zero", "Anon", "X", "Phantom", "Rogue", "Crimson", "Night", "Null"]
        suffixes = ["Wolf", "Fox", "Byte", "Strike", "Sec", "Net", "Blade", "Root", "Admin", "Hax", "Ninja", "Bot"]
        platforms_list = ["DarkMarket Forum", "ExploitDB Underground", "TorLeaks Archive", "Hacker Forum B", "Pastebin Monitor"]
        handles = []
        for a in other_actors:
            for _ in range(random.randint(2, 5)):
                h = f"@{random.choice(prefixes)}{random.choice(suffixes)}{random.randint(0,999) if random.random()>0.5 else ''}"
                handles.append(Handle(
                    actor_id=a.id, handle=h,
                    platform=random.choice(platforms_list),
                    source_id=random.choice(sources).id,
                    first_seen=base_dt + timedelta(days=random.randint(30, 500)),
                    last_seen=base_dt + timedelta(days=random.randint(500, 950)),
                ))
        db.add_all(handles)
        db.commit()
        print("[+] Seeded handles.")

        # ===================== ONION SERVICES =====================
        onion_services_data = [
            ("shadowfox-market.onion.invalid", "ShadowFox Market", shadowfox.id, "ONLINE"),
            ("zerobyte-toolshop.onion.invalid", "ZeroByte Toolshop", zerobyte.id, "OFFLINE"),
            ("darkmarket-main.onion.invalid", "DarkMarket Main", None, "ONLINE"),
            ("exploitdb-underground.onion.invalid", "ExploitDB Underground", None, "ONLINE"),
            ("ransom-demo-portal.onion.invalid", "Synthetic Ransom Portal", None, "ONLINE"),
            ("credentials-vault.onion.invalid", "Credentials Vault", None, "SUSPECTED"),
            ("nullbyte-shop.onion.invalid", "NullByte Shop", None, "OFFLINE"),
        ]
        onion_services = []
        for addr, title, actor_id, status in onion_services_data:
            os_entry = OnionService(
                address=addr, title=title,
                status=status,
                first_seen=base_dt + timedelta(days=random.randint(50, 300)),
                last_seen=base_dt + timedelta(days=random.randint(700, 950)),
                metadata_={"synthetic": True, "note": "Controlled demonstration data"},
                source_id=random.choice(sources).id,
            )
            onion_services.append(os_entry)
        db.add_all(onion_services)

        # Extra onion services
        for i in range(43):
            addr = f"demo-hidden-service-{300+i}.onion.invalid"
            onion_services.append(OnionService(
                address=addr, title=f"Hidden Service {300+i}", status=random.choice(["ONLINE", "OFFLINE", "SUSPECTED"]),
                first_seen=base_dt + timedelta(days=random.randint(10, 500)),
                last_seen=base_dt + timedelta(days=random.randint(500, 950)),
                metadata_={"synthetic": True},
                source_id=random.choice(sources).id,
            ))
        db.add_all(onion_services[-43:])
        db.commit()
        print(f"[+] Seeded onion services.")

        # ===================== POSTS =====================
        # ShadowFox posts (distinctive style)
        sf_posts_texts = [
            "selling simulated rdp access to fictional acme-labs.example.invalid network. contact via pgp only. demo pricing negotiable.",
            "new ransomware build available. undetected as of today. 20% affiliate split. serious inquiries only.",
            "credit card dumps fresh from pos systems. high balance guaranteed. contact me via jabber for samples.",
            "looking for trusted escrow for large transaction. reputation vouched by multiple forum members.",
            "infrastructure for sale. dedicated servers, bulletproof hosting. no logs policy strictly enforced.",
            "offering 0day for popular vpn solution. price 50k usd. pgp authentication required for contact.",
            "forum members beware of imposters using similar handles. my pgp fingerprint is in profile.",
            "bulk fullz available from recent breach. 50k records. price per record negotiable in volume.",
            "crypter fud for 30 days. custom stub per client. contact for pricing and samples.",
            "ransomware deployment service. target qualification required. 30% revenue share model.",
            "synthetic access record for fictional northstar-clinic.example.invalid. lab directory snapshot available.",
            "selling fabricated corporate email access lists for demo organizations. synthetic bulk pricing available.",
            "trusted by top forum members for 3 years. history available on request.",
        ]
        # ZeroByte posts (similar style — key stylometry evidence)
        zb_posts_texts = [
            "selling rdp access to major us corporations. network pivoting available. pgp contact only.",
            "new payload ready for deployment. clean against major av solutions. affiliate program open.",
            "card dumps available from recent point of sale compromise. high balance profiles. jabber for details.",
            "looking for reliable escrow service for large deals. need established forum member.",
            "dedicated infrastructure for rent. clean ips, no abuse complaints. strict no-logging.",
            "vulnerability in enterprise vpn software. proof of concept available. interested parties only.",
            "verify my pgp key against profile. all impersonators should be reported to mods.",
            "fabricated database of accounts from fictional aurora-bank.example.invalid. demo bulk rates on request.",
            "custom crypter service with fud guarantee for extended period. contact for sample.",
            "access broker service for enterprise targets. revenue sharing arrangement.",
            "fresh corporate access available. complete network map included.",
            "verified seller with established track record across multiple forums.",
        ]

        sf_posts = [Post(
            actor_id=shadowfox.id, platform="DarkMarket Forum", content=t, language="en",
            source_id=src["DarkMarket Forum"].id,
            timestamp=base_dt + timedelta(days=random.randint(30, 600)),
        ) for t in sf_posts_texts]

        zb_posts = [Post(
            actor_id=zerobyte.id, platform="ExploitDB Underground", content=t, language="en",
            source_id=src["ExploitDB Underground"].id,
            timestamp=base_dt + timedelta(days=random.randint(400, 920)),
        ) for t in zb_posts_texts]

        db.add_all(sf_posts + zb_posts)

        # Posts for other actors
        topics = [
            ["credit", "dumps", "cvv", "fullz", "bank", "cards", "payment"],
            ["malware", "botnet", "c2", "rat", "crypter", "payload", "fud"],
            ["access", "rdp", "vpn", "network", "shell", "corporate", "webshell"],
            ["leak", "database", "sql", "breach", "combo", "passwords", "credentials"],
            ["exploit", "0day", "cve", "vulnerability", "poc", "rce", "privesc"],
        ]
        posts = []
        for a in other_actors:
            topic = random.choice(topics)
            for _ in range(random.randint(8, 15)):
                words = random.choices(topic + ["contact", "price", "bulk", "fresh", "verified", "trusted", "pgp", "jabber"], k=random.randint(8, 20))
                content = " ".join(words) + "."
                posts.append(Post(
                    actor_id=a.id,
                    platform=random.choice(platforms_list),
                    content=content, language="en",
                    source_id=random.choice(sources).id,
                    timestamp=base_dt + timedelta(days=random.randint(100, 900)),
                ))
        db.add_all(posts)
        db.commit()
        print("[+] Seeded posts.")

        # ===================== INFRASTRUCTURE INDICATORS =====================
        os_ent = db.query(OnionService).first()
        infra_data = [
            ("tls_fingerprint", "JA3:a1b2c3d4e5f6789012345678901234ab", 0.82),
            ("http_header", "Server: nginx/1.18.0 (custom build)", 0.71),
            ("ssl_cert_serial", "7F:3A:1B:9C:4D:2E:5F:6A", 0.88),
            ("hosting_asn", "AS12345 BulletProof Hosting Ltd", 0.75),
            ("bitcoin_address", "DEMO_BTC_WALLET_INFRASTRUCTURE_NOT_VALID", 0.90),
            ("domain_registrar", "Anonymous Domain Registration Service", 0.65),
        ]
        infra = []
        for i_type, value, confidence in infra_data:
            infra.append(InfrastructureIndicator(
                service_id=os_ent.id if os_ent else None,
                indicator_type=i_type, value=value, confidence=confidence,
                source_id=random.choice(sources).id,
                observed_at=base_dt + timedelta(days=random.randint(200, 700)),
            ))
        db.add_all(infra)
        db.commit()
        print("[+] Seeded infrastructure indicators.")

        # ===================== RELATIONSHIPS =====================
        relationships = []
        # ShadowFox <-> ZeroByte (main relationship)
        relationships.append(Relationship(
            source_entity_type="actor", source_entity_id=shadowfox.id,
            relationship_type="POSSIBLY_SAME_ACTOR",
            target_entity_type="actor", target_entity_id=zerobyte.id,
            confidence=0.84,
            evidence={
                "positive": [
                    {"type": "shared_pgp", "value": shared_pgp_fp[:16] + "...", "weight": 30},
                    {"type": "stylometric_similarity", "value": "0.86", "weight": 15},
                    {"type": "behavioural_similarity", "value": "0.82", "weight": 10},
                    {"type": "timeline_correlation", "value": "Gap after DarkMarket takedown", "weight": 5},
                    {"type": "infrastructure_overlap", "value": "Shared hosting fingerprint", "weight": 8},
                ],
                "negative": [
                    {"type": "different_wallet", "value": "No shared BTC/ETH wallets", "weight": -8},
                    {"type": "different_platform", "value": "Distinct platform communities", "weight": -5},
                ]
            }
        ))
        # Actor-handle relationships
        all_handles = db.query(Handle).limit(20).all()
        for h in all_handles:
            relationships.append(Relationship(
                source_entity_type="actor", source_entity_id=h.actor_id,
                relationship_type="USES_HANDLE",
                target_entity_type="handle", target_entity_id=h.id,
                confidence=0.95,
                evidence={"source": "forum_observation"}
            ))
        db.add_all(relationships)
        db.commit()
        print("[+] Seeded relationships.")

        # ===================== ATTRIBUTION ASSESSMENTS =====================
        assessment = AttributionAssessment(
            actor_a=shadowfox.id,
            actor_b=zerobyte.id,
            score=84.0,
            confidence_level="HIGH",
            evidence_json={
                "shared_pgp": {"score": 30, "description": "Identical PGP fingerprint observed on both personas", "type": "positive"},
                "stylometry": {"score": 13, "description": "Stylometric similarity 86% — distinctive writing pattern match", "type": "positive"},
                "behaviour": {"score": 8, "description": "Behavioural profile similarity 82% — consistent activity hours", "type": "positive"},
                "timeline": {"score": 5, "description": "ShadowFox inactivity coincides with ZeroByte emergence", "type": "positive"},
                "infrastructure": {"score": 6, "description": "TLS fingerprint overlap on observed services", "type": "positive"},
                "wallet_divergence": {"score": -8, "description": "No shared cryptocurrency wallets identified", "type": "negative"},
                "platform_divergence": {"score": -5, "description": "Different forum communities with no direct crossover", "type": "negative"},
            },
            negative_evidence_json={
                "different_wallet": "No shared BTC or ETH wallets detected across observed transactions.",
                "different_platform": "Platforms used by both personas do not overlap in membership lists.",
            },
            explanation=(
                "Attribution assessment based on convergence of multiple independent evidence streams. "
                "Shared PGP fingerprint provides strongest single indicator. "
                "Stylometric and behavioural analysis corroborate the relationship. "
                "Timeline correlation consistent with persona migration following DarkMarket disruption. "
                "Absence of shared wallets reduces confidence. "
                "Assessment requires analyst verification before operational use."
            )
        )
        db.add(assessment)
        db.commit()
        print("[+] Seeded ShadowFox-ZeroByte attribution assessment (score: 84).")

        print("\n=== Seeding Complete ===")
        print(f"Actors: {db.query(Actor).count()}")
        print(f"Handles: {db.query(Handle).count()}")
        print(f"PGP Identifiers: {db.query(PGPIdentifier).count()}")
        print(f"Wallets: {db.query(Wallet).count()}")
        print(f"Posts: {db.query(Post).count()}")
        print(f"Onion Services: {db.query(OnionService).count()}")
        print(f"Infrastructure Indicators: {db.query(InfrastructureIndicator).count()}")
        print(f"Relationships: {db.query(Relationship).count()}")
        print(f"Sources: {db.query(Source).count()}")
        print(f"Attribution Assessments: {db.query(AttributionAssessment).count()}")

    finally:
        db.close()

if __name__ == "__main__":
    print("=== DARKTRACE Demo Database Seeder ===")
    reset_db()
    seed()
