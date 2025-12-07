import string
import secrets
from .utils import logger
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
        logger.print_custom(f"\n\n{message}", 93)
        logger.print_custom("---------------------------------------------\n", 1)

        logger.print_custom(f"Serving directory : \"{FileState.ROOT_DIR}\"", 1)
        logger.print_custom(f"Open in browser   : {login_link}", 1)

        logger.print_custom(f"\nLogin Details:", 36, 1)
        print(f"   • Username  : {ServerState.USERNAME}")
        print(f"   • OTP       : {ServerState.OTP}")

        logger.print_custom(f"\nSettings:", 36, 1)
        print(f"   • Max users : {FileState.CONFIG['max_users']} Allowed")
        print(f"   • Time Out  : {FileState.CONFIG['idle_timeout_m']} minutes")
        
        logger.print_custom("\n---------------------------------------------", 1)

        # logging
        logger.log_info(f"Generated New Credentials", f"Message: {message or 'None'}")
