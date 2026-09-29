"""
mock_forum.py — Self-hosted Mock Dark Forum for DarkTrace Demo
Generates realistic dark-web forum HTML served by FastAPI itself.
The DarkTrace crawler can safely crawl this endpoint for live demos.

Routes exposed (mounted at /api/mock-forum):
  GET /         — Forum index with thread list
  GET /thread/{thread_id} — Individual thread with posts
  GET /member/{username}  — Member profile page

All content is synthetic/fictional. Wallets and onion hosts are deliberately
invalid identifiers that cannot be used on production networks.
"""

import random
import hashlib
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

# ─────────────────────────────────────────────────────────────────
# Synthetic data pools
# ─────────────────────────────────────────────────────────────────

_HANDLES = [
    "@ShadowFox_RU", "@ZeroByte_RaaS", "@CrimsonKnight", "@NullVector",
    "@PhantomExec", "@DarkMatter_67", "@r00tz_crew", "@ByteWitch",
    "@VoidRunner", "@GhostCell_0x41", "@EncryptedSoul", "@BinaryGhost",
    "@RedTeam_Alpha", "@SilkRoad_Redux", "@NightCipher",
]

_BTCS = [
    "DEMO_BTC_WALLET_FORUM_ALPHA_NOT_VALID",
    "DEMO_BTC_WALLET_FORUM_BRAVO_NOT_VALID",
    "DEMO_BTC_WALLET_FORUM_CHARLIE_NOT_VALID",
    "DEMO_BTC_WALLET_FORUM_DELTA_NOT_VALID",
]

_PGPS = [
    "A3F4B2C1D0E9F8A7B6C5D4E3F2A1B0C9",
    "1F2E3D4C5B6A7980ABCDEF0123456789",
    "DEADBEEF01234567ABCDEF9876543210",
    "0x4E9A7B2F1C8D6E3A5B0F2D4C7E1A9B3D",
]

_ONIONS = [
    "darkforum-demo.onion.invalid",
    "leakmarket-demo.onion.invalid",
    "cardshop-demo.onion.invalid",
    "exploitdb-demo.onion.invalid",
]

_CATEGORIES = [
    "Credentials & Leaks", "Malware & Exploits", "Carding & Fraud",
    "Ransomware Services", "OSINT & Doxing", "Network Access",
]

_THREAD_TOPICS = [
    ("Synthetic credentials exercise — Acme Labs", "Credentials & Leaks"),
    ("[SIMULATION] CrimsonLock lab affiliate scenario", "Ransomware Services"),
    ("Fabricated payment-card dataset for analyst training", "Carding & Fraud"),
    ("Synthetic web-service exploit discussion", "Malware & Exploits"),
    ("[OSINT LAB] Correlating fictional chat aliases", "OSINT & Doxing"),
    ("Demo VPN access — Northstar Logistics", "Network Access"),
    ("KeyLogger simulator v5 — inert training sample", "Malware & Exploits"),
    ("Lab shell access — example.invalid host", "Network Access"),
    ("Fabricated school-domain account dataset", "Credentials & Leaks"),
    ("[LAB GROUP] Recruiting for defensive malware analysis", "Malware & Exploits"),
]

_POST_CONTENTS = [
    "DEMO ONLY. Synthetic vendor. PGP marker: {pgp}. Invalid BTC identifier: {btc}.",
    "SIMULATION ONLY. Lab scenario contact via {onion} or handle {handle}.",
    "Fabricated dataset listing. Invalid payment identifier: {btc}. PGP marker: {pgp}.",
    "Synthetic logs — no real records. BTC demo identifier: {btc}. Contact: {handle}.",
    "Training scenario seeking a lab partner. Fictional handle: {handle}.",
    "Inert exploit exercise. Invalid BTC identifier: {btc}.",
    "Synthetic sample available. Invalid payment identifier: {btc}. Signature marker: {pgp}.",
    "Demo forum voucher: @ShadowFox_RU. Fictional verifier: {handle}.",
    "Synthetic market at {onion}. Demo admin: {handle}.",
    "Mixer-analysis exercise. Invalid identifier: {btc}. Non-routable host: {onion}.",
]


