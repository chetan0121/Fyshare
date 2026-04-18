from pathlib import Path
import re
import time
from http.server import SimpleHTTPRequestHandler as ReqHandler
from typing import Optional, Union
from urllib.parse import unquote, urlparse
from ..state import ServerState, FileState
from ..utils import helper

class SecurityMixin(ReqHandler):
    """Security and path-safety helpers shared by request handlers."""

    def get_session_token(self) -> Optional[str]:
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

    def translate_path(self, path: Union[str,Path], base_dir: Union[str,Path] = None) -> Path:
        """Resolve a URL path under a base directory and contain traversal.

        Args:
            path: Raw request path or relative path segment.
            base_dir: Root directory to resolve from. Defaults to server root.

        Returns:
            A normalized absolute path contained within `base_dir`.
            If traversal escapes base_dir, returns `base_dir` itself.
        """
        if base_dir is None:
            base_dir = FileState.ROOT_DIR
        else:
            base_dir = Path(base_dir)
        
        # Clean URL
        path = urlparse(str(path)).path
        path = unquote(path)
        
        rel_path = path.strip('/')
        
        # Build final path
        full_path = helper.refine_path(base_dir / rel_path)
        
        try:
            full_path.relative_to(base_dir)
        except ValueError:
            return base_dir

        return full_path
    