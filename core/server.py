import time
import http.server as http_server
from . import credentials
from .utils import logger
from .state import ServerState, FileState
from .handlers.file_handler import FileHandler

class ServerError(Exception): pass

def init_server():
    """
    Run this only after -> state.init_server_state()
    """
    port = ServerState.PORT
    try:
        ServerState.Server = http_server.ThreadingHTTPServer(("", port), FileHandler)
    except OSError as e:
        logger.print_error(
            f"Server: Failed to bind to port[{port}], Please try again.",
            f"\nMore Details: {str(e)}"
        )
        exit(1)

def shutdown_server(msg=""):
    if ServerState.Server:
        try:
            ServerState.is_running = False
            ServerState.Server.server_close()
        except Exception as e:
            logger.emit_error(f"During shutdown: {str(e)}")
            return

    # Print and log the msg
    logger.print_info(msg, lvl_tag=False, prefix="\n\n")
    logger.log_info(f"{msg}\n", lvl_tag=False)

def run_server():
    S = ServerState
    S.is_running = True

    Session = S.SESSION_MANAGER
    server = S.Server
    server.timeout = FileState.CONFIG["refresh_time_s"]

    # Constant configs
    cleanup_time_s = FileState.CONFIG['cleanup_timeout_m'] * 60
    idle_timeout_m = FileState.CONFIG['idle_timeout_m']
    idle_timeout_s = idle_timeout_m * 60

    while S.is_running:
        # Clean expired sessions & attempts and update current time
        Session.clean_expired_attempts()
        Session.clean_expired_sessions()
        current_time = time.monotonic()

        # Auto update credentials after cleanUp time
        if S.LAST_UPDATED_CRED is None:
            S.LAST_UPDATED_CRED = current_time
        elif current_time - S.LAST_UPDATED_CRED > cleanup_time_s:
            credentials.generate_credentials("Old Credentials expired!")

        # Handle inactivity timeout
        if not Session.sessions and S.INACTIVITY_START is None:
            S.INACTIVITY_START = current_time
        elif Session.sessions:
            S.INACTIVITY_START = None

        # Handle incoming server requests
        server.handle_request()

        # Shutdown server automatically after idle-timeout
        if S.INACTIVITY_START and (current_time - S.INACTIVITY_START) > idle_timeout_s:
            minutePrint = 'minute' if idle_timeout_m == 1 else 'minutes'
            shutdown_server(f"- Server closed successfully after {idle_timeout_m} {minutePrint} of inactivity")

