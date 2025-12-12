import threading
import secrets
from http.server import ThreadingHTTPServer
from ..utils import host_ip
from ..session_manager import SessionManager

class ServerState:
    # Server
    Server: ThreadingHTTPServer | None = None
    is_running = False

    # Credentials
    OTP: str
    USERNAME: str
    credentials_lock = threading.Lock()

    # Manager
    SESSION_MANAGER: SessionManager | None = None

    # States of server
    PORT: str
    LOCAL_IP: str
    GLOBAL_TOTAL_ATTEMPTS: int = 0
    LAST_UPDATED_CRED: float | None = None
    INACTIVITY_START: float | None = None

    def init_server_state():
        """Only run this before starting the server (using server.init_server)"""
        # Get local ip
        ip = host_ip.get_local_ip()
        if ip:
            ServerState.LOCAL_IP = ip
        else:
            ServerState.LOCAL_IP = "127.0.0.1"

        # Select random port from 1500 to 9500
        ServerState.PORT = secrets.choice(range(1500, 9500))
        
        