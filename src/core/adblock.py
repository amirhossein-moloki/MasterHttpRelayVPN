import os
import time
import logging
import json
import urllib.request
import asyncio
import re
from pathlib import Path

log = logging.getLogger("Adblock")

CACHE_FILE = Path("data/adblock_cache.json")

def parse_hosts(content: str) -> set[str]:
    """Parse hosts-format content and return a set of domains."""
    domains = set()
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Match "127.0.0.1 domain.com" or "0.0.0.0 domain.com" or just "domain.com"
        # Some lists just have one domain per line.
        parts = line.split()
        if len(parts) >= 2:
            domain = parts[1].lower()
        else:
            domain = parts[0].lower()

        # Basic domain validation
        if re.match(r"^[a-z0-9.-]+$", domain) and "." in domain:
            domains.add(domain)
    return domains

def load_all(urls: list[str]) -> list[str]:
    """Load cached domains from disk."""
    if not CACHE_FILE.exists():
        return []

    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)

        all_domains = set()
        for url in urls:
            if url in cache:
                all_domains.update(cache[url].get("domains", []))

        return list(all_domains)
    except Exception as e:
        log.warning("Failed to load adblock cache: %s", e)
        return []

async def refresh_all(urls: list[str], callback=None) -> None:
    """Download stale adblock lists and update cache."""
    if not urls:
        return

    # Create data dir if not exists
    os.makedirs("data", exist_ok=True)

    cache = {}
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except:
            pass

    updated = False
    now = time.time()
    # Refresh if older than 24 hours
    TTL = 24 * 3600

    for url in urls:
        entry = cache.get(url, {})
        last_refresh = entry.get("last_refresh", 0)

        if now - last_refresh < TTL and "domains" in entry:
            continue

        log.info("Refreshing adblock list: %s", url)
        try:
            # Run blocking I/O in thread
            content = await asyncio.to_thread(fetch_url, url)
            domains = parse_hosts(content)
            cache[url] = {
                "last_refresh": now,
                "domains": list(domains)
            }
            updated = True
        except Exception as e:
            log.warning("Failed to refresh %s: %s", url, e)

    if updated:
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache, f)

            if callback:
                all_domains = set()
                for url in urls:
                    if url in cache:
                        all_domains.update(cache[url].get("domains", []))
                callback(list(all_domains))
        except Exception as e:
            log.error("Failed to save adblock cache: %s", e)

def fetch_url(url: str) -> str:
    """Synchronous fetch of a URL."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MasterHttpRelayVPN/1.0"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")
