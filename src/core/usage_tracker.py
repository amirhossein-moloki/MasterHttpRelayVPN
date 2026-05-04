import json
import os
import time
import threading
import logging
from datetime import datetime, timedelta

log = logging.getLogger("UsageTracker")

class UsageTracker:
    def __init__(self, filepath="usage_stats.json", limit=20000, history_days=30):
        self.filepath = filepath
        self.limit = limit
        self.history_days = history_days
        self._lock = threading.Lock()
        self.stats = self._load_stats()
        self._check_reset()

    def _load_stats(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    data = json.load(f)
                    # Ensure basic structure
                    if "count" not in data: data["count"] = 0
                    if "last_reset" not in data: data["last_reset"] = time.time()
                    if "history" not in data: data["history"] = {}
                    return data
            except Exception as e:
                log.error(f"Error loading usage stats: {e}")
        return {"count": 0, "last_reset": time.time(), "history": {}}

    def _save_stats(self):
        with self._lock:
            try:
                with open(self.filepath, "w") as f:
                    json.dump(self.stats, f)
            except Exception as e:
                log.error(f"Error saving usage stats: {e}")

    def _get_today_str(self):
        return datetime.now().strftime("%Y-%m-%d")

    def _check_reset(self):
        with self._lock:
            now = time.time()
            current_dt = datetime.fromtimestamp(now)
            today_1030 = current_dt.replace(hour=10, minute=30, second=0, microsecond=0)

            needs_reset = False
            if now >= today_1030.timestamp():
                last_reset_dt = datetime.fromtimestamp(self.stats["last_reset"])
                if last_reset_dt < today_1030:
                    needs_reset = True
            else:
                yesterday_1030 = today_1030 - timedelta(days=1)
                last_reset_dt = datetime.fromtimestamp(self.stats["last_reset"])
                if last_reset_dt < yesterday_1030:
                    needs_reset = True

            if needs_reset:
                self.stats["count"] = 0
                self.stats["last_reset"] = now

            # Cleanup old history
            history = self.stats.get("history", {})
            if history:
                cutoff = (datetime.now() - timedelta(days=self.history_days)).strftime("%Y-%m-%d")
                keys_to_delete = [k for k in history.keys() if k < cutoff]
                for k in keys_to_delete:
                    del history[k]

            if needs_reset or (history and keys_to_delete):
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

    def record_site_usage(self, host, upload_bytes, download_bytes, errored=False):
        self._check_reset()
        today = self._get_today_str()
        with self._lock:
            history = self.stats.setdefault("history", {})
            day_data = history.setdefault(today, {"total_requests": 0, "total_upload": 0, "total_download": 0, "hosts": {}})

            day_data["total_requests"] += 1
            day_data["total_upload"] += upload_bytes
            day_data["total_download"] += download_bytes

            host_data = day_data["hosts"].setdefault(host, {"requests": 0, "upload": 0, "download": 0, "errors": 0})
            host_data["requests"] += 1
            host_data["upload"] += upload_bytes
            host_data["download"] += download_bytes
            if errored:
                host_data["errors"] += 1
        self._save_stats()

    def get_count(self):
        self._check_reset()
        with self._lock:
            return self.stats["count"]

    def get_history(self):
        self._check_reset()
        with self._lock:
            return self.stats.get("history", {})

    def get_remaining(self):
        return max(0, self.limit - self.get_count())

    def set_limit(self, limit):
        with self._lock:
            self.limit = limit

    def is_over_limit(self):
        return self.get_count() >= self.limit
