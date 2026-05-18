import asyncio
import time
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from relay.domain_fronter import DomainFronter

class TestFronterPerf(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.config = {
            "script_ids": ["sid1", "sid2", "sid3"],
            "google_ip": "1.1.1.1",
            "front_domain": "www.google.com"
        }
        self.usage_tracker = MagicMock()
        self.usage_tracker.get_count.return_value = 0
        self.usage_tracker.is_script_over_limit.return_value = False
        self.fronter = DomainFronter(self.config, usage_tracker=self.usage_tracker)

    async def test_strike_system_failure(self):
        # 3 failures should blacklist
        sid = "sid1"
        self.fronter._record_sid_perf(sid, 1.0, False) # Strike 1
        self.fronter._record_sid_perf(sid, 1.0, False) # Strike 2
        self.assertFalse(self.fronter._is_sid_blacklisted(sid))
        self.fronter._record_sid_perf(sid, 1.0, False) # Strike 3 -> Blacklist
        self.assertTrue(self.fronter._is_sid_blacklisted(sid))

    async def test_strike_system_slowness(self):
        # 3 slow responses should blacklist
        sid = "sid2"
        self.fronter._record_sid_perf(sid, 16.0, True) # Strike 1 (slow)
        self.fronter._record_sid_perf(sid, 16.0, True) # Strike 2 (slow)
        self.assertFalse(self.fronter._is_sid_blacklisted(sid))
        self.fronter._record_sid_perf(sid, 16.0, True) # Strike 3 (slow) -> Blacklist
        self.assertTrue(self.fronter._is_sid_blacklisted(sid))

    async def test_strike_reset_on_fast_success(self):
        sid = "sid3"
        self.fronter._record_sid_perf(sid, 1.0, False) # Strike 1
        self.fronter._record_sid_perf(sid, 1.0, False) # Strike 2
        self.fronter._record_sid_perf(sid, 1.0, True)  # Fast success -> Reset
        self.fronter._record_sid_perf(sid, 1.0, False) # Strike 1
        self.fronter._record_sid_perf(sid, 1.0, False) # Strike 2
        self.assertFalse(self.fronter._is_sid_blacklisted(sid))

    async def test_relay_single_records_perf(self):
        # Mock _acquire and read_http_response
        mock_writer = MagicMock()
        mock_writer.drain = AsyncMock()
        mock_writer.close = MagicMock()
        mock_reader = MagicMock()
        mock_reader.at_eof = MagicMock(return_value=False)

        # Mock self._acquire directly to return sid, reader, writer, created
        # Wait, _acquire only returns (reader, writer, created)
        self.fronter._acquire = AsyncMock(return_value=(mock_reader, mock_writer, time.time()))

        # Status line + headers + double newline + empty body
        mock_response = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n{}"

        with patch("relay.domain_fronter.read_http_response", AsyncMock(return_value=(200, {"content-length": "2"}, b"{}"))), \
             patch("relay.domain_fronter.parse_relay_response", return_value=mock_response):

            # Use sid_for_key to get the actual sid used
            host_key = self.fronter._host_key("http://test.com")
            sid = self.fronter._script_id_for_key(host_key)

            await self.fronter._relay_single({"u": "http://test.com"})

            # Should have 0 strikes initially (because it succeeded fast)
            self.assertEqual(self.fronter._sid_strikes.get(sid, 0), 0)

            # Simulate failure in inner try block of _relay_single
            with patch("relay.domain_fronter.read_http_response", side_effect=Exception("test error")):
                try:
                    await self.fronter._relay_single({"u": "http://test.com"})
                except:
                    pass
                self.assertEqual(self.fronter._sid_strikes.get(sid, 0), 1)

if __name__ == "__main__":
    unittest.main()
