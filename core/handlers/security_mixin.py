import re, time
from http.server import SimpleHTTPRequestHandler as ReqHandler
from ..utils import helper
from ..state import ServerState, FileState

class SecurityMixin():
    def get_session_token(self: ReqHandler):
        cookies = self.headers.get('Cookie', '')
        for cookie in cookies.split(';'):
            cookie = cookie.strip()
            if cookie.startswith('session_token='):
                return cookie.split('=', 1)[1].strip()
        return None

    def validate_credentials(self: ReqHandler, otp, timeout):
        # Validate otp: exactly 6 digits
        is_valid_otp = bool(re.fullmatch(r'\d{6}', otp))

        # Validate timeout: must be between min and max allowed seconds in Options
        lowest_opt = FileState.OPTIONS[0][0]*60
        highest_opt = FileState.OPTIONS[-1][0]*60
        is_valid_timeout = bool(lowest_opt <= timeout <= highest_opt)

        return is_valid_otp and is_valid_timeout 

    def check_authentication(self):
        session_token = self.get_session_token()
        if not session_token:
            return False
        
        session_data = ServerState.session_manager.get_session(session_token)
        if not session_data:
            return False
        
        if time.monotonic() >= session_data.get('expiry', 0):
            ServerState.session_manager.remove_session(session_token)
            return False
        
        return True

    def translate_path(self: ReqHandler, path: str):
        path = super().translate_path(str(path))
        real_path = str(helper.refine_path(path))
        if not real_path.startswith(str(FileState.ROOT_DIR)):
            self.send_error(403, "Access denied")
            return str(FileState.ROOT_DIR)
        
        return real_path  
    
    