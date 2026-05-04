import asyncio
import logging
import threading
from typing import Optional, Callable

from PyQt6.QtCore import QObject, pyqtSignal
from proxy.proxy_server import ProxyServer

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
        self.server = ProxyServer(self.config)

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

    def get_usage(self):
        if self.server and self.server.fronter and self.server.fronter._usage_tracker:
            tracker = self.server.fronter._usage_tracker
            return {
                "count": tracker.get_count(),
                "limit": tracker.limit,
                "remaining": tracker.get_remaining(),
                "percent": (tracker.get_count() / tracker.limit) * 100 if tracker.limit > 0 else 0
            }
        return None
