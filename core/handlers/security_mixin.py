import re
import time
from http.server import SimpleHTTPRequestHandler as ReqHandler
from ..utils import helper
from ..state import ServerState, FileState

class SecurityMixin(ReqHandler):
    def get_session_token(self) -> str | None:
        """Extract session token from request cookies.
        
        Returns:
            The session token string if found, None otherwise.
        """
        cookies = self.headers.get('Cookie', '')
        for cookie in cookies.split(';'):
            cookie = cookie.strip()
            if cookie.startswith('session_token='):
                return cookie.split('=', 1)[1].strip()
        return None

    @staticmethod
    def validate_credentials(otp: str, timeout: int) -> bool:
        """Validate OTP format and session timeout range.
        
        Args:
            otp: One-time password to validate (must be 6 digits).
            timeout: Session timeout in seconds.
            
        Returns:
            True if both OTP and timeout are valid, False otherwise.
        """
        # Validate otp: exactly 6 digits
        is_valid_otp = bool(re.fullmatch(r'\d{6}', otp))

        # Validate timeout: must be between min and max allowed seconds in Options
        lowest_opt = FileState.OPTIONS[0][0] * 60
        highest_opt = FileState.OPTIONS[-1][0] * 60
        is_valid_timeout = bool(lowest_opt <= timeout <= highest_opt)

        return is_valid_otp and is_valid_timeout 

    def check_authentication(self) -> bool:
        """Check if the request has a valid, non-expired session.
        
        Returns:
            True if session exists and is not expired, False otherwise.
        """
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

    def translate_path(self, path: str) -> str:
        """Translate URL path to filesystem path with security validation.
        
        Ensures the resolved path is within ROOT_DIR to prevent directory traversal.
        
        Args:
            path: URL path to translate.
            
        Returns:
            The validated real filesystem path.
            
        Raises:
            Sends 403 error if path is outside ROOT_DIR.
        """
        path = super().translate_path(str(path))
        real_path = str(helper.refine_path(path))
        if not real_path.startswith(str(FileState.ROOT_DIR)):
            self.send_error(403, "Access denied")
            return str(FileState.ROOT_DIR)
        
        return real_path  
    
    