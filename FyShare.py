"""
FyShare : Secure one-time file sharing server
"""
from pathlib import Path
from core import server, credentials
from core import load_config, backup_config
from core import SessionManager
from core.state import FileState, ServerState, StateError
from core.utils import logger, helper

def main() -> None:
    # Current folder
    this_dir = Path(__file__).parent

    # Setup logger
    logger.set_logger(f"{this_dir}/logs/server.log")

    # Load and validate configuration
    FileState.config_path = helper.refine_path(f"{this_dir}/config.json")
    FileState.CONFIG = load_config(FileState.config_path)

    # Request for backup if config isn't valid/found
    if not FileState.CONFIG:
        if not backup_config(): return
        
        FileState.CONFIG = load_config(FileState.config_path)
    
    # Setup directories (root, templates, static)
    try:
        FileState.set_root_path()
        FileState.set_templates(f"{this_dir}/templates")
        FileState.set_static_dir(f"{this_dir}/static")
    except (StateError, helper.UtilityError) as e:
        logger.print_error(f"Directory setup failed: {e}")
        return
    except KeyboardInterrupt:
        logger.print_info("Operation cancelled by user")
        return

    # Initialize core components
    ServerState.SESSION_MANAGER = SessionManager()
    ServerState.init_server_state()
    server.init_server()

    # First-time startup banner
    startup_url = f"http://{ServerState.LOCAL_IP}:{ServerState.PORT}"
    logger.log_info(
        f"\n- Server started → {startup_url} | Serving: '{FileState.ROOT_DIR}'"
    )

    # Generate and print credentials
    credentials.generate_credentials("New server started")
    print("Refer to ReadMe.md for secure file-sharing instructions.\n")

    # Start the server (loop)
    try:
        server.run_server()
    except KeyboardInterrupt:
        server.shutdown_server("- Server stopped manually")
    except Exception as e:
        logger.emit_error(f"Server error: {e}")
        server.shutdown_server(f"- Server terminated due to error")

# Entry point
if __name__ == "__main__":
    main()
