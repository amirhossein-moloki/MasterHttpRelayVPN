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
            # Migration: check if daily_quota has script_id
            cursor.execute("PRAGMA table_info(daily_quota)")
            columns = [info[1] for info in cursor.fetchall()]

            if columns and "script_id" not in columns:
                log.info("Migrating daily_quota table to include script_id")
                # Rename old table
                cursor.execute("ALTER TABLE daily_quota RENAME TO daily_quota_old")
                # Create new table
                cursor.execute("""
                    CREATE TABLE daily_quota (
                        date TEXT,
                        script_id TEXT,
                        count INTEGER DEFAULT 0,
                        PRIMARY KEY (date, script_id)
                    )
                """)
                # Copy data (assign 'default' to old records)
                cursor.execute("""
                    INSERT INTO daily_quota (date, script_id, count)
                    SELECT date, 'default', count FROM daily_quota_old
                """)
                cursor.execute("DROP TABLE daily_quota_old")
            else:
                # Table for daily execution count (Apps Script quota)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS daily_quota (
                        date TEXT,
                        script_id TEXT,
                        count INTEGER DEFAULT 0,
                        PRIMARY KEY (date, script_id)
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
                    today, script_id, count = data
                    cursor.execute("""
                        INSERT INTO daily_quota (date, script_id, count) VALUES (?, ?, ?)
                        ON CONFLICT(date, script_id) DO UPDATE SET count = count + ?
                    """, (today, script_id, count, count))
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
        """Get the date string for the current quota day (starts at 10:30 AM)."""
        return self._get_quota_day_str(time.time())

    def _get_quota_day_str(self, ts):
        dt = datetime.fromtimestamp(ts)
        reset_time = dt.replace(hour=10, minute=30, second=0, microsecond=0)
        if dt < reset_time:
            return (dt - timedelta(days=1)).strftime("%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")

    def get_current_quota_day_start(self):
        """Get the unix timestamp for the start of the current quota day (10:30 AM)."""
        dt_now = datetime.now()
        reset_time = dt_now.replace(hour=10, minute=30, second=0, microsecond=0)
        if dt_now < reset_time:
            return (reset_time - timedelta(days=1)).timestamp()
        return reset_time.timestamp()

    def add_request(self, script_id, count=1):
        """Record Apps Script executions for quota tracking (Async)."""
        today = self._get_today_str()
        self._queue.put(("quota", (today, script_id, count)))

    def add_traffic(self, host, bytes_sent, bytes_received):
        """Record detailed traffic log (Async)."""
        self._queue.put(("traffic", (time.time(), host, bytes_sent, bytes_received)))

    def get_count(self, script_id=None):
        """Get today's execution count for a specific script or total (Sync)."""
        today = self._get_today_str()
        with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                if script_id:
                    cursor.execute("SELECT count FROM daily_quota WHERE date = ? AND script_id = ?", (today, script_id))
                    row = cursor.fetchone()
                    conn.close()
                    return (row[0] or 0) if row else 0
                else:
                    cursor.execute("SELECT SUM(count) FROM daily_quota WHERE date = ?", (today,))
                    row = cursor.fetchone()
                    conn.close()
                    return (row[0] or 0) if row else 0
            except Exception as e:
                log.error(f"Error getting count from DB: {e}")
                return 0

    def get_script_counts(self):
        """Get today's counts for all scripts."""
        today = self._get_today_str()
        with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT script_id, count FROM daily_quota WHERE date = ?", (today,))
                rows = cursor.fetchall()
                conn.close()
                return {r[0]: r[1] for r in rows}
            except Exception as e:
                log.error(f"Error getting script counts from DB: {e}")
                return {}

    def set_limit(self, limit):
        with self._lock:
            self.limit = limit

    def get_remaining(self):
        return max(0, self.limit - self.get_count())

    def is_over_limit(self):
        return self.get_count() >= self.limit

    def is_script_over_limit(self, script_id, limit=20000):
        return self.get_count(script_id) >= limit

    def get_top_hosts(self, limit=10, days=1):
        """Get top hosts by total traffic. If days=1, shows data since 10:30 AM today."""
        if days == 1:
            since = self.get_current_quota_day_start()
        else:
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
        """Get daily traffic history for charts, grouped by quota days (10:30 to 10:30)."""
        # We shift the timestamp by 10 hours and 30 minutes (37800 seconds) backwards
        # so that 10:30 AM becomes 00:00 AM in SQLite's date calculation.
        shift = 10 * 3600 + 30 * 60
        with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute(f"""
                    SELECT date(timestamp - {shift}, 'unixepoch', 'localtime') as day,
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
