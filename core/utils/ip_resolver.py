import os
import socket
import subprocess
import re
from typing import Final, Optional
from . import style_manager as S
from . import helper

# Global variables
exclude_prefixes: Final[tuple[str, ...]] = ("lo", "tun", "tap", "wg", "ppp", "ccmni")
priority_prefixes: Final[tuple[str, ...]] = ("wlan", "wl", "wifi", "ath", "eth", "en")

def is_unix_like()-> bool:
    """
    Return True if the current system is Unix Like system
    - e.g. Linux, Darwin, Android
    """
    return os.name == 'posix'

def get_local_ip() -> str:
    """Get local IP address"""
    ip = get_local_ip_socket()
    
    if not ip and is_unix_like():
        ip = get_local_ip_unix()
    
    return ip if ip else "127.0.0.1"

def get_local_ip_socket() -> str:
    """Get IP using common socket/UDP method"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            ip = str(s.getsockname()[0])
            if is_hostable_ipv4(ip): 
                return ip
    except Exception:
        pass
    return ""

def get_local_ip_unix() -> str:
    """Get IP on Unix-like systems"""
    # Try 'ip addr show' first (Best for modern Android & Linux)
    try:
        result = subprocess.run(['ip', 'addr', 'show'],
                            capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            ip = _parse_ip_output(result.stdout)
            return ip
    except PermissionError:
        S.Style.print(
            "\nPermission denied: Unable to run \'ip addr show\' command", 
            S.TextStyle.BOLD, 
            S.Color.YELLOW
        )
    except KeyboardInterrupt:
        raise
    except Exception:
        pass
    
    # 2. Try 'ifconfig' (Fallback for macOS, Android, legacy linux)
    try:
        result = subprocess.run(['ifconfig'],
                            capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            ip = _parse_ifconfig_output(result.stdout)
            if ip:
                return ip
    except PermissionError:
        S.Style.print(
            "\nPermission denied: Unable to run \'ifconfig\' command", 
            S.TextStyle.BOLD, 
            S.Color.YELLOW
        )
    except KeyboardInterrupt:
        raise
    except Exception:
        pass

    return ""


class _IPManager:
    """Score and track the best matching IP address by interface priority."""
    def __init__(self, priority_prefixes):
        self.prior_ip = ""
        self.max_points = 0
        self.prefixes = priority_prefixes

    def add_ip(self, new_ip: str, iface: str) -> None:
        """Track an IP if its interface has higher priority than the current best.
        
        Args:
            new_ip: IP address to consider.
            iface: Interface name to score against priorities.
        """
        score = 0
        for i, prefix in enumerate(self.prefixes):
            if iface.startswith(prefix):
                score = len(self.prefixes)-i
                break

        # Override with new-ip if same prefix
        if score >= self.max_points:
            self.prior_ip   = new_ip
            self.max_points = score

def _parse_ip_output(output: str) -> str:
    """Parse output of 'ip addr show' command"""

    current_iface: Optional[str] = None
    ip_manager = _IPManager(priority_prefixes)
    
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

        # Look for IPv4 address (skip inet6)
        if current_iface and 'inet ' in line:
            match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', line)
            if match:
                ip = match.group(1)
                if is_hostable_ipv4(ip):
                    ip_manager.add_ip(ip, current_iface)

    return ip_manager.prior_ip   

def _parse_ifconfig_output(output: str) -> str:
    """Parse output of 'ifconfig' command"""
    
    current_iface: Optional[str] = None
    ip_manager = _IPManager(priority_prefixes)
    
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

        # Look for IPv4 address (skip inet6)
        if current_iface and 'inet ' in line:
            match = re.search(r'inet.*?(\d+\.\d+\.\d+\.\d+)', line)
            if match:
                ip = match.group(1)
                if is_hostable_ipv4(ip):
                    ip_manager.add_ip(ip, current_iface)

    return ip_manager.prior_ip

def is_hostable_ipv4(ip: str) -> bool:
    """Check if a string is a usable IPv4 address for hosting a LAN server.
    
    Returns False for loopback (127.x.x.x), link-local (169.254.x.x),
    unspecified (0.x.x.x), or reserved/multicast (224.x.x.x-255.x.x.x) ranges.
    
    Args:
        ip: IPv4 address as a string.
    
    Returns:
        True if the address is valid and usable for LAN hosting.
    """
    ip = ip.strip()
    
    # Check for empty string, loopback-ip, link-local ip etc.
    if not ip or any(ip.startswith(s) for s in ["127.", "169.254.", "0.", "224.", "255."]):
        return False
    
    return is_valid_ipv4(ip)
    
def is_valid_ipv4(ip: str) -> bool:
    """Check if a string is a valid IPv4 address.
    
    Args:
        ip: IPv4 address as a string (e.g., '192.168.1.1').
    
    Returns:
        True if the address has four octets in range 0-255.
    """
    # Verify four decimal octets
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    
    # Validate the numbers
    for p in parts:
        num = helper.try_parse_int(p)
        if num is None:
            return False

        if not (0 <= num <= 255):
            return False     

    return True
