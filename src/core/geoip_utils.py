import ipaddress
import logging
import os

log = logging.getLogger("GeoIP")

class IPBypassChecker:
    def __init__(self, manual_cidrs=None, bypass_iran=True):
        self.iran_networks = []
        if bypass_iran:
            # Load from file if exists, otherwise use fallback
            file_path = os.path.join("data", "iran_ips.txt")
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r") as f:
                        for line in f:
                            cidr = line.strip()
                            if cidr:
                                try:
                                    self.iran_networks.append(ipaddress.ip_network(cidr))
                                except ValueError:
                                    continue
                except Exception as e:
                    log.error(f"Error loading Iran IP ranges from file: {e}")

            if not self.iran_networks:
                # Fallback to some common ranges if file load failed
                fallback = ["2.176.0.0/12", "5.160.0.0/12", "31.24.0.0/14", "31.56.0.0/13"]
                for cidr in fallback:
                    self.iran_networks.append(ipaddress.ip_network(cidr))

        self.manual_networks = []
        if manual_cidrs:
            for cidr in manual_cidrs:
                try:
                    self.manual_networks.append(ipaddress.ip_network(cidr))
                except ValueError:
                    # Might be a single IP
                    try:
                        self.manual_networks.append(ipaddress.ip_network(f"{cidr}/32"))
                    except ValueError:
                        log.warning(f"Invalid CIDR or IP in manual bypass list: {cidr}")

    def is_bypassed(self, ip_str):
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return False

        # Check manual list first (Override)
        for network in self.manual_networks:
            if ip in network:
                return True

        # Check Iran ranges
        for network in self.iran_networks:
            if ip in network:
                return True

        return False
