import string
import secrets
from core.state import FileState, ServerState
from core.utils import logger

def generate_session_token(b_size:int = 32) -> str:
    return secrets.token_hex(b_size)

def generate_username() -> str:
    # pick 4–5 letters
    chars = ''.join(secrets.choice(string.ascii_lowercase) for _ in range(secrets.choice([4, 5])))

    # pick 3–4 digits
    digits = ''.join(secrets.choice(string.digits) for _ in range(secrets.choice([3, 4])))

    # return generated letters + digits as a single string
    return chars + digits   

def generate_otp(length=6) -> str:
    return ''.join(secrets.choice(string.digits) for _ in range(length))

def generate_credentials(message = str("")):
    with ServerState.credentials_lock:
        ServerState.USERNAME = generate_username()
        ServerState.OTP = generate_otp()
        
        logger.print_custom(f"\n\n{message}", 33)
        logger.print_custom("---------------------------------------------", 1)
        logger.print_custom(f"\nServing directory: \"{FileState.ROOT_DIR}\"", 1)
        logger.print_custom(f"Open in browser: http://{ServerState.LOCAL_IP}:{ServerState.PORT}", 1)

        logger.print_custom(f"\nCredentials:", 36, 1)
        print(f"   - Username  : {ServerState.USERNAME}")
        print(f"   - OTP       : {ServerState.OTP}")
        print(f"   - Max users : {FileState.CONFIG['max_users']} Allowed")
        print(f"   - Time Out  : {FileState.CONFIG['idle_timeout_m']} {'minute' if FileState.CONFIG['idle_timeout_m'] == 1 else 'minutes'} of inactivity")
        logger.print_custom("\n---------------------------------------------", 1)

        logger.log_info(f"Generated New Credentials", f"Reason: {message or 'Server just started'}")
