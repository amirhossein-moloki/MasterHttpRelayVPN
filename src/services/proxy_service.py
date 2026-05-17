import asyncio
import logging
import threading
import json
import urllib.request
from typing import Optional, Callable

from PyQt6.QtCore import QObject, pyqtSignal
from proxy.proxy_server import ProxyServer
from core.usage_tracker import UsageTracker
from core.paths import USAGE_DB_PATH, ensure_dirs

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
        # Ensure data directory exists
        ensure_dirs()

        self.usage_tracker = UsageTracker(
            db_path=self.config.get("usage_db", USAGE_DB_PATH),
            limit=total_limit
        )

    def _set_status(self, status: str):
        self.status_changed.emit(status)

    def update_config(self, config: dict):
        """Update service configuration and quota limits."""
        self.config = config
        script_ids = self.config.get("script_ids") or self.config.get("script_id")
        num_scripts = len(script_ids) if isinstance(script_ids, list) else (1 if script_ids else 0)
        total_limit = 20000 * num_scripts if num_scripts > 0 else 20000
        self.usage_tracker.set_limit(total_limit)

        if self.server:
            self.server.update_rule_groups(self.config)

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
            "history": tracker.get_history(days=7 if days <= 7 else days),
            "script_counts": tracker.get_script_counts()
        }

    def get_total_usage(self):
        return self.usage_tracker.get_total_stats()

    async def update_bypass_group(self, group_index: int) -> bool:
        """Fetch updated rules for a bypass group from its update_url."""
        groups = self.config.get("rule_groups", []) or self.config.get("bypass_groups", [])
        if group_index < 0 or group_index >= len(groups):
            return False

        group = groups[group_index]
        url = group.get("update_url")
        if not url:
            return False

        try:
            log.info(f"Updating bypass group '{group.get('name')}' from {url}")

            # Use run_in_executor to avoid blocking the event loop with synchronous urllib
            def fetch():
                with urllib.request.urlopen(url, timeout=15) as response:
                    return response.read().decode('utf-8')

            loop = asyncio.get_running_loop()
            content = await loop.run_in_executor(None, fetch)

            # Attempt to parse as JSON first, then fallback to line-separated
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    new_rules = [str(r) for r in data]
                elif isinstance(data, dict) and "rules" in data:
                    new_rules = [str(r) for r in data["rules"]]
                else:
                    new_rules = content.strip().splitlines()
            except json.JSONDecodeError:
                new_rules = content.strip().splitlines()

            new_rules = [r.strip() for r in new_rules if r.strip()]
            if new_rules:
                group["rules"] = new_rules
                # Save config
                # Note: This is a bit hacky since ProxyService shouldn't ideally know about ModernUI
                # but in this project the config is often shared/managed by the UI.
                # A better way is to have a config manager.
                # For now, we'll just update the group in memory.
                # The UI should handle the actual saving to file.
                return True
        except Exception as e:
            log.error(f"Failed to update bypass group '{group.get('name')}': {e}")

        return False
