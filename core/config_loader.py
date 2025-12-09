from .utils import helper, logger
from .state import FileState

# Custom Exception
class ConfigError(Exception): pass

# Normalize value types of config
def normalize_config(config) -> dict:
    try:
        CONFIG = {
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
            "cleanup_timeout_m": int(config["cleanup_timeout_minutes"]),            

            # Cache duration for static files (HTML, CSS, etc...)
            "cache_time_out_s": float(config["default_cache_time_out_seconds"])     
        }
    except ValueError:
        raise ConfigError(f"invalid keys in config")

    return CONFIG

# Verify config values
def check_config(CONFIG) -> None:
    if CONFIG['max_users'] < 1 or CONFIG['max_users'] > 100:
        raise ConfigError("'max_users' must be a natural number from 1 to 100")

    if CONFIG['idle_timeout_m'] < 1 or CONFIG['idle_timeout_m'] > 1440:
        raise ConfigError("'idle_timeout_minutes' must be between 1 and 1440 minutes")

    if CONFIG['refresh_time_s'] <= 0 or CONFIG['refresh_time_s'] > 5:
        raise ConfigError("'refresh_time_seconds' must be between 0 and 5 seconds (excluding 0)")

    if CONFIG['max_attempts'] < 1 or CONFIG['max_attempts'] >= CONFIG['max_total_attempts']:
        raise ConfigError("'max_attempts' must be between 1 and 'max_total_attempts'")
    
    if CONFIG['max_total_attempts'] > 50:
        raise ConfigError("'max_total_attempts_per_ip' can't be more than 50 numbers")

    if CONFIG['cooldown_s'] < 0 or CONFIG['cooldown_s'] >= CONFIG['block_time_m']*60:
        raise ConfigError("invalid 'cooldown_seconds', it must be between 0 and 'block_time_minutes'")
    
    if CONFIG['block_time_m'] > CONFIG['cleanup_timeout_m']:
        raise ConfigError("'block_time_minutes' can't be more than 'cleanup_timeout_minutes'")
    
    if CONFIG['cleanup_timeout_m'] < 10 or CONFIG['cleanup_timeout_m'] > 120:
        raise ConfigError("'cleanup_timeout_minutes' must be between 10 and 120 minutes")

    if CONFIG['cache_time_out_s'] < 0 or CONFIG['cache_time_out_s'] > 86400:
        raise ConfigError("'default_cache_time_out_seconds' must be between 0 and 86400")


# Load config (Normalize, verify and return as dict)
def load_config(config_path) -> dict:
    try:
        raw_config = helper.get_json(config_path)
        CONFIG = normalize_config(raw_config)
        check_config(CONFIG)
    except (ConfigError, helper.UtilityError) as e:
        logger.print_error(str(e))
        return None

    return CONFIG

def backup_config():
        logger.print_info("Do you want to reset the current config to default?", end="\n")
        try:
            opt = input("Enter (y/n) => ").strip().lower()
        except KeyboardInterrupt:
            opt = "n"    

        config_path = FileState.config_path

        if opt == "y" or opt == "yes":
            source_path = config_path.with_name("config_example.json")

            try:
                helper.copy_file(source_path, config_path)
            except helper.UtilityError as e:
                logger.print_error(str(e))
                return False

            logger.print_info(f"Config-file '{config_path.name}' successfully restored from '{source_path.name}'", end="\n")
            return True

        elif opt == "n" or opt == "no":
            logger.print_info(f"Reset cancelled by user, Current config '{config_path.name}' was kept unchanged.", end="\n")
            logger.print_error("Failed to recover config: Reset cancelled")
            return False
        
        else:
            logger.print_error("Failed to recover config: Invalid input!")
            return False
    