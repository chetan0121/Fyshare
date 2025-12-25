import time
import http.server as http_server
from . import credentials
from .utils import logger
from .state import ServerState, FileState
from .handlers.file_handler import FileHandler

class ServerError(Exception): pass

def init_server():
    """
    Initialize server
    - Create and set instance of ThreadingHTTPServer with Custom Filehandler
    Note: Run this only after -> state.init_server_state()
    """
    if not ServerState.is_initialized:
        raise ValueError("Can't run init_server before init_server_state")

    port = ServerState.port
    try:
        ServerState.server = http_server.ThreadingHTTPServer(("", port), FileHandler)
    except OSError:
        raise RuntimeError(
            f"Server: Failed to bind to port[{port}], Please try again."
        )
    
def shutdown_server(msg="Shutdown the Server"):
    if ServerState.server:
        try:
            ServerState.server.server_close()
            ServerState.is_running = False
            ServerState.server = None
        except Exception as e:
            logger.emit_error(f"During shutdown: {str(e)}")
            return

    # Print and log the msg
    logger.print_info(f"- {msg}", lvl_tag=False, prefix="\n\n")
    logger.log_info(msg)

def run_server():
    # Make Alias of server
    S = ServerState
    server  = S.server
    session_manager = S.session_manager

    # Check is server and session_manager initialized
    if not server or not session_manager:
        raise AttributeError("Instance of SessionManager not found")

    # Set refresh time
    server.timeout = FileState.CONFIG["refresh_time_s"]

    # Constant configs
    cleanup_time_s = FileState.CONFIG['cleanup_timeout_m'] * 60
    idle_timeout_m = FileState.CONFIG['idle_timeout_m']
    idle_timeout_s = idle_timeout_m * 60

    # Server loop
    S.is_running = True
    while S.is_running:
        # Clean expired sessions & attempts and update current time
        session_manager.clean_expired_attempts()
        session_manager.clean_expired_sessions()
        current_time = time.monotonic()

        # Auto update credentials after cleanUp time
        if S.last_credential_update_ts is None:
            S.last_credential_update_ts = current_time
        elif current_time - S.last_credential_update_ts > cleanup_time_s:
            credentials.generate_credentials("Old Credentials expired!")

        # Handle inactivity timeout
        if not session_manager.sessions and S.inactivity_start_ts is None:
            S.inactivity_start_ts = current_time
        elif session_manager.sessions:
            S.inactivity_start_ts = None

        # Handle incoming server requests
        server.handle_request()

        # Shutdown server automatically after idle-timeout
        if S.inactivity_start_ts is None:
            continue

        if (current_time - S.inactivity_start_ts) > idle_timeout_s:
            min_or_mins = 'minute' if idle_timeout_m == 1 else 'minutes'
            shutdown_server(
                f"Server closed successfully after "
                f"{idle_timeout_m} {min_or_mins} of inactivity"
            )
