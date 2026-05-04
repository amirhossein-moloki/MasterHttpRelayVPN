import asyncio
import logging
import threading
from typing import Optional, Callable

from PyQt6.QtCore import QObject, pyqtSignal
from proxy.proxy_server import ProxyServer
from core.usage_tracker import UsageTracker

log = logging.getLogger("ProxyService")

class ProxyService(QObject):
    status_changed = pyqtSignal(str)

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.server: Optional[ProxyServer] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None
        self.is_running = False

        # Initialize persistent usage tracker
        script_ids = self.config.get("script_ids") or self.config.get("script_id")
        num_scripts = len(script_ids) if isinstance(script_ids, list) else (1 if script_ids else 0)
        total_limit = 20000 * num_scripts if num_scripts > 0 else 20000
        self.usage_tracker = UsageTracker(
            db_path=self.config.get("usage_db", "usage_stats.db"),
            limit=total_limit
        )

    def _set_status(self, status: str):
        self.status_changed.emit(status)

    def start(self):
        if self.is_running:
            return

        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self.is_running = True

    def _run_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        self._set_status("starting")
        self.server = ProxyServer(self.config, usage_tracker=self.usage_tracker)

        try:
            self.loop.run_until_complete(self.server.start(on_ready=lambda: self._set_status("running")))
        except asyncio.CancelledError:
            log.info("Proxy server task cancelled")
        except Exception as e:
            log.error(f"Proxy server error: {e}")
            self._set_status(f"error: {e}")
        finally:
            self._set_status("stopped")
            self.is_running = False

    def stop(self):
        if not self.is_running or not self.loop:
            return

        self._set_status("stopping")

        async def _stop():
            if self.server:
                await self.server.stop()

            # Cancel all tasks
            tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            self.loop.stop()

        self.loop.call_soon_threadsafe(lambda: asyncio.ensure_future(_stop(), loop=self.loop))

        if self.thread:
            self.thread.join(timeout=5)
        self.is_running = False

    def get_stats(self):
        if self.server and self.server.fronter:
            return self.server.fronter.stats_snapshot()
        return None

    def get_usage(self, days=1):
        tracker = self.usage_tracker
        return {
            "count": tracker.get_count(),
            "limit": tracker.limit,
            "remaining": tracker.get_remaining(),
            "percent": (tracker.get_count() / tracker.limit) * 100 if tracker.limit > 0 else 0,
            "top_hosts": tracker.get_top_hosts(limit=10, days=days),
            "history": tracker.get_history(days=7 if days <= 7 else days)
        }

    def get_total_usage(self):
        return self.usage_tracker.get_total_stats()
