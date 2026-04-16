import threading
import socket
from typing import Optional
from http.server import ThreadingHTTPServer

from ..utils import helper, logger
from ..utils import ip_resolver
from ..session_manager import SessionManager
from .file_state import FileState


class ServerState:
    # Server
    server: Optional[ThreadingHTTPServer] = None
    is_running = False

    # Credentials
    otp: str
    credentials_lock: threading.Lock

    # Manager
    session_manager: Optional[SessionManager] = None

    # States of server
    port: int
    local_ip: str
    global_attempts: int = 0
    last_credential_update_ts: Optional[float] = None
    server_url: str

    # init_server flag
    is_initialized = False

    @classmethod
    def init_server_state(cls) -> None:
        """Initialize server state: local IP, port, locks, and managers.
        
        Detects local network IP, selects an available port from config or fallback range.
        Must run before server.init_server().
        """
        if cls.is_initialized:
            return
        
        cls.is_initialized = True
        cls.credentials_lock = threading.Lock()
        cls.session_manager = SessionManager()
        cls.local_ip = cls._fetch_ip()
        cls.port = cls._select_port()
        cls.server_url = cls._get_server_url()
        
    @staticmethod
    def _fetch_ip() -> str:
        """Detect or retrieve local network IP.
        
        Returns config IP if valid; otherwise uses system IP detection.
        Falls back to auto-detected IP on invalid config.
        """
        ip = str(FileState.CONFIG["local_ip"]).strip().lower()
        if ip not in ("auto", ""):
            if ip_resolver.is_valid_ipv4(ip):
                return ip
            
            logger.print_warning(
                f"Config: Invalid IP \'{ip}\'.",
                end="\n"
            )
        
        logger.print_info("Auto fetching device IP.", end="\n")
        
        return ip_resolver.get_local_ip()
        
    @classmethod
    def _select_port(cls) -> int:
        """Select an available port from config or fallback range.
        
        Returns config port if valid and available; otherwise picks a random
        available port from 1500-9499. Raises if no port is available.
        """
        ip = cls.local_ip
        
        port = cls._get_config_port()
        if port is not None:
            return port
        
        logger.print_info("Auto selecting available PORT.", end="\n")
        
        safe_min_port = 1500
        safe_max_port = 9500
        
        for p in range(safe_min_port, safe_max_port):
            if cls._is_port_available(ip, p):
                return p
        
        raise RuntimeError(
            "Port Selection: Can't select suitable port" 
            "\n     - Invalid IP or"
            "\n     - No ports are available"
        )
        
    @classmethod
    def _get_server_url(cls):
        ip = cls.local_ip
        if ip == "0.0.0.0":
            ip = ip_resolver.get_local_ip()
            
        return f"http://{ip}:{cls.port}"
        
    @staticmethod
    def _is_port_available(ip: str, port: int) -> bool:
        """Check if an IP:port pair is available for binding.
        
        Args:
            ip: IPv4 address to test.
            port: Port number to test.
            
        Returns:
            True if socket bind succeeds; False otherwise.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((ip, port))
            return True
        except OSError:
            return False
        
    @classmethod
    def _get_config_port(cls) -> Optional[int]:
        """Get and validate port from config.
        
        Returns config port if valid and available; None if auto or invalid.
        Logs warnings for out-of-range or busy ports and falls back to auto-select.
        """
        ip = cls.local_ip
        min_port = 1
        max_port = 65535

        config_port = str(FileState.CONFIG["port"]).strip().lower()
        
        # Auto or empty
        if config_port in ("auto", ""):
            return None
        
        # Parse port number
        port = helper.try_parse_int(config_port)
        if port is None:
            logger.print_warning(
                f"Config: Port '{config_port}' is not a number.",
                end="\n"
            )
            return None
        
        # Validate range
        if port < min_port or port > max_port:
            logger.print_warning(
                f"Config: Port {port} is out of range."
                f"{min_port}-{max_port}. ",
                end="\n"
            )
            return None

        # Check availability
        if not cls._is_port_available(ip, port):
            logger.print_warning(
                f"Port Selection: Port \'{port}\' is not bindable to IP \'{ip}\'",
                end="\n"
            )
            return None

        return port
