import requests, json
base = 'http://localhost:8000'

r = requests.get(base + '/api/deepdarkcti/status', timeout=10)
d = r.json()
print("=== deepdarkCTI Status: HTTP " + str(r.status_code) + " ===")
print("Total sources: " + str(d["sources"]["total"]))
print("Discovered: " + str(d["sources"]["discovered"]))
print("Enabled: " + str(d["sources"]["enabled"]))
print("Reachable: " + str(d["sources"]["reachable"]))
print("Observations: " + str(d["observations"]["total_from_deepdarkcti"]))

r2 = requests.get(base + '/api/deepdarkcti/sources?limit=5', timeout=10)
d2 = r2.json()
print("=== Sources (total " + str(d2["total"]) + ") ===")
for s in d2["sources"][:5]:
    print("  [" + str(s["id"]) + "] " + s["source_name"] + " | " + s["category"] + " | " + s["collection_status"])

r3 = requests.get(base + '/api/dashboard', timeout=10)
d3 = r3.json()
print("=== Dashboard deepdarkCTI ===")
print(json.dumps(d3.get("deepdarkcti", {}), indent=2))
