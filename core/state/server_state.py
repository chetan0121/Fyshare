import threading
import secrets
from typing import Optional
from http.server import ThreadingHTTPServer

from ..utils.get_local_ip import get_local_ip
from ..session_manager import SessionManager

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
    inactivity_start_ts: Optional[float] = None

    # init_server flag
    is_initialized = False

    @classmethod
    def init_server_state(cls):
        """
        Initialize server states
        - Get and set local_ip
        - Select port randomly
        Note: Only run this before starting the server (using server.init_server)
        """
        if cls.is_initialized:
            return
        
        # Indicates that init_server_state() has been executed
        cls.is_initialized = True

        # Threading lock
        cls.credentials_lock = threading.Lock()

        # Create instance of SessionManager class
        cls.session_manager = SessionManager()

        # Get local ip
        cls.local_ip = get_local_ip()

        # Select random port from 1500 to 9500
        cls.port = int(secrets.choice(range(1500, 9500)))
        