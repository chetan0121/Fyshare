"""HTTP server initialization, management, and request handling loop."""

import time
import http.server as http_server
from . import credentials
from .utils import logger
from .state import ServerState, FileState
from .handlers.file_handler import FileHandler


class ServerError(Exception):
    """Exception raised for server initialization or runtime errors."""
    pass

def init_server() -> None:
    """Create and bind the HTTP server to configured IP and port.
    
    Initializes a ThreadingHTTPServer with the FileHandler to serve requests.
    Must be called after state.init_server_state() to ensure ServerState
    is properly initialized.
    
    Raises:
        ValueError: If ServerState is not initialized.
        RuntimeError: If the server cannot bind to the configured IP:port
            (port already in use or permission denied).
    """
    if not ServerState.is_initialized:
        raise ValueError("State Error: Server state is not initialized yet")

    ip = ServerState.local_ip
    port = ServerState.port
    try:
        ServerState.server = http_server.ThreadingHTTPServer((ip, port), FileHandler)
    except OSError:
        raise RuntimeError(
            f"Bind Error: Failed to bind {ip}:{port}"
        )
        
def shutdown_server(msg: str = "Shutdown the Server") -> None:
    """Gracefully shut down the HTTP server.
    
    Sets is_running flag to False, closes the server socket, and logs
    the shutdown message. Handles exceptions during shutdown without
    propagating them.
    
    Args:
        msg: Shutdown reason message to display and log.
    """
    ServerState.is_running = False
    if ServerState.server:
        try:
            ServerState.server.server_close()
            ServerState.server = None
        except Exception as e:
            logger.emit_error(f"During shutdown: {str(e)}")
            return

    # Print and log the msg
    logger.print_info(f"- {msg}", lvl_tag=False, prefix="\n\n")
    logger.log_info(msg, end=f"\n{'='*100}")

def run_server() -> None:
    """Run the main server loop handling requests and managing timeouts.
    
    Continuously processes incoming client requests, performs session/attempt
    cleanup, rotates credentials on schedule, and auto-shuts down after the
    configured idle timeout period. Terminates when ServerState.is_running
    is set to False.
    
    Raises:
        AttributeError: If ServerState or FileState is not properly initialized.
    """
    # Make Alias of server
    S = ServerState
    server = S.server
    session_manager = S.session_manager

    # Check is server and session_manager initialized
    if not server or not session_manager:
        raise AttributeError("State Error: ServerState isn't initialized properly.")

    # Constant configs
    server.timeout = FileState.CONFIG["refresh_time_s"]
    cleanup_time_s = FileState.CONFIG['cleanup_timeout_m'] * 60
    idle_timeout_m = FileState.CONFIG['idle_timeout_m']
    idle_timeout_s = idle_timeout_m * 60
    
    # To track timeout
    inactivity_start_ts = None

    # Server loop
    S.is_running = True
    while S.is_running:
        current_time = time.monotonic()

        # Cleanup
        session_manager.clean_expired_attempts()
        session_manager.clean_expired_sessions()

        # Auto update credentials after cleanUp time
        if current_time - S.last_credential_update_ts >= cleanup_time_s:
            credentials.generate_credentials("Old Credentials expired!")

        # Handle inactivity timeout
        if not session_manager.sessions and inactivity_start_ts is None:
            inactivity_start_ts = current_time
        elif session_manager.sessions:
            inactivity_start_ts = None

        # Handle incoming server requests
        server.handle_request()

        # Shutdown server automatically after idle-timeout
        if inactivity_start_ts is not None \
            and (current_time - inactivity_start_ts) > idle_timeout_s:
            
            min_or_mins = 'minute' if idle_timeout_m == 1 else 'minutes'
            shutdown_server(
                f"Server closed successfully after "
                f"{idle_timeout_m} {min_or_mins} of inactivity"
            )
