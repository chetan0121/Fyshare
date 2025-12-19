import socket
import subprocess
import re
import platform
from typing import Optional

class IPManager:
    def __init__(self, priority_prefixes):
        self.prior_ip = ""
        self.max_points = 0
        self.prefixes = priority_prefixes

    def compare(self, new_ip: str, iface: str):
        score = 0
        for i, prefix in enumerate(self.prefixes):
            if iface.startswith(prefix):
                score = len(self.prefixes)-i
                break

        if score >= self.max_points:
            self.prior_ip   = new_ip
            self.max_points = score

def get_local_ip() -> str:
    """Get local IP address"""
    ip = get_local_ip_socket()

    if not ip:
        system = platform.system().lower()
        if system == "linux" or system == "darwin":
            ip = get_local_ip_unix()
    
    if ip:
        return ip
    return "127.0.0.1"
    
def get_local_ip_socket() -> str:
    """Get IP using common socket/UDP method"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            ip = str(s.getsockname()[0])
            if is_valid_ip(ip):
                return ip
    except:
        pass
    return ""

def get_local_ip_unix() -> str:
    """Get IP on Unix-like systems"""
    try:
        # Try 'ifconfig' command
        result = subprocess.run(['ifconfig'],
                            capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            ip = _parse_ifconfig_output(result.stdout)
            if ip:
                return ip
    except:
        pass

    try:
        # Try 'ip' command
        result = subprocess.run(['ip', 'addr', 'show'],
                            capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            ip = _parse_ip_output(result.stdout)
            return ip
    except:
        pass

    return ""

def _parse_ip_output(output: str) -> str:
    """Parse output of 'ip addr show' command"""
    exclude_prefixes = ("lo", "tun", "tap", "wg", "ppp", "ccmni")
    priority_prefixes = ("wlan", "wl", "wifi", "ath", "eth", "en")

    current_iface: Optional[str] = None
    ip_manager = IPManager(priority_prefixes)
    
    for line in output.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # Get interface name
        if line[0].isdigit():
            parts = line.split(':')
            if len(parts) >= 2:
                current_iface = parts[1].strip().lower()
                if any(current_iface.startswith(i) for i in exclude_prefixes):
                    current_iface = None
            continue

        if current_iface is None:
            continue

        # Look for IPv4 address (skip inet6)
        if 'inet ' in line:
            match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', line)
            if match:
                ip = match.group(1)
                if is_valid_ip(ip):
                    ip_manager.compare(ip, current_iface)

    return ip_manager.prior_ip   

def _parse_ifconfig_output(output: str) -> str:
    """Parse output of 'ifconfig' command"""
    exclude_prefixes = ("lo", "tun", "tap", "wg", "ppp", "ccmni")
    priority_prefixes = ("wlan", "wl", "wifi", "ath", "eth", "en")

    current_iface: Optional[str] = None
    ip_manager = IPManager(priority_prefixes)
    
    for line in output.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # Get interface name
        if 'flags' in line or 'encap' in line:
            parts = line.split(':', 1)[0].split()
            current_iface = parts[0].lower()
            if any(current_iface.startswith(i) for i in exclude_prefixes):
                current_iface = None
            continue

        if current_iface is None:
            continue
        
        # Look for IPv4 address (skip inet6)
        if 'inet ' in line:
            match = re.search(r'inet.*?(\d+\.\d+\.\d+\.\d+)', line)
            if match:
                ip = match.group(1)
                if is_valid_ip(ip):
                    ip_manager.compare(ip, current_iface)

    return ip_manager.prior_ip

def is_valid_ip(ip: str) -> bool:
    """Check if IP is valid IPv4 and not special/reserved"""
    ip = ip.strip()
    if not ip:
        return False
    
    # Check for loopback, link-local etc.
    if (
        ip.startswith("127.") or
        ip.startswith("169.254.") or
        ip.startswith("0.") or
        ip.startswith("255.")
    ):
        return False
    
    # Basic IP validation
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    
    try:
        if 224 <= int(parts[0]) <= 255:
            return False
        
        for part in parts:
            num = int(part)
            if num < 0 or num > 255:
                return False
    except (ValueError, ValueError):
        return False
    
    return True
