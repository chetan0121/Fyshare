from core.state import FileState
from core import ConfigError, load_config
from core import config_loader
from core.utils import logger
from core.session import SessionManager

# Initialize logger
logger.set_logger("logs/server.log")

# Set and load config
FileState.config_path = str("config.json")
try:
    # FileState.CONFIG = load_config(FileState.config_path)
    raw_config = config_loader.get_config(FileState.config_path)
    FileState.raw_config = raw_config

    CONFIG = config_loader.normalize_config(raw_config)
    config_loader.check_config(CONFIG)
    FileState.CONFIG = CONFIG
except ConfigError as c:
    logger.print_error(c)

FileState.set_root_path()
FileState.set_template_dir("templates")


Session = SessionManager()