def _random_handle() -> str:
    return random.choice(_HANDLES)

def _random_btc() -> str:
    return random.choice(_BTCS)

def _random_pgp() -> str:
    return random.choice(_PGPS)

def _random_onion() -> str:
    return random.choice(_ONIONS)

def _past_date(days_ago_max: int = 180) -> str:
    delta = timedelta(days=random.randint(1, days_ago_max))
    return (datetime.now(timezone.utc) - delta).strftime("%Y-%m-%d %H:%M UTC")

def _render_post(content_template: str) -> str:
    return content_template.format(
        handle=_random_handle(),
        btc=_random_btc(),
        pgp=_random_pgp(),
        onion=_random_onion(),
    )


# ─────────────────────────────────────────────────────────────────
# HTML generators
# ─────────────────────────────────────────────────────────────────

_CSS = """
<style>
  body { background: #0d0d0d; color: #c9c9c9; font-family: monospace; margin: 0; padding: 20px; }
  h1, h2 { color: #e0442a; }
  a { color: #7ec8e3; text-decoration: none; }
  a:hover { text-decoration: underline; }
  .forum-header { border-bottom: 1px solid #333; padding-bottom: 10px; margin-bottom: 20px; }
  .thread-row { border: 1px solid #222; margin: 6px 0; padding: 10px; background: #111; }
  .thread-row:hover { background: #1a1a1a; }
  .badge { background: #e0442a; color: white; font-size: 11px; padding: 2px 6px; border-radius: 3px; }
  .post { border: 1px solid #2a2a2a; margin: 10px 0; padding: 12px; background: #111; }
  .post-header { color: #7ec8e3; font-size: 12px; margin-bottom: 8px; }
  .post-body { line-height: 1.6; }
  .entity { background: #1a2a1a; color: #6ec96e; padding: 1px 4px; border-radius: 2px; font-size: 12px; }
  .stat { color: #888; font-size: 12px; }
  .footer { margin-top: 40px; border-top: 1px solid #222; padding-top: 10px; font-size: 11px; color: #444; }
</style>
"""

def render_forum_index() -> str:
    """Generate the dark forum index page HTML."""
    threads_html = ""
    for i, (topic, category) in enumerate(_THREAD_TOPICS, start=1):
        author = _random_handle()
        replies = random.randint(3, 87)
        views = random.randint(200, 15000)
        posted = _past_date(90)
        threads_html += f"""
        <div class="thread-row">
          <div><a href="/api/mock-forum/thread/{i}"><strong>{topic}</strong></a>
          <span class="badge" style="margin-left:8px">{category}</span></div>
          <div class="stat">By: <span class="entity">{author}</span> &nbsp;|&nbsp;
          Replies: {replies} &nbsp;|&nbsp; Views: {views} &nbsp;|&nbsp; {posted}</div>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>BreachZone Forum — Controlled Demo Environment</title>{_CSS}</head>
<body>
<div class="forum-header">
  <h1>BreachZone Underground Forum</h1>
  <div class="stat">NOTICE: This is a controlled demo environment operated by DarkTrace Research.
  All content is synthetic. No real credentials or malware exist here.</div>
</div>
<h2>Active Threads ({len(_THREAD_TOPICS)})</h2>
{threads_html}
<div class="footer">BreachZone Forum v4.2 | Tor: {_ONIONS[0]} | Members: {random.randint(8000,25000):,}</div>
</body></html>"""


