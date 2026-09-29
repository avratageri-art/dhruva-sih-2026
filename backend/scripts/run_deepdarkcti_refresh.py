import sys
sys.path.insert(0, '.')
from app.database import SessionLocal
from app.services.crawler.deepdarkcti_importer import refresh_all, upsert_sources_to_db

print('=== Fetching deepdarkCTI sources from GitHub ===')
result = refresh_all(timeout=30)
total = result['total_sources']
print(f'Total sources fetched: {total}')
print('By category:')
for cat, info in result['by_category'].items():
    print(f'  {cat}: {info["count"]} sources')
if result['errors']:
    print('Errors:', result['errors'])

print()
print('=== Upserting to database ===')
db = SessionLocal()
try:
    stats = upsert_sources_to_db(result['sources'], db, result['fetched_at'])
    print(f'Created: {stats["created"]}, Updated: {stats["updated"]}, Skipped: {stats["skipped"]}')
finally:
    db.close()

print()
print('=== Verifying DB state ===')
db2 = SessionLocal()
try:
    from app.models.intelligence import SeedSource
    ddc_total = db2.query(SeedSource).filter(SeedSource.notes.like('%deepdarkCTI%')).count()
    print(f'Total deepdarkCTI sources in DB: {ddc_total}')
    
    # Show sample
    samples = db2.query(SeedSource).filter(SeedSource.notes.like('%deepdarkCTI%')).limit(5).all()
    for s in samples:
        print(f'  [{s.id}] {s.name} | cat={s.category} | status={s.status} | url={s.reference[:60]}')
finally:
    db2.close()

print('DONE.')
