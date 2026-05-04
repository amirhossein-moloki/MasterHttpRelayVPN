import json
import os
import time
import threading
import logging
from datetime import datetime, timedelta

log = logging.getLogger("UsageTracker")

class UsageTracker:
    def __init__(self, filepath="usage_stats.json", limit=20000):
        self.filepath = filepath
        self.limit = limit
        self._lock = threading.Lock()
        self.stats = self._load_stats()
        self._check_reset()

    def _load_stats(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    return json.load(f)
            except:
                pass
        return {"count": 0, "last_reset": time.time()}

    def _save_stats(self):
        # Using a lock to prevent concurrent writes from different threads
        with self._lock:
            try:
                with open(self.filepath, "w") as f:
                    json.dump(self.stats, f)
            except Exception as e:
                log.error(f"Error saving usage stats: {e}")

    def _get_next_reset_time(self, last_reset_ts):
        last_reset_dt = datetime.fromtimestamp(last_reset_ts)
        # Reset at 10:30 AM
        reset_time = last_reset_dt.replace(hour=10, minute=30, second=0, microsecond=0)

        # If last reset was before 10:30 AM today, then next reset is today at 10:30 AM
        # But if last reset was after 10:30 AM today, next reset is tomorrow at 10:30 AM
        if last_reset_dt >= reset_time:
            reset_time += timedelta(days=1)

        return reset_time.timestamp()

    def _check_reset(self):
        with self._lock:
            now = time.time()
            # A more robust reset logic:
            # If current time has passed 10:30 AM and the last reset was before the most recent 10:30 AM, then reset.

            current_dt = datetime.fromtimestamp(now)
            today_1030 = current_dt.replace(hour=10, minute=30, second=0, microsecond=0)

            needs_save = False
            if now >= today_1030.timestamp():
                # Most recent reset should have been today at 10:30
                last_reset_dt = datetime.fromtimestamp(self.stats["last_reset"])
                if last_reset_dt < today_1030:
                    self.stats["count"] = 0
                    self.stats["last_reset"] = now # Or today_1030.timestamp()
                    needs_save = True
            else:
                # Most recent reset should have been yesterday at 10:30
                yesterday_1030 = today_1030 - timedelta(days=1)
                last_reset_dt = datetime.fromtimestamp(self.stats["last_reset"])
                if last_reset_dt < yesterday_1030:
                    self.stats["count"] = 0
                    self.stats["last_reset"] = now
                    needs_save = True

            if needs_save:
                # Can't call self._save_stats() here because it would double-lock
                try:
                    with open(self.filepath, "w") as f:
                        json.dump(self.stats, f)
                except Exception as e:
                    log.error(f"Error saving usage stats during reset: {e}")

    def add_request(self, count=1):
        self._check_reset()
        with self._lock:
            self.stats["count"] += count
        self._save_stats()

    def get_count(self):
        self._check_reset()
        with self._lock:
            return self.stats["count"]

    def get_remaining(self):
        return max(0, self.limit - self.get_count())

    def set_limit(self, limit):
        with self._lock:
            self.limit = limit

    def is_over_limit(self):
        return self.get_count() >= self.limit
