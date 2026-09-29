"""Seed a completed Robin job for the local SIH demonstration.

DEMO DATA ONLY — synthetic data for local development and demonstration.
No real-world threat intelligence is included.

All domains use the reserved ``.invalid`` top-level domain. Wallets, handles,
emails, infrastructure identifiers, and organization names are deliberately
non-operational. The output schema matches Robin jobs created by the backend.
"""

import json
import os


DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
os.makedirs(DATA_DIR, exist_ok=True)
JOBS_FILE = os.path.join(DATA_DIR, "robin_jobs.json")


scraped_pages_data = [
    {
        "url": "http://nightjar-market.onion.invalid/board",
        "title": "Nightjar Collective Demo Board",
        "status": "success",
        "status_code": 200,
        "entity_count": 5,
        "engine": "SyntheticDemo",
        "scraped_at": "2026-09-25T17:26:28.000000Z",
        "text": (
            "SYNTHETIC EXERCISE RECORD. The fictional Nightjar Collective uses "
            "the handle @demo_nightjar and demo contact analyst-one@example.invalid. "
            "Observed wallet DEMO_BTC_WALLET_NIGHTJAR_NOT_VALID and infrastructure "
            "nightjar-drop.onion.invalid."
        ),
        "entities": {
            "btc_wallets": ["DEMO_BTC_WALLET_NIGHTJAR_NOT_VALID"],
            "emails": ["analyst-one@example.invalid"],
            "handles": ["demo_nightjar"],
            "onion_addresses": ["nightjar-market.onion.invalid", "nightjar-drop.onion.invalid"],
        },
    },
    {
        "url": "http://copper-finch.onion.invalid/notices",
        "title": "Copper Finch Synthetic Noticeboard",
        "status": "success",
        "status_code": 200,
        "entity_count": 5,
        "engine": "SyntheticDemo",
        "scraped_at": "2026-09-25T17:26:40.000000Z",
        "text": (
            "SYNTHETIC EXERCISE RECORD. The fictional Copper Finch persona posts as "
            "@demo_copperfinch and shares nightjar-drop.onion.invalid with another "
            "demo persona. Contact analyst-two@example.invalid. Wallet "
            "DEMO_XMR_WALLET_COPPER_FINCH_NOT_VALID."
        ),
        "entities": {
            "xmr_wallets": ["DEMO_XMR_WALLET_COPPER_FINCH_NOT_VALID"],
            "emails": ["analyst-two@example.invalid"],
            "handles": ["demo_copperfinch"],
            "onion_addresses": ["copper-finch.onion.invalid", "nightjar-drop.onion.invalid"],
        },
    },
    {
        "url": "http://demo-key-index.onion.invalid/keys",
        "title": "Synthetic Identity Key Index",
        "status": "success",
        "status_code": 200,
        "entity_count": 4,
        "engine": "SyntheticDemo",
        "scraped_at": "2026-09-25T17:26:55.000000Z",
        "text": (
            "SYNTHETIC EXERCISE RECORD. Demo key fingerprint "
            "DEMO-PGP-FINGERPRINT-NIGHTJAR-NOT-VALID is associated with "
            "@demo_nightjar and nightjar-market.onion.invalid."
        ),
        "entities": {
            "pgp_fingerprints": ["DEMO-PGP-FINGERPRINT-NIGHTJAR-NOT-VALID"],
            "handles": ["demo_nightjar"],
            "onion_addresses": ["demo-key-index.onion.invalid", "nightjar-market.onion.invalid"],
        },
    },
]


observations = []
aggregated = {
    "btc_wallets": set(),
    "xmr_wallets": set(),
    "pgp_fingerprints": set(),
    "emails": set(),
    "handles": set(),
    "onion_addresses": set(),
}

for page in scraped_pages_data:
    observations.append(
        {
            "source": "RobinSyntheticDemo",
            "source_type": "synthetic-demo",
            "service": page["url"].split("/")[2],
            "title": page["title"],
            "content": page["text"][:2000],
            "raw_reference": page["url"],
            "reliability": 0.50,
            "collection_method": "SyntheticDemoSeed",
            "timestamp": page["scraped_at"],
            "extracted_entities": page["entities"],
            "query": "synthetic relationship exercise",
            "engine": page["engine"],
            "tor_used": False,
        }
    )
    for entity_type, values in page["entities"].items():
        if entity_type in aggregated:
            aggregated[entity_type].update(values)

all_entities = {key: sorted(values) for key, values in aggregated.items() if values}
search_results = [
    {
        "link": page["url"],
        "title": page["title"],
        "snippet": page["text"][:120],
        "engine": page["engine"],
    }
    for page in scraped_pages_data
]

job_id = "demo-robin-001"
jobs_data = {
    job_id: {
        "job_id": job_id,
        "query": "synthetic relationship exercise",
        "status": "done",
        "started_at": "2026-09-25T17:26:28.000000Z",
        "finished_at": "2026-09-25T17:26:59.000000Z",
        "elapsed_seconds": 31.0,
        "tor_used": False,
        "search_results_count": len(search_results),
        "pages_scraped": len(scraped_pages_data),
        "observations": observations,
        "all_entities": all_entities,
        "search_results": search_results,
        "scraped_pages": scraped_pages_data,
        "error": None,
        "demo_data": True,
    }
}

with open(JOBS_FILE, "w", encoding="utf-8") as file_handle:
    json.dump(jobs_data, file_handle, indent=2)

print(f"Seeded {len(jobs_data)} synthetic Robin demo job to {JOBS_FILE}")
