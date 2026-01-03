import string
import secrets
from .utils import logger
from .utils.style_manager import *
from .state import FileState, ServerState

def generate_session_token(b_size:int = 32) -> str:
    return secrets.token_hex(b_size)

def generate_otp(length=6) -> str:
    return ''.join(secrets.choice(string.digits) for _ in range(length))

def _print_credentials(message: str):
    root_dir = f"\"{FileState.ROOT_DIR}\""
    login_link = f"http://{ServerState.local_ip}:{ServerState.port}"
    separator_line = str('-'*50)
    
    # Print credentials and stats
    Style.print_style(f"\n\n{message}", Color.YELLOW, TextStyle.BRIGHT)
    Style.print_style(separator_line, TextStyle.BOLD)

    Style.print_style(f"Serving directory : {root_dir}", TextStyle.BOLD)
    Style.print_style(f"Open in browser   : {login_link}", TextStyle.BOLD)

    Style.print_style(f"\nLogin Details:", 36, TextStyle.BOLD)
    Style.print_style(f"   • OTP       : {ServerState.otp}")

    Style.print_style(f"\nSettings:", 36, TextStyle.BOLD)
    Style.print_style(f"   • Max users : {FileState.CONFIG['max_users']} Allowed")
    Style.print_style(f"   • Time Out  : {FileState.CONFIG['idle_timeout_m']} minutes")
    
    Style.print_style(f"{separator_line}\n", TextStyle.BOLD)

def _log_credentials(msg: str):
    reason = msg if msg else 'Not specified'

    data = {
        "Max allowed": f"{FileState.CONFIG['max_users']} users",
        "Time out": f"{FileState.CONFIG['idle_timeout_m']} minutes",
        "Server refresh interval": f"{FileState.CONFIG['refresh_time_s']} seconds",
        "Server cleanup": f"{FileState.CONFIG['cleanup_timeout_m']} minutes",
    }

    # Build content lines
    lines = [f"- {k}: {v}" for k, v in data.items()]
    
    # Find max width
    max_len = max(len(line) for line in lines)
    sep_line = str('-' * (max_len+2))

    logger.log_info("", lvl_tag=False)
    logger.log_info(f"Generated New Credentials", f"Reason: {reason}", lvl_tag=False)
    logger.log_info(sep_line, lvl_tag=False)

    for line in lines:
        logger.log_info(f"{line.ljust(max_len)} |", lvl_tag=False)

    logger.log_info(sep_line, lvl_tag=False)
    logger.log_info("", lvl_tag=False)

def generate_credentials(message = str("")):
    with ServerState.credentials_lock:
        # Handle stat and generate new OTP
        ServerState.last_credential_update_ts = None
        ServerState.otp = generate_otp()

        # Printing
        _print_credentials(message)

        # logging
        _log_credentials(message)
