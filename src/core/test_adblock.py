import unittest
import os
import json
import shutil
from core.adblock import parse_hosts, load_all, CACHE_FILE

class TestAdblock(unittest.TestCase):
    def setUp(self):
        if CACHE_FILE.exists():
            CACHE_FILE.unlink()
        if not os.path.exists("data"):
            os.makedirs("data")

    def test_parse_hosts(self):
        content = """
# comment
127.0.0.1 ads.example.com
0.0.0.0 more-ads.com
just-a-domain.org
invalid_domain
127.0.0.1 ok.com # with comment
"""
        domains = parse_hosts(content)
        self.assertIn("ads.example.com", domains)
        self.assertIn("more-ads.com", domains)
        self.assertIn("just-a-domain.org", domains)
        self.assertIn("ok.com", domains)
        self.assertNotIn("invalid_domain", domains)

    def test_load_all_empty(self):
        urls = ["http://example.com/ads.txt"]
        domains = load_all(urls)
        self.assertEqual(domains, [])

    def test_load_all_cached(self):
        url = "http://example.com/ads.txt"
        cache = {
            url: {
                "last_refresh": 123456789,
                "domains": ["blocked.com", "ad-server.net"]
            }
        }
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f)

        domains = load_all([url])
        self.assertIn("blocked.com", domains)
        self.assertIn("ad-server.net", domains)

if __name__ == "__main__":
    unittest.main()
