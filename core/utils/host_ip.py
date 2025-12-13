import socket
import subprocess
import re
import platform
from . import logger

_exclude_prefixes = ("lo", "tun", "tap", "wg", "ppp", "ccmni", 
                    "docker", "veth", "vmnet", "virbr", "gif")
_priority_prefixes = ("wlan", "wl", "wifi", "ath", "eth", "en")

class IPManager:
    def __init__(self):
        self.prior_ip = ""
        self.max_points = 0

    def compare(self, new_ip: str, iface: str):
        score = 0
        for i, prefix in enumerate(_priority_prefixes):
            if iface.startswith(prefix):
                score = len(_priority_prefixes)-i
                break

        if score >= self.max_points:
            self.prior_ip = new_ip
            self.max_points = score

def get_local_ip() -> str:
    """Get local IP address"""

    # Try UDP socket method (widely used)
    ip = get_local_ip_socket()
    if ip:
        return ip

    # Get core system as string(in lower-case)
    system = platform.system().lower()
    
    # Try system specific commands to get ip
    if system == "linux" or system == "darwin":  # Linux, macOS, Android
        return get_local_ip_unix()
    elif system == "windows":
        return get_local_ip_windows()
    else:
        return get_local_ip_fallback()
    
def get_local_ip_socket() -> str:
    """Get IP using common socket/UDP method"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            ip = str(s.getsockname()[0])
            if is_valid_ip(ip):
                return ip
    except Exception as e:
        logger.print_warning(f"Failed to get ip using socket method: {str(e)}")
        
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
    except Exception as e:
        logger.print_warning(f"Failed to get ip using ifconfig method: {str(e)}")

    try:
        # Try 'ip' command
        result = subprocess.run(['ip', 'addr', 'show'],
                            capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            ip = _parse_ip_output(result.stdout)
            if ip:
                return ip
    except Exception as e:
        logger.print_warning(f"Failed to get ip using ip_command method: {str(e)}")

    return get_local_ip_fallback()

def get_local_ip_windows() -> str:
    """Get IP on Windows"""
    try:
        result = subprocess.run(
            'ipconfig',
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            ip = _parse_ipconfig_output(result.stdout)
            if ip:
                logger.print_info(f"Got IPConfig: {ip}")
                return ip
    except Exception as e:
        logger.print_warning(f"Failed to get ip using ipconfig method: {str(e)}")

    return get_local_ip_fallback()    

def _parse_ip_output(output: str) -> str:
    """Parse output of 'ip addr show' command"""
    current_iface: str | None = None
    ip_manager = IPManager()
    
    for line in output.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # Get interface name
        if line[0].isdigit():
            parts = line.split(':')
            if len(parts) >= 2:
                current_iface = parts[1].strip().lower()
                if any(current_iface.startswith(i) for i in _exclude_prefixes):
                    current_iface = None
            continue

        if current_iface is None:
            continue

        # Look for IPv4 address
        if 'inet ' in line:
            match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', line)
            if match:
                ip = match.group(1)
                if is_valid_ip(ip):
                    ip_manager.compare(ip, current_iface)

    return ip_manager.prior_ip   

def _parse_ifconfig_output(output: str) -> str:
    """Parse output of 'ifconfig' command"""
    current_iface: str | None = None
    ip_manager = IPManager()
    
    for line in output.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # Get interface name (non-empty line that doesn't start with whitespace)
        if not line[0].isspace() and ('flags' in line or 'encap' in line):
            parts = line.split(':', 1)[0].split()
            current_iface = parts[0].lower()
            if any(current_iface.startswith(i) for i in _exclude_prefixes):
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

def _parse_ipconfig_output(output: str) -> str:
    for line in output.split('\n'):
        line = line.strip()
        if not line:
            continue

        if "IPv4" in line:
            match = re.search(r'IPv4[^:]*:\s*(\d+\.\d+\.\d+\.\d+)', line, re.IGNORECASE)
            if match:
                ip = match.group(1)
                if is_valid_ip(ip):
                    return ip
    return ""

def is_valid_ip(ip: str) -> bool:
    """Check if IP is valid IPv4 and not special/reserved"""
    if not ip:
        return False
    
    # Check for loopback, link-local etc.
    if (ip.startswith("127.") or 
        ip.startswith("169.254.") or
        ip.startswith("0.") or
        ip == "0.0.0.0" or
        ip == "255.255.255.255"):
        return False
    
    # Basic IP validation
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    
    # Check for invalid chars in IP
    try:
        # Multi-cast ip
        if 224 <= int(parts[0]) <= 239:
            return False
    
        for part in parts:
            num = int(part)
            if num < 0 or num > 255:
                return False
    except ValueError:
        logger.print_warning("Invalid ip: Non numerical IP found")
        return False
    
    return True

def get_local_ip_fallback() -> str:
    """Last resort fallback method"""
    try:
        # Try to get IP by connecting to itself
        hostname = socket.gethostname()
        try:
            # Get all IPs for hostname
            ip_list = socket.getaddrinfo(hostname, None, socket.AF_INET)
            for ip_info in ip_list:
                ip = ip_info[4][0]
                if is_valid_ip(ip):
                    return ip
        except:
            # Try localhost resolution
            ip_list = socket.getaddrinfo("localhost", None, socket.AF_INET)
            for ip_info in ip_list:
                ip = ip_info[4][0]
                if is_valid_ip(ip):
                    return ip
    except:
        pass
    
    return "0.0.0.0"
