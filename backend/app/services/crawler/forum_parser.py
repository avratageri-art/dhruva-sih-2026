"""
forum_parser.py — Forum Data Parser & Ingestion Module for DarkTrace
Scans data/forums/ for .json and .html files, extracts threat actor handles,
timestamps, PGP blocks, wallets, and contact info, then normalizes for pipeline ingestion.
"""

import os
import re
import json
import hashlib
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger("ForumParser")

# Resolve data directories
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(MODULE_DIR, "..", "..", ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))

FORUM_DATA_DIRS = [
    os.path.join(PROJECT_ROOT, "data", "forums"),
    os.path.join(BACKEND_DIR, "data", "forums"),
]


def find_forum_dir() -> Optional[str]:
    """Locate the forums data directory."""
    for d in FORUM_DATA_DIRS:
        if os.path.isdir(d):
            return d
    return None


def parse_json_forum(filepath: str) -> List[Dict[str, Any]]:
    """
    Parse a JSON forum file. Supports two schemas:
    1. Array of thread objects with optional 'replies' arrays
    2. Array of flat post objects
    """
    posts = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            data = [data]

        for entry in data:
            forum = entry.get("forum", os.path.basename(filepath).replace(".json", ""))
            thread_id = entry.get("thread_id", "")
            thread_title = entry.get("thread_title", entry.get("title", ""))

            # Main post
            author = entry.get("author", entry.get("handle", ""))
            content = entry.get("content", entry.get("post", entry.get("body", "")))
            timestamp = entry.get("timestamp", entry.get("created_at", ""))
            author_pgp = entry.get("author_pgp", "")

            if content:
                posts.append({
                    "forum": forum,
                    "thread_id": thread_id,
                    "thread_title": thread_title,
                    "author": author,
                    "author_pgp": author_pgp,
                    "content": content,
                    "timestamp": timestamp,
                    "source_file": os.path.basename(filepath),
                    "post_type": "thread_op",
                })

            # Replies
            for reply in entry.get("replies", []):
                r_author = reply.get("author", "")
                r_content = reply.get("content", reply.get("body", ""))
                r_timestamp = reply.get("timestamp", "")
                if r_content:
                    posts.append({
                        "forum": forum,
                        "thread_id": thread_id,
                        "thread_title": thread_title,
                        "author": r_author,
                        "author_pgp": reply.get("author_pgp", ""),
                        "content": r_content,
                        "timestamp": r_timestamp,
                        "source_file": os.path.basename(filepath),
                        "post_type": "reply",
                    })

    except Exception as e:
        logger.error(f"Error parsing JSON forum file {filepath}: {e}")

    return posts


def parse_html_forum(filepath: str) -> List[Dict[str, Any]]:
    """
    Parse an HTML forum page. Extracts post containers with common forum HTML patterns.
    """
    posts = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()

        soup = BeautifulSoup(html, "html.parser")
        forum_name = os.path.basename(filepath).replace(".html", "")

        # Try common forum HTML patterns
        post_containers = (
            soup.find_all("div", class_=re.compile(r"post|message|entry", re.I)) or
            soup.find_all("article") or
            soup.find_all("tr", class_=re.compile(r"post|row", re.I))
        )

        if post_containers:
            for container in post_containers:
                author_el = container.find(class_=re.compile(r"author|user|poster|name", re.I))
                content_el = container.find(class_=re.compile(r"content|body|message|text", re.I))
                time_el = container.find("time") or container.find(class_=re.compile(r"date|time|timestamp", re.I))

                author = author_el.get_text(strip=True) if author_el else ""
                content = content_el.get_text(separator=" ", strip=True) if content_el else ""
                timestamp = ""
                if time_el:
                    timestamp = time_el.get("datetime", "") or time_el.get_text(strip=True)

                if content:
                    posts.append({
                        "forum": forum_name,
                        "thread_id": "",
                        "thread_title": soup.title.string.strip() if soup.title else "",
                        "author": author,
                        "author_pgp": "",
                        "content": content,
                        "timestamp": timestamp,
                        "source_file": os.path.basename(filepath),
                        "post_type": "html_extracted",
                    })
        else:
            # Fallback: extract all text content
            body_text = soup.get_text(separator=" ", strip=True)
            if body_text and len(body_text) > 50:
                posts.append({
                    "forum": forum_name,
                    "thread_id": "",
                    "thread_title": soup.title.string.strip() if soup.title else "",
                    "author": "",
                    "author_pgp": "",
                    "content": body_text[:2000],
                    "timestamp": "",
                    "source_file": os.path.basename(filepath),
                    "post_type": "html_fulltext",
                })

    except Exception as e:
        logger.error(f"Error parsing HTML forum file {filepath}: {e}")

    return posts


