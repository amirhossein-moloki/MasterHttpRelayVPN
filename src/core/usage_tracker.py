import sqlite3
import os
import time
import threading
import logging
import queue
from datetime import datetime, timedelta

log = logging.getLogger("UsageTracker")

class UsageTracker:
    def __init__(self, db_path="usage_stats.db", limit=20000):
        self.db_path = db_path
        self.limit = limit
        self._lock = threading.Lock()
        self._queue = queue.Queue()
        self._init_db()

        self._worker_thread = threading.Thread(target=self._db_worker, daemon=True)
        self._worker_thread.start()

    def _init_db(self):
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # Table for daily execution count (Apps Script quota)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_quota (
                    date TEXT PRIMARY KEY,
                    count INTEGER DEFAULT 0
                )
            """)
            # Table for detailed traffic logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS traffic_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    host TEXT,
                    bytes_sent INTEGER,
                    bytes_received INTEGER
                )
            """)
            # Indexing for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_traffic_timestamp ON traffic_logs(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_traffic_host ON traffic_logs(host)")
            conn.commit()
            conn.close()

    def _db_worker(self):
        """Background worker to handle DB writes without blocking the event loop."""
        conn = sqlite3.connect(self.db_path)
        while True:
            try:
                task = self._queue.get()
                if task is None: break # Signal to stop

                type, data = task
                cursor = conn.cursor()
                if type == "quota":
                    today, count = data
                    cursor.execute("""
                        INSERT INTO daily_quota (date, count) VALUES (?, ?)
                        ON CONFLICT(date) DO UPDATE SET count = count + ?
                    """, (today, count, count))
                elif type == "traffic":
                    ts, host, sent, received = data
                    cursor.execute("""
                        INSERT INTO traffic_logs (timestamp, host, bytes_sent, bytes_received)
                        VALUES (?, ?, ?, ?)
                    """, (ts, host, sent, received))

                conn.commit()
                self._queue.task_done()
            except Exception as e:
                log.error(f"DB Worker error: {e}")
                time.sleep(1) # Simple backoff

    def _get_today_str(self):
        now = datetime.now()
        reset_time = now.replace(hour=10, minute=30, second=0, microsecond=0)
        if now < reset_time:
            return (now - timedelta(days=1)).strftime("%Y-%m-%d")
        return now.strftime("%Y-%m-%d")

    def add_request(self, count=1):
        """Record Apps Script executions for quota tracking (Async)."""
        today = self._get_today_str()
        self._queue.put(("quota", (today, count)))

    def add_traffic(self, host, bytes_sent, bytes_received):
        """Record detailed traffic log (Async)."""
        self._queue.put(("traffic", (time.time(), host, bytes_sent, bytes_received)))

    def get_count(self):
        """Get today's execution count (Sync - used for display/limit checks)."""
        today = self._get_today_str()
        with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT count FROM daily_quota WHERE date = ?", (today,))
                row = cursor.fetchone()
                conn.close()
                return row[0] if row else 0
            except Exception as e:
                log.error(f"Error getting count from DB: {e}")
                return 0

    def get_remaining(self):
        return max(0, self.limit - self.get_count())

    def is_over_limit(self):
        return self.get_count() >= self.limit

    def get_top_hosts(self, limit=10, days=1):
        """Get top hosts by total traffic in the last N days."""
        since = time.time() - (days * 86400)
        with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT host, SUM(bytes_sent), SUM(bytes_received), COUNT(*)
                    FROM traffic_logs
                    WHERE timestamp > ?
                    GROUP BY host
                    ORDER BY (SUM(bytes_sent) + SUM(bytes_received)) DESC
                    LIMIT ?
                """, (since, limit))
                rows = cursor.fetchall()
                conn.close()
                return [
                    {
                        "host": r[0],
                        "sent": r[1] or 0,
                        "received": r[2] or 0,
                        "total": (r[1] or 0) + (r[2] or 0),
                        "requests": r[3]
                    } for r in rows
                ]
            except Exception as e:
                log.error(f"Error getting top hosts: {e}")
                return []

    def get_history(self, days=7):
        """Get daily traffic history for charts."""
        with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT date(timestamp, 'unixepoch', 'localtime') as day,
                           SUM(bytes_sent), SUM(bytes_received)
                    FROM traffic_logs
                    WHERE timestamp > ?
                    GROUP BY day
                    ORDER BY day ASC
                """, (time.time() - (days * 86400),))
                rows = cursor.fetchall()
                conn.close()
                return [{"day": r[0], "sent": r[1] or 0, "received": r[2] or 0} for r in rows]
            except Exception as e:
                log.error(f"Error getting history: {e}")
                return []

    def get_total_stats(self):
        """Get total requests and total bytes transferred (all time)."""
        with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                # Total Apps Script executions (from daily_quota table)
                cursor.execute("SELECT SUM(count) FROM daily_quota")
                total_req = cursor.fetchone()[0] or 0

                # Total bytes from traffic_logs
                cursor.execute("SELECT SUM(bytes_sent), SUM(bytes_received) FROM traffic_logs")
                row = cursor.fetchone()
                conn.close()
                sent = row[0] or 0
                received = row[1] or 0
                return {
                    "total_requests": total_req,
                    "total_bytes": sent + received,
                    "sent": sent,
                    "received": received
                }
            except Exception as e:
                log.error(f"Error getting total stats: {e}")
                return {"total_requests": 0, "total_bytes": 0, "sent": 0, "received": 0}
