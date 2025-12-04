import http.server as http_server
import re
from core.state import ServerState

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
    
    