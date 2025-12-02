import string
import socket
import secrets
from core.state import FileState, ServerState
from utils import logger

def generate_username():
    # pick 4–5 letters
    chars = ''.join(secrets.choice(string.ascii_lowercase) for _ in range(secrets.choice([4, 5])))

    # pick 3–4 digits
    digits = ''.join(secrets.choice(string.digits) for _ in range(secrets.choice([3, 4])))

    # return generated letters + digits as a single string
    return chars + digits   

def generate_otp(length=6):
    return ''.join(secrets.choice(string.digits) for _ in range(length))

def get_local_ip() -> str:
    # Connect to a public DNS server to discover outgoing interface
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as socket_conn:
        socket_conn.connect(("8.8.8.8", 80))
        local_ip = str(socket_conn.getsockname()[0])
        
        # Verify it's not a localhost
        if not local_ip.startswith("127."):
            return local_ip
    
    # Bind to all available network interfaces (for LAN)
    return "0.0.0.0"

def generate_credentials(message = str("")):
    global USERNAME, GLOBAL_TOTAL_ATTEMPTS, LOCAL_IP
    with credentials_lock:
        USERNAME = generate_username()
        ServerState.otp = generate_otp()
        
        logger.print_custom(f"\n\n{message}", 33)
        logger.print_custom("---------------------------------------------", 1)
        logger.print_custom(f"\nServing directory: \"{ROOT_DIR}\"", 1)
        logger.print_custom(f"Open in browser: http://{LOCAL_IP}:{PORT}", 1)

        logger.print_custom(f"\nCredentials:", 36, 1)
        print(f"   - Username  : {USERNAME}")
        print(f"   - OTP       : {ServerState.otp}")
        print(f"   - Max users : {FileState.CONFIG['max_users']} Allowed")
        print(f"   - Time Out  : {FileState.CONFIG['idle_timeout_m']} {'minute' if FileState.CONFIG['idle_timeout_m'] == 1 else 'minutes'} of inactivity")
        logger.print_custom("\n---------------------------------------------", 1)

        logger.log_info(f"Generated New Credentials", f"Reason: {message or 'Server just started'}")