import time
import http.server as http_server
from . import credentials
from .utils import logger
from .states import ServerState, FileState
from .handlers.file_handler import FileHandler

class ServerError(Exception): pass

def init_server():
    """
    Run this only after -> state.init_server_state()
    """
    try:
        ServerState.Server = http_server.ThreadingHTTPServer(("", ServerState.PORT), FileHandler)
    except OSError as e:
        logger.print_error(f"Server: Failed to bind to port[{ServerState.PORT}], Please try again.")
        print("- Details:", e)
        exit(1)

def shutdown_server(msg=""):
    if ServerState.Server:
        try:
            ServerState.is_running = False
            ServerState.Server.server_close()
        except Exception as e:
            logger.print_error(f"During shutdown: {e}")
            logger.log_error(f"During shutdown: {e}")
            return

    # Print and log the msg
    logger.print_info(f"{msg}", lvl_tag=False)
    logger.log_info(f"{msg}\n")

def run_server():
    ServerState.is_running = True

    Session = ServerState.SESSION_MANAGER
    server = ServerState.Server
    server.timeout = FileState.CONFIG["refresh_time_s"]

    last_updated = ServerState.LAST_UPDATED_CRED
    inactivity = ServerState.INACTIVITY_START

    # Constant configs
    cleanup_time_s = int(FileState.CONFIG['cleanup_timeout_m'] * 60)
    idle_timeout_m = int(FileState.CONFIG['idle_timeout_m'])
    idle_timeout_s = idle_timeout_m * 60

    while ServerState.is_running:
        # Clean expired sessions & attempts and update current time
        Session.clean_expired_attempts()
        Session.clean_expired_sessions()
        current_time = time.monotonic()

        # Auto update credentials after cleanUp time
        if last_updated is None:
            last_updated = current_time
        elif current_time - last_updated > cleanup_time_s:
            credentials.generate_credentials("Old Credentials expired!")

        # Handle inactivity timeout
        if not Session.sessions and inactivity is None:
            inactivity = current_time
        elif Session.sessions:
            inactivity = None

        # Handle incoming server requests
        server.handle_request()

        # Shutdown server automatically after idle-timeout
        if inactivity and (current_time - inactivity) > idle_timeout_s:
            minutePrint = 'minute' if idle_timeout_m == 1 else 'minutes'
            shutdown_server(f"- Server closed successfully after {idle_timeout_m} {minutePrint} of inactivity")

