import threading
import secrets
from http.server import ThreadingHTTPServer
from . import FileState
from ..utils import helper
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

    # Session timeout options (CONSTANT)
    OPTIONS = [
        (5, "5 minutes"),
        (15, "15 minutes"),
        (30, "30 minutes"),
        (60, "1 hour"),
        (120, "2 hours"),
    ]

    def init_server_state():
        """
        - Only run this before starting the server (server.init_server())
        - Only run this after template setup (FileState.set_templates())
        """
        ServerState.PORT = secrets.choice(range(1500, 9500))
        ServerState.LOCAL_IP = helper.get_local_ip()

        timeout_opt = ServerState.OPTIONS
        timeout_opt.sort(key=lambda x: x[0])
        
        options_html = []
        for mins, label in timeout_opt:
            options_html.append(f'<option value="{mins*60}">{label}</option>')

        options_html = "\n".join(options_html)
        FileState.LOGIN_HTML = FileState.LOGIN_HTML.replace('{{options}}', options_html)
        