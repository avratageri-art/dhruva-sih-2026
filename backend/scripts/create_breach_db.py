"""Create the local breach-correlation database from synthetic demo records.

DEMO DATA ONLY — synthetic data for local development and demonstration.
No real-world breach intelligence is included. Generated ``.db`` files are
runtime artifacts and are intentionally ignored by Git.
"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "breaches", "breaches.db")
os.makedirs(os.path.dirname(db_path), exist_ok=True)

conn = sqlite3.connect(db_path)
c = conn.cursor()

# Create breach records table
c.execute("""CREATE TABLE IF NOT EXISTS breach_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    breach_name TEXT NOT NULL,
    breach_date TEXT,
    source_platform TEXT,
    handle TEXT,
    email TEXT,
    password_hash TEXT,
    ip_address TEXT,
    additional_data TEXT,
    severity TEXT DEFAULT 'MEDIUM',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)""")

# Create breach metadata table
c.execute("""CREATE TABLE IF NOT EXISTS breach_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    breach_name TEXT UNIQUE NOT NULL,
    breach_date TEXT,
    record_count INTEGER,
    data_types TEXT,
    source TEXT,
    description TEXT
)""")

# Insert breach metadata
breaches_meta = [
    ('DemoMarket_2025_Exercise', '2025-11-15', 45000, 'handles,emails,passwords,ip_addresses',
     'Synthetic Market Exercise', 'Fictional records for local correlation demonstrations'),
    ('CipherBazaar_2026_Exercise', '2026-02-22', 23000, 'handles,emails,wallets,pgp_keys',
     'Synthetic Vendor Exercise', 'Fictional vendor and buyer registration records'),
    ('LabForum_2025_Exercise', '2025-08-10', 12000, 'handles,emails,posts',
     'Synthetic Research Forum', 'Fictional forum records with reserved example addresses'),
    ('SimulatedLeaks_2026_Exercise', '2026-04-01', 8500, 'handles,emails,passwords,wallets',
     'Synthetic Correlation Collection', 'Fictional identifiers for relationship-analysis testing'),
    ('DemoMail_2024_Exercise', '2024-12-20', 67000, 'emails,pgp_keys,metadata',
     'Synthetic Mail Archive', 'Fictional mail metadata for local development'),
]
c.executemany('INSERT OR IGNORE INTO breach_metadata VALUES (NULL,?,?,?,?,?,?)', breaches_meta)

# Insert breach records matching known actors
records = [
    # ShadowFox
    ('DemoMarket_2025_Exercise', '2025-11-15', 'DemoMarket Forum', 'shadow_fox99',
     'shadowfox@example.invalid', 'DEMO_PASSWORD_HASH_SHADOWFOX_NOT_VALID', '192.0.2.42',
     '{"registration_date":"2024-03-15","posts":847,"reputation":4.8}', 'HIGH'),
    ('SimulatedLeaks_2026_Exercise', '2026-04-01', 'Synthetic Aggregate', 'shadow_fox99',
     'shadow-desk@example.invalid', None, None,
     '{"alternate_handles":["sf99","shadow_admin"],"platforms":["DemoMarket","CipherBazaar"]}', 'HIGH'),
    ('CipherBazaar_2026_Exercise', '2026-02-22', 'CipherBazaar', 'shadow_fox99',
     'shadowfox@example.invalid', None, '192.0.2.42',
     '{"vendor_level":"Trusted","btc_wallet":"DEMO_BTC_WALLET_SHADOWFOX_NOT_VALID","pgp":"DEMO_PGP_SHADOWFOX_NOT_VALID"}', 'CRITICAL'),

    # ZeroByte
    ('LabForum_2025_Exercise', '2025-08-10', 'LabForum', 'zerobyte_off',
     'zerobyte@example.invalid', 'DEMO_PASSWORD_HASH_ZEROBYTE_NOT_VALID', '198.51.100.23',
     '{"registration_date":"2023-11-01","posts":312,"specialization":"0day_research"}', 'HIGH'),
    ('DemoMarket_2025_Exercise', '2025-11-15', 'DemoMarket Forum', '0xByte',
     'zerobyte@example.invalid', 'DEMO_PASSWORD_HASH_0XBYTE_NOT_VALID', '198.51.100.23',
     '{"alternate_handles":["zerobyte_off"],"pgp":"DEMO_PGP_ZEROBYTE_NOT_VALID"}', 'HIGH'),

    # CrimsonDump
    ('CipherBazaar_2026_Exercise', '2026-02-22', 'CipherBazaar', 'crimson_dump',
     'crimson-admin@example.invalid', None, '203.0.113.67',
     '{"vendor_level":"Premium","btc_wallet":"DEMO_BTC_WALLET_CRIMSON_NOT_VALID","pgp":"DEMO_PGP_CRIMSON_NOT_VALID"}', 'HIGH'),
    ('SimulatedLeaks_2026_Exercise', '2026-04-01', 'Synthetic Aggregate', 'crimson_dump',
     'crimson-admin@example.invalid', None, None,
     '{"contact":"crimson-admin@example.invalid","platforms":["CipherBazaar","DemoMarket"]}', 'MEDIUM'),

    # PhantomStrike
    ('DemoMarket_2025_Exercise', '2025-11-15', 'DemoMarket Forum', 'phantom_ddos',
     None, 'DEMO_PASSWORD_HASH_PHANTOM_NOT_VALID', '192.0.2.88',
     '{"registration_date":"2024-06-20","posts":156,"service":"DDoS-as-a-Service"}', 'MEDIUM'),
    ('CipherBazaar_2026_Exercise', '2026-02-22', 'CipherBazaar', 'PhantomStrike_BZ',
     None, None, '192.0.2.88',
     '{"vendor_level":"Standard","linked_handle":"phantom_ddos"}', 'MEDIUM'),

    # NullRoot
    ('LabForum_2025_Exercise', '2025-08-10', 'LabForum', 'null_r00t',
     None, 'DEMO_PASSWORD_HASH_NULLROOT_NOT_VALID', '203.0.113.156',
     '{"registration_date":"2024-01-10","posts":89,"specialization":"initial_access"}', 'MEDIUM'),
    ('DemoMarket_2025_Exercise', '2025-11-15', 'DemoMarket Forum', 'nullroot_acc',
     None, 'DEMO_PASSWORD_HASH_NULLROOT_ALT_NOT_VALID', '203.0.113.156',
     '{"alternate_handles":["null_r00t"],"service":"initial_access_broker"}', 'MEDIUM'),

    # Ghost Cipher (new actor from forum data)
    ('DemoMail_2024_Exercise', '2024-12-20', 'DemoMail', 'ghost_cipher',
     'ghost-cipher@example.invalid', None, None,
     '{"pgp":"DEMO_PGP_GHOST_CIPHER_NOT_VALID","mail_volume":245}', 'MEDIUM'),

    # Vortex Leaks
    ('SimulatedLeaks_2026_Exercise', '2026-04-01', 'Synthetic Aggregate', 'vortex_leaks',
     'vortex-ops@example.invalid', None, '198.51.100.100',
     '{"platforms":["CipherBazaar"],"specialization":"data_brokerage"}', 'MEDIUM'),
]
c.executemany('INSERT INTO breach_records VALUES (NULL,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)', records)

conn.commit()
total_records = c.execute("SELECT COUNT(*) FROM breach_records").fetchone()[0]
total_breaches = c.execute("SELECT COUNT(*) FROM breach_metadata").fetchone()[0]
print(f"Breach DB created at: {os.path.abspath(db_path)}")
print(f"  {total_records} breach records across {total_breaches} breaches")
conn.close()
