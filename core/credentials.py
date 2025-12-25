import string
import secrets
from .utils import logger
from .utils.style_manager import *
from .state import FileState, ServerState

def generate_session_token(b_size:int = 32) -> str:
    return secrets.token_hex(b_size)

def generate_otp(length=6) -> str:
    return ''.join(secrets.choice(string.digits) for _ in range(length))

def generate_credentials(message = str("")):
    with ServerState.credentials_lock:
        # Generate new username and otp
        ServerState.last_credential_update_ts = None
        ServerState.otp = generate_otp()

        # Details to print
        root_dir = f"\"{FileState.ROOT_DIR}\""
        login_link = f"http://{ServerState.local_ip}:{ServerState.port}"
        separator_line = str('-'*50)
        
        # Printing New Server details
        Style.print_style(f"\n\n{message}", Color.YELLOW, TextStyle.BRIGHT)
        Style.print_style(separator_line, TextStyle.BOLD)

        Style.print_style(f"Serving directory : {root_dir}", TextStyle.BOLD)
        Style.print_style(f"Open in browser   : {login_link}", TextStyle.BOLD)

        Style.print_style(f"\nLogin Details:", 36, TextStyle.BOLD)
        print(f"   • OTP       : {ServerState.otp}")

        Style.print_style(f"\nSettings:", 36, TextStyle.BOLD)
        print(f"   • Max users : {FileState.CONFIG['max_users']} Allowed")
        print(f"   • Time Out  : {FileState.CONFIG['idle_timeout_m']} minutes")
        
        Style.print_style(f"{separator_line}\n", TextStyle.BOLD)

        # logging
        reason = message if message else 'None'
        logger.log_info(f"Generated New Credentials", f"Reason: {reason}")
