import threading
import secrets
from typing import Optional
from http.server import ThreadingHTTPServer
from ..utils import host_ip
from ..session_manager import SessionManager

class ServerState:
    # Server
    Server: Optional[ThreadingHTTPServer] = None
    is_running = False

    # Credentials
    otp: str
    username: str
    credentials_lock = threading.Lock()

    # Manager
    session_manager: Optional[SessionManager] = None

    # States of server
    port: str
    local_ip: str
    global_attempts: int = 0
    last_credential_update_ts: Optional[float] = None
    inactivity_start_ts: Optional[float] = None

    # init_server flag
    is_server_state = False

    def init_server_state():
        """
        Initialize server states
        - Get and set local_ip
        - Select port randomly
        Note: Only run this before starting the server (using server.init_server)
        """
        ServerState.is_server_state = True

        # Get local ip
        ServerState.local_ip = host_ip.get_local_ip()

        # Select random port from 1500 to 9500
        ServerState.port = secrets.choice(range(1500, 9500))
        
        