def render_thread(thread_id: int) -> str:
    """Generate a dark forum thread page with posts containing entities."""
    idx = (thread_id - 1) % len(_THREAD_TOPICS)
    topic, category = _THREAD_TOPICS[idx]

    op_handle = _random_handle()
    op_btc = _random_btc()
    op_pgp = _random_pgp()
    op_date = _past_date(90)

    posts_html = f"""
    <div class="post">
      <div class="post-header">OP: <span class="entity">{op_handle}</span> &nbsp;|&nbsp; {op_date} &nbsp;|&nbsp; Posts: {random.randint(100,2000)}</div>
      <div class="post-body">
        {_render_post(random.choice(_POST_CONTENTS))}<br><br>
        BTC Payment: <span class="entity">{op_btc}</span><br>
        PGP Key: <span class="entity">{op_pgp}</span><br>
        Contact via Telegram: <span class="entity">{op_handle}</span><br>
        Private board: <span class="entity">{_random_onion()}</span>
      </div>
    </div>
    """

    n_replies = random.randint(3, 8)
    for j in range(n_replies):
        reply_handle = _random_handle()
        reply_date = _past_date(80)
        reply_content = _render_post(random.choice(_POST_CONTENTS))
        posts_html += f"""
    <div class="post">
      <div class="post-header">#{j+2} &nbsp;|&nbsp; <span class="entity">{reply_handle}</span> &nbsp;|&nbsp; {reply_date}</div>
      <div class="post-body">{reply_content}</div>
    </div>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>{topic} — BreachZone</title>{_CSS}</head>
<body>
<div class="forum-header">
  <h1><a href="/api/mock-forum/">BreachZone</a> &gt; {category}</h1>
  <h2>{topic}</h2>
</div>
{posts_html}
<div class="footer">BreachZone Forum v4.2 — Controlled Synthetic Demo | Thread #{thread_id}</div>
</body></html>"""


def render_member_profile(username: str) -> str:
    """Generate a synthetic member profile page."""
    joined = _past_date(365)
    posts = random.randint(50, 3000)
    rep = random.randint(-5, 200)
    btc = _random_btc()
    pgp = _random_pgp()

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Member: {username} — BreachZone</title>{_CSS}</head>
<body>
<div class="forum-header">
  <h1><a href="/api/mock-forum/">BreachZone</a> &gt; Member Profile</h1>
</div>
<div class="post">
  <h2>{username}</h2>
  <div class="stat">Joined: {joined} &nbsp;|&nbsp; Posts: {posts} &nbsp;|&nbsp; Reputation: {rep}</div>
  <br>
  <strong>BTC Address:</strong> <span class="entity">{btc}</span><br>
  <strong>PGP Fingerprint:</strong> <span class="entity">{pgp}</span><br>
  <strong>Status:</strong> <span class="badge">VERIFIED VENDOR</span><br>
  <strong>Contact:</strong> Telegram: <span class="entity">{username}</span><br>
</div>
<div class="footer">BreachZone Forum v4.2 — Controlled Synthetic Demo</div>
</body></html>"""


def get_forum_as_crawlable_records() -> List[Dict[str, Any]]:
    """
    Return mock forum content as structured dicts ready for crawler ingestion.
    Used by the ingestion worker to feed mock forum data into the pipeline.
    """
    records = []
    now = datetime.now(timezone.utc)

    for i, (topic, category) in enumerate(_THREAD_TOPICS, start=1):
        op_handle = _random_handle()
        op_btc = _random_btc()
        op_pgp = _random_pgp()
        op_onion = _random_onion()

        content = (
            f"Category: {category}. Topic: {topic}. "
            f"Author: {op_handle}. "
            f"Payment BTC: {op_btc}. "
            f"PGP: {op_pgp}. "
            f"Contact: {op_onion}. "
            f"{_render_post(random.choice(_POST_CONTENTS))}"
        )

        records.append({
            "source": "MockDarkForum",
            "source_type": "forum-post",
            "service": "localhost/api/mock-forum",
            "title": topic,
            "content": content,
            "raw_reference": f"mock_forum::thread::{i}::v1",
            "reliability": 0.75,
            "metadata": {
                "thread_id": i,
                "category": category,
                "author": op_handle,
                "is_mock": True,
            },
            "extracted_entities": {
                "handles": [op_handle],
                "wallets": [op_btc],
                "pgp_keys": [op_pgp],
                "emails": [],
                "domains": [op_onion],
            },
            "timestamp": (now - timedelta(days=random.randint(1, 60))).isoformat(),
        })

    return records
