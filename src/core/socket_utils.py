"""
Socket utilities for network optimization in restrictive environments.

Provides optimized socket creation and configuration, specifically targeting
DPI bypass and performance in high-latency, lossy networks (e.g. Iran).

Optimizations:
- TCP_NODELAY: Disable Nagle's algorithm for immediate packet dispatch.
- TCP_MAXSEG (MSS): Limit segment size to prevent fragmentation (PMTU issues).
- TCP_FASTOPEN: Reduce RTT by sending data in the initial SYN (where supported).
"""

import socket
import sys
import logging

log = logging.getLogger("SocketUtils")

# Recommended MTU for restrictive networks is 1360-1400.
# MSS = MTU - 40 (for IPv4/TCP headers). 1340 MSS corresponds to 1380 MTU.
DEFAULT_MSS = 1340

# OS-specific constants for TCP_FASTOPEN if missing in the socket module
if not hasattr(socket, "TCP_FASTOPEN"):
    if sys.platform == "linux":
        socket.TCP_FASTOPEN = 23
    elif sys.platform == "darwin":
        socket.TCP_FASTOPEN = 105
    elif sys.platform == "win32":
        # Windows uses a different API (ConnectEx) for TFO,
        # but we can try setting the option.
        socket.TCP_FASTOPEN = 15

def apply_optimized_socket_options(sock: socket.socket, mss: int = DEFAULT_MSS):
    """Apply performance and bypass optimizations to a TCP socket."""
    if sock.type != socket.SOCK_STREAM:
        return

    # 1. Disable Nagle's Algorithm (Immediate dispatch)
    try:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except OSError:
        pass

    # 2. Limit MSS (Prevent Fragmentation)
    # This is highly effective against DPI that chokes on fragmented packets
    # or networks with broken PMTU discovery.
    if mss > 0:
        try:
            if hasattr(socket, "TCP_MAXSEG"):
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_MAXSEG, mss)
            else:
                # Manual constant for Linux/Darwin if not in socket module
                TCP_MAXSEG = 2
                sock.setsockopt(socket.IPPROTO_TCP, TCP_MAXSEG, mss)
        except OSError as e:
            # Some OSs (like Windows) don't allow setting MSS directly on a socket
            # or require the socket to be in a specific state.
            log.debug("Could not set TCP_MAXSEG: %s", e)

    # 3. Reduce Buffer Bloat (Lower Latency)
    # TCP_NOTSENT_LOWAT limits the amount of unsent data in the socket write buffer.
    # This helps in maintaining lower RTT on high-latency links.
    if hasattr(socket, "TCP_NOTSENT_LOWAT"):
        try:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NOTSENT_LOWAT, 16384)
        except OSError:
            pass

    # 4. TCP Fast Open (Reduce Handshake RTT)
    if hasattr(socket, "TCP_FASTOPEN"):
        try:
            # On Linux, the value is the queue length for incoming TFO.
            # For a client socket, any non-zero value usually enables it.
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_FASTOPEN, 5)
        except OSError:
            pass

    # 5. Keepalive settings for long-lived connections
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        if sys.platform == "linux":
            # Idle time before sending keepalive probes (seconds)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
            # Interval between probes
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
            # Number of failed probes before closing
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 6)
        elif sys.platform == "darwin":
            # macOS uses TCP_KEEPALIVE instead of TCP_KEEPIDLE
            TCP_KEEPALIVE = 0x10
            sock.setsockopt(socket.IPPROTO_TCP, TCP_KEEPALIVE, 60)
    except OSError:
        pass

def create_optimized_socket(family=socket.AF_INET, mss: int = DEFAULT_MSS) -> socket.socket:
    """Create a new TCP socket with optimizations applied."""
    sock = socket.socket(family, socket.SOCK_STREAM)
    apply_optimized_socket_options(sock, mss=mss)
    return sock
