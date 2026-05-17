import unittest
import os
import sqlite3
import time
from src.core.usage_tracker import UsageTracker

class TestUsageTracker(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_usage_stats.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.tracker = UsageTracker(db_path=self.db_path, limit=100)

    def tearDown(self):
        # Give some time for background worker to finish
        time.sleep(0.5)
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except PermissionError:
                pass

    def test_add_request_per_script(self):
        script1 = "script1"
        script2 = "script2"

        self.tracker.add_request(script1, 10)
        self.tracker.add_request(script2, 5)

        # Wait for async writes
        time.sleep(0.5)

        self.assertEqual(self.tracker.get_count(script1), 10)
        self.assertEqual(self.tracker.get_count(script2), 5)
        self.assertEqual(self.tracker.get_count(), 15)

    def test_is_script_over_limit(self):
        script1 = "script1"
        self.tracker.add_request(script1, 20000)

        # Wait for async writes
        time.sleep(0.5)

        self.assertTrue(self.tracker.is_script_over_limit(script1, limit=20000))
        self.assertFalse(self.tracker.is_script_over_limit("script2", limit=20000))

    def test_get_script_counts(self):
        script1 = "script1"
        script2 = "script2"

        self.tracker.add_request(script1, 10)
        self.tracker.add_request(script2, 20)

        # Wait for async writes
        time.sleep(0.5)

        counts = self.tracker.get_script_counts()
        self.assertEqual(counts[script1], 10)
        self.assertEqual(counts[script2], 20)

if __name__ == "__main__":
    unittest.main()