def scan_forum_directory() -> List[Dict[str, Any]]:
    """
    Scan all .json and .html files in data/forums/ and extract all posts.
    Returns a unified list of parsed post dictionaries.
    """
    forum_dir = find_forum_dir()
    if not forum_dir:
        logger.warning("No forum data directory found. Checked: " + str(FORUM_DATA_DIRS))
        return []

    all_posts = []
    logger.info(f"[ForumParser] Scanning directory: {forum_dir}")

    for filename in os.listdir(forum_dir):
        filepath = os.path.join(forum_dir, filename)
        if not os.path.isfile(filepath):
            continue

        if filename.endswith(".json"):
            posts = parse_json_forum(filepath)
            logger.info(f"  Parsed {len(posts)} posts from {filename}")
            all_posts.extend(posts)
        elif filename.endswith(".html") or filename.endswith(".htm"):
            posts = parse_html_forum(filepath)
            logger.info(f"  Parsed {len(posts)} posts from {filename}")
            all_posts.extend(posts)

    logger.info(f"[ForumParser] Total posts extracted: {len(all_posts)}")
    return all_posts


def normalize_forum_post(post: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a parsed forum post into the DarkTrace normalized observation schema
    compatible with CrawlerPipeline ingestion.
    """
    forum = post.get("forum", "Unknown Forum")
    author = post.get("author", "")
    content = post.get("content", "")
    timestamp = post.get("timestamp", "") or datetime.now(timezone.utc).isoformat()
    thread_title = post.get("thread_title", f"Post by {author}")

    content_hash = hashlib.sha256(
        (forum + author + content[:200]).encode("utf-8")
    ).hexdigest()[:16]

    metadata = {
        "forum": forum,
        "author": author,
        "thread_id": post.get("thread_id", ""),
        "source_file": post.get("source_file", ""),
        "post_type": post.get("post_type", ""),
        "author_pgp": post.get("author_pgp", ""),
        "hash": content_hash,
    }

    return {
        "source": "ForumParser",
        "source_type": "forum-post",
        "timestamp": timestamp,
        "service": forum.lower().replace(" ", "_"),
        "title": thread_title,
        "content": content,
        "metadata": metadata,
        "reference": f"forum://{forum.lower().replace(' ', '_')}/{post.get('thread_id', 'unknown')}/{author}",
        "reliability": 0.82,
        "collection_method": "ForumParserModule",
        "raw_reference": f"sha256:{content_hash}",
        "extracted_entities": None,  # Will be extracted by pipeline
        "favicon_murmur_hash": None,
    }


# CLI standalone test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    posts = scan_forum_directory()
    print(f"\n{'='*60}")
    print(f"Forum Parser Results: {len(posts)} posts found")
    print(f"{'='*60}")
    for i, p in enumerate(posts, 1):
        print(f"\n[{i}] Forum: {p['forum']} | Author: {p['author']} | Type: {p['post_type']}")
        print(f"    Thread: {p['thread_title']}")
        print(f"    Content: {p['content'][:120]}...")
        norm = normalize_forum_post(p)
        print(f"    Normalized: source={norm['source']}, service={norm['service']}, ref={norm['raw_reference']}")
