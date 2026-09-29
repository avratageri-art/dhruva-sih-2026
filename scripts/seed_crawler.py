"""Populate the SeedSource registry with non-routable synthetic demo entries.

DEMO DATA ONLY — synthetic data for local development and demonstration.
No real-world threat intelligence is included and no collection starts here.
"""
import os
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BACKEND_DIR = os.path.join(PROJECT_ROOT, 'backend')
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault('DATABASE_URL', f'sqlite:///{os.path.join(BACKEND_DIR, "darktrace.db")}')

from app.database import SessionLocal
from app.models.intelligence import SeedSource

db = SessionLocal()

print("🌱 Seeding DarkTrace Seed Sources...")

seeds_data = [
    ("tor://demo-market.onion.invalid", "DemoMarket Forum", "SYNTHETIC", 0.90, "15m", "Non-routable synthetic marketplace seed"),
    ("tor://nightjar-panel.onion.invalid", "Nightjar Exercise Panel", "SYNTHETIC", 0.95, "30m", "Non-routable synthetic actor seed"),
    ("tor://zerobyte-lab.onion.invalid", "ZeroByte Exercise Hub", "SYNTHETIC", 0.92, "1h", "Non-routable synthetic research seed"),
    ("tor://nullroot-demo.onion.invalid", "NullRoot Exercise Portal", "SYNTHETIC", 0.88, "2h", "Non-routable synthetic relationship seed"),
]

for ref, name, cat, rel, freq, notes in seeds_data:
    existing = db.query(SeedSource).filter(SeedSource.reference == ref).first()
    if not existing:
        s = SeedSource(
            reference=ref,
            name=name,
            category=cat,
            reliability=rel,
            collection_frequency=freq,
            authorized=0,
            status="DISCOVERED",
            first_seen=datetime.utcnow() - timedelta(days=60),
            last_seen=datetime.utcnow() - timedelta(minutes=15),
            notes=notes,
            observation_count=0,
            error_count=0,
        )
        db.add(s)

db.commit()
print(f"✓ Seed sources registered: {db.query(SeedSource).count()}")

db.close()
print("✅ Synthetic crawler seeds registered; collection remains disabled.")
