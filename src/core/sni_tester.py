"""
SNI Tester — verifies reachability of domains through specific IPs.

Useful for testing if certain domains are SNI-blocked or if they work
when fronted through specific Google IPs.
"""

import asyncio
import ssl
import time
import logging
from dataclasses import dataclass
from typing import Optional

log = logging.getLogger("SNITester")

@dataclass
class SNIResult:
    domain: str
    target_ip: str
    latency_ms: Optional[int] = None
    status_code: Optional[int] = None
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.latency_ms is not None

async def test_sni(domain: str, target_ip: str, timeout: float = 5.0) -> SNIResult:
    """
    Test reachability of a domain through a specific IP using HTTPS.
    """
    start_time = time.time()
    try:
        # Create SSL context that skips certificate verification
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        # Connect to IP:443 with SNI set to the domain we want to test
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(
                target_ip,
                443,
                ssl=ctx,
                server_hostname=domain,
            ),
            timeout=timeout,
        )

        # Send minimal HTTP HEAD request
        request = f"HEAD / HTTP/1.1\r\nHost: {domain}\r\nConnection: close\r\n\r\n"
        writer.write(request.encode())
        await writer.drain()

        # Read response header
        response = await asyncio.wait_for(reader.read(1024), timeout=timeout)

        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass

        if not response:
            return SNIResult(domain=domain, target_ip=target_ip, error="empty response")

        response_str = response.decode("utf-8", errors="ignore")
        if not response_str.startswith("HTTP/"):
            return SNIResult(domain=domain, target_ip=target_ip, error=f"invalid response: {response_str[:30]!r}")

        # Extract status code
        try:
            status_code = int(response_str.split(" ")[1])
        except (IndexError, ValueError):
            status_code = None

        elapsed_ms = int((time.time() - start_time) * 1000)
        return SNIResult(domain=domain, target_ip=target_ip, latency_ms=elapsed_ms, status_code=status_code)

    except asyncio.TimeoutError:
        return SNIResult(domain=domain, target_ip=target_ip, error="timeout")
    except ConnectionRefusedError:
        return SNIResult(domain=domain, target_ip=target_ip, error="connection refused")
    except ConnectionResetError:
        return SNIResult(domain=domain, target_ip=target_ip, error="connection reset")
    except OSError as e:
        return SNIResult(domain=domain, target_ip=target_ip, error=f"network error: {e.strerror or str(e)}")
    except Exception as e:
        return SNIResult(domain=domain, target_ip=target_ip, error=f"test failed: {type(e).__name__}")
