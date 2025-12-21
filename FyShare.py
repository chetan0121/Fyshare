"""
FyShare : Secure one-time file sharing server
"""
import os
from pathlib import Path
from core import server, credentials
from core import load_config, backup_config
from core import SessionManager
from core.state import FileState, ServerState, StateError
from core.utils import logger, helper

def main() -> None:
    # Set true, if run is from github CI
    FileState.ci_mod = os.getenv("FYSHARE_CI", "0") == "1"

    # Get current folder as path
    FileState.base_dir = Path(__file__).parent
    this_dir = str(FileState.base_dir)

    # Setup logger
    logger.set_logger(f"{this_dir}/logs/server.log")

    # Load configuration
    FileState.config_path = helper.refine_path(f"{this_dir}/config.json", False)
    FileState.CONFIG = load_config(FileState.config_path)

    # Request for backup if config is invalid or not found
    if not FileState.CONFIG:
        if not backup_config():
            return
        FileState.CONFIG = load_config(FileState.config_path)
    
    # Setup directories (root, templates, static)
    try:
        FileState.set_root_path()
        FileState.set_templates(f"{this_dir}/templates")
        FileState.set_static_dir(f"{this_dir}/static")
    except (StateError, helper.UtilityError) as e:
        logger.print_error(f"Directory setup failed: {e}", prefix="\n\n", end="\n")
        return
    except KeyboardInterrupt:
        logger.print_info("Operation cancelled by user", prefix="\n\n", end="\n")
        return

    # Initialize core components for server
    ServerState.session_manager = SessionManager()
    ServerState.init_server_state()
    server.init_server()

    # First-time startup banner
    startup_url = f"http://{ServerState.local_ip}:{ServerState.port}"
    logger.log_info(
        f"Server started → {startup_url}",
        f"Root Dir: '{FileState.ROOT_DIR}'",
        prefix=f"{'='*100}\n"
    )

    # Generate and print credentials
    credentials.generate_credentials("New server started")

    # Start the server
    try:
        server.run_server()
    except KeyboardInterrupt:
        server.shutdown_server("Server stopped manually")
    except Exception as e:
        logger.emit_error(f"Server error: {e}")
        server.shutdown_server(f"Server terminated due to error")

# Entry point
if __name__ == "__main__":
    main()
