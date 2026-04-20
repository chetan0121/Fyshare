"""Configuration loading, validation, and backup management."""

from typing import Optional
from .utils import helper, logger
from .utils.style_manager import Style, Color, TextStyle
from .state import FileState

class ConfigError(Exception):
    """Exception raised for configuration errors during loading or validation."""
    pass

def normalize_config(config: dict) -> dict:
    """Normalize and type-cast raw config values.
    
    Converts raw JSON config values to their target types (int, float, str).
    Uses keys from raw_config and maps them to normalized CONFIG keys.
    
    Args:
        config: Raw configuration dictionary from JSON file.
    
    Returns:
        Normalized dictionary with typed values and standard key names.
    
    Raises:
        ConfigError: If a value cannot be converted to its target type (ValueError)
            or if a required key is missing (KeyError).
    """
    try:
        CONFIG = {
            # Custom Server IP
            "local_ip": str(config["local_ipv4"]),
            
            # Custom Port 
            "port": str(config["port"]),
            
            # Root directory served by the server
            "root_directory": str(config["root_directory"]),

            # Maximum number of users allowed to access the server                 
            "max_users": int(config["max_users"]),

            # Automatically stop server after this many minutes of inactivity                                
            "idle_timeout_m": int(config["idle_timeout_minutes"]),   

            # Server refresh/update interval in seconds              
            "refresh_time_s": float(config["refresh_time_seconds"]),       

            # Allowed failed attempts per IP before cooldown         
            "max_attempts": int(config["max_attempts_per_ip"]),  

            # Total allowed attempts before IP is blocked               
            "max_total_attempts": int(config["max_total_attempts_per_ip"]),         

            # Cooldown duration for an IP after exceeding "max_attempts"                
            "cooldown_s": int(config["cooldown_seconds"]),           

            # Duration of an IP remains blocked (after reaching "max_total_attempts")
            "block_time_m": int(config["block_time_minutes"]),                      

            # Time in minutes, before old attempts are cleaned up
            "cleanup_timeout_m": int(config["cleanup_timeout_minutes"])
        }
    except ValueError as v:
        raise ConfigError(f"Invalid value type in config: {str(v)}")
    except KeyError as k:
        raise ConfigError(f"Missing required key: {str(k)}")

    return CONFIG

def check_config(CONFIG: dict) -> None:
    """Validate normalized config values for acceptable ranges and constraints.
    
    Note: IP and port configs are validated in server-state initialization,
    not here. This function validates timeouts, user limits, and attempt counters.
    
    Args:
        CONFIG: Normalized configuration dictionary.
    
    Raises:
        ConfigError: If any config value is outside acceptable range or violates
            inter-parameter constraints.
    """
    if CONFIG['max_users'] < 1 or CONFIG['max_users'] > 100:
        raise ConfigError("'max_users' must be a natural number from 1 to 100")

    if CONFIG['idle_timeout_m'] < 1 or CONFIG['idle_timeout_m'] > 1440:
        raise ConfigError("'idle_timeout_minutes' must be between 1 and 1440 minutes")

    if CONFIG['refresh_time_s'] <= 0 or CONFIG['refresh_time_s'] > 5:
        raise ConfigError(
            "'refresh_time_seconds' must be between 0 and 5 seconds (excluding 0)"
        )

    if CONFIG['max_attempts'] < 1 or \
        CONFIG['max_attempts'] >= CONFIG['max_total_attempts']:
        raise ConfigError("'max_attempts' must be between 1 and 'max_total_attempts'")
    
    if CONFIG['max_total_attempts'] > 50:
        raise ConfigError("'max_total_attempts_per_ip' can't be more than 50 numbers")

    if CONFIG['cooldown_s'] < 0 or CONFIG['cooldown_s'] >= CONFIG['block_time_m']*60:
        raise ConfigError(
            "invalid 'cooldown_seconds', "
            "it must be between 0 and 'block_time_minutes'"
        )
    
    if CONFIG['block_time_m'] > CONFIG['cleanup_timeout_m']:
        raise ConfigError(
            "'block_time_minutes' can't be more than 'cleanup_timeout_minutes'"
        )
    
    if CONFIG['cleanup_timeout_m'] < 10 or CONFIG['cleanup_timeout_m'] > 120:
        raise ConfigError(
            "'cleanup_timeout_minutes' must be between 10 and 120 minutes"
        )


def load_config(config_path) -> Optional[dict]:
    """Load, normalize, and validate configuration file.
    
    Args:
        config_path: Path to the configuration JSON file.
    
    Returns:
        Normalized configuration dictionary, or None if loading/validation fails.
        On error, logs the failure reason to the error logger.
    """
    try:
        raw_config = helper.get_json(config_path)
        CONFIG = normalize_config(raw_config)
        check_config(CONFIG)
    except (ConfigError, helper.UtilityError) as e:
        logger.print_error(f"Config: {e}")
        return None

    return CONFIG

def backup_config(file_name: str) -> bool:
    """Restore default configuration after user confirmation.
    
    Prompts the user to confirm resetting to default config, then copies
    the specified backup file over the current config.json. Handles user
    cancellation and I/O errors gracefully with logging.
    
    Args:
        file_name: Name of the backup/default config file to restore from.
    
    Returns:
        True if restore succeeded, False otherwise (cancellation or error).
    """
    config_path = FileState.config_path
    source_path = config_path.with_name(file_name)

    # Prompt via StyleManager; keep status/error output on logger.
    Style.print(
        "Reset whole server config to default?",
        Color.YELLOW,
        TextStyle.BOLD,
        end=" "
    )
    Style.print("(y/n) => ", Color.CYAN, end="")

    try:
        opt = input().strip().lower()
    except KeyboardInterrupt:
        logger.print_info("Reset cancelled by user", end="\n")
        logger.print_error("Failed to recover config: Reset cancelled")
        return False

    if opt in ("y", "yes"):
        try:
            helper.copy_file(source_path, config_path)
        except helper.UtilityError as e:
            logger.print_error(str(e))
            return False

        logger.print_info(
            f"Default server config restored successfully.",
            end="\n"
        )
        return True

    elif opt in ("n", "no"):
        logger.print_info(
            "Reset cancelled by user, "
            f"Current server config was kept unchanged.",
            end="\n"
        )
        logger.print_error("Failed to recover config: Reset cancelled")
    
    else:
        logger.print_error("Failed to recover config: Invalid input!")

    return False
    