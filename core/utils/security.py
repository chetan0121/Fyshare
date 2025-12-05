import re, time
import http.server as http_server
from . import logger
from ..states import ServerState

class Security(http_server.SimpleHTTPRequestHandler):
    
    def get_session_token(self):
        cookies = self.headers.get('Cookie', '')
        for cookie in cookies.split(';'):
            cookie = cookie.strip()
            if cookie.startswith('session_token='):
                return cookie.split('=', 1)[1].strip()
        return None
    
    def send_security_headers(self, cache_time = 0):
        self.send_header("X-Frame-Options", "DENY")
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self';")
        self.send_header('Referrer-Policy', 'no-referrer')
        if cache_time > 0:
            self.send_header('Cache-Control', f'max-age={cache_time}')
        else:
            self.send_header('Cache-Control', 'no-store, must-revalidate')

    def validate_credentials(self, username, otp, timeout):
        # Validate username: 6–20 alphanumeric characters
        is_valid_username = bool(re.fullmatch(r'[a-zA-Z0-9]{6,20}', username))

        # Validate OTP: exactly 6 digits
        is_valid_otp = bool(re.fullmatch(r'\d{6}', otp))

        # Validate timeout: must be between min and max allowed seconds in Options
        lowest_opt = ServerState.OPTIONS[0][0]*60
        highest_opt = ServerState.OPTIONS[-1][0]*60
        is_valid_timeout = bool(lowest_opt <= timeout <= highest_opt)

        return is_valid_username and is_valid_otp and is_valid_timeout 

    def check_authentication(self):
        session_token = Security.get_session_token(self)
        session_data = ServerState.SESSION_MANAGER.get_session(session_token)

        if not session_token or not session_data:
            return False
        if session_data['ip'] != self.client_address[0]:
            logger.print_warning(f"Session-token stolen from {session_data['ip']}", "Request terminated")
            logger.log_warning(f"Session-token stolen from User[{session_data['ip']}]", "Request terminated")
            ServerState.SESSION_MANAGER.remove_session(session_token)
            return False
        if time.monotonic() >= session_data['expiry']:
            ServerState.SESSION_MANAGER.remove_session(session_token)
            return False
        
        return True       
    
    