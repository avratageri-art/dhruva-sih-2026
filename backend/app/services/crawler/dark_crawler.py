"""
Bridge module exposing DarkCrawler within the app.services.crawler package.
"""
import sys
import os

# Ensure backend root is on sys.path
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from dark_crawler import DarkCrawler, REGEX_PATTERNS, DEFAULT_TOR_PROXIES, DEFAULT_INTEL_FILE

__all__ = ["DarkCrawler", "REGEX_PATTERNS", "DEFAULT_TOR_PROXIES", "DEFAULT_INTEL_FILE"]
