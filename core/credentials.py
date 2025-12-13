import string
import secrets
from .utils import logger
from .utils.style_manager import *
from .state import FileState, ServerState

def generate_session_token(b_size:int = 32) -> str:
    return secrets.token_hex(b_size)

def generate_username() -> str:
    # pick 4–5 letters
    c_len = secrets.choice([4, 5])
    chars = ''.join(secrets.choice(string.ascii_lowercase) for _ in range(c_len))

    # pick 3–4 digits
    d_len = secrets.choice([3, 4])
    digits = ''.join(secrets.choice(string.digits) for _ in range(d_len))

    # return generated letters + digits as a single string
    return chars + digits   

def generate_otp(length=6) -> str:
    return ''.join(secrets.choice(string.digits) for _ in range(length))

def generate_credentials(message = str("")):
    with ServerState.credentials_lock:
        ServerState.LAST_UPDATED_CRED = None
        ServerState.USERNAME = generate_username()
        ServerState.OTP = generate_otp()
        login_link = f"http://{ServerState.LOCAL_IP}:{ServerState.PORT}"
        
        # Printing New Server details
        Style.print_style(f"\n\n{message}", Color.YELLOW, TextStyle.BRIGHT)
        Style.print_style("---------------------------------------------\n", TextStyle.BOLD)

        Style.print_style(f"Serving directory : \"{FileState.ROOT_DIR}\"", TextStyle.BOLD)
        Style.print_style(f"Open in browser   : {login_link}", TextStyle.BOLD)

        Style.print_style(f"\nLogin Details:", 36, TextStyle.BOLD)
        print(f"   • Username  : {ServerState.USERNAME}")
        print(f"   • OTP       : {ServerState.OTP}")

        Style.print_style(f"\nSettings:", 36, TextStyle.BOLD)
        print(f"   • Max users : {FileState.CONFIG['max_users']} Allowed")
        print(f"   • Time Out  : {FileState.CONFIG['idle_timeout_m']} minutes")
        
        Style.print_style("\n---------------------------------------------", TextStyle.BOLD)

        # logging
        logger.log_info(f"Generated New Credentials", f"Message: {message or 'None'}")
