from core import ConfigError, load_config
from core import server, credentials
from core.state import FileState, ServerState, StateError
from core.utils import logger
from core.session import SessionManager
from core.utils import helper

# Initialize logger
logger.set_logger("logs/server.log")

# Set and load config
FileState.config_path = helper.refine_path("config.json")
try:
    FileState.CONFIG = load_config(FileState.config_path)
except ConfigError as e:
    logger.print_error(str(e))
    if FileState.backup_config():
        FileState.CONFIG = load_config(FileState.config_path)
    else:
        exit(1)    

# Setup and verify files
try:
    FileState.set_root_path()
    FileState.set_templates("templates")
    FileState.set_static_dir("static")
except (StateError, helper.UtilityError) as e:
    logger.print_error(str(e))
    exit(1)
except KeyboardInterrupt:
    print("\n\n- Program Exited!\n")
    exit(1)

ServerState.SESSION_MANAGER = SessionManager()
ServerState.init_server_state()

# Generate and print new credentials
credentials.generate_credentials()
print("Refer to ReadMe.md for secure file-sharing instructions.\n")
logger.log_info(f"- Started server 'http://{ServerState.LOCAL_IP}:{ServerState.PORT}' | Root directory: '{FileState.ROOT_DIR}'")

# Initialize and Run server
try:
    server.init_server()
    server.run_server()
except OSError as e:
    server.shutdown_server()
    logger.print_info(str(e))
except KeyboardInterrupt:
    server.shutdown_server("- Server stopped manually\n")
