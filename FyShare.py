"""
FyShare : Secure one-time file sharing server
"""
from core import ConfigError, load_config
from core import server, credentials
from core.state import FileState, ServerState, StateError
from core.utils import logger, helper
from core.session import SessionManager 

def main() -> None:
    # Setup logger
    logger.set_logger("logs/server.log")

    # Load and validate configuration
    FileState.config_path = helper.refine_path("config.json")
    try:
        FileState.CONFIG = load_config(FileState.config_path)
    except ConfigError as e:
        logger.print_error(str(e))
        logger.print_info("Attempting to restore from backup config...")
        if not FileState.backup_config():
            logger.print_error("Failed to recover config. Exiting.")
            exit(1)
        
        FileState.CONFIG = load_config(FileState.config_path)

    # Setup directories (root, templates, static)
    try:
        FileState.set_root_path()
        FileState.set_templates("templates")
        FileState.set_static_dir("static")
    except (StateError, helper.UtilityError) as e:
        logger.print_error(f"Directory setup failed: {e}")
        exit(1)
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        exit(0)

    # Initialize core components
    ServerState.SESSION_MANAGER = SessionManager()  # session & security manager
    ServerState.init_server_state()                 # set Port and IP
    server.init_server()                            # create TCPServer instance

    # First-time startup banner
    startup_url = f"http://{ServerState.LOCAL_IP}:{ServerState.PORT}"
    logger.log_info(
        f"Server started → {startup_url} | Serving: '{FileState.ROOT_DIR}'"
    )

    # Generate and print credentials
    credentials.generate_credentials()
    print("Refer to ReadMe.md for secure file-sharing instructions.\n")

    # Start the server (loop)
    try:
        server.run_server()
    except KeyboardInterrupt:
        server.shutdown_server("- Server stopped manually\n")
    except Exception as e:
        logger.print_error(f"Server error: {e}")
        server.shutdown_server(f"Server terminated due to error")

# Entry point
if __name__ == "__main__":
    main()
