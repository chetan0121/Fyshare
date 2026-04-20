"""User session and login attempt tracking with cooldown and blocking."""

import time
import threading
from typing import Optional

from .utils import logger
from .state import FileState


class SessionManager:
    """Manages active user sessions and tracks login attempts per IP.
    
    Provides thread-safe methods to store sessions (token -> IP + expiry),
    track login attempts per IP with cooldown and blocking mechanisms,
    and clean up expired sessions/attempts based on timestamps.
    """
    def __init__(self) -> None:
        """Initialize empty session and attempt tracking dictionaries.
        
        Creates storage for active sessions (token -> IP/expiry) and
        attempt tracking (IP -> attempt count/cooldown/block times).
        Initializes thread lock for all access to these dictionaries.
        """
        self.sessions: dict = {}      
        # {
        #     token: {
        #         'ip': client_ip, 
        #         'expiry': timestamp
        #     }
        # }

        self.attempts: dict = {}    
        # {
        #    ip: {
        #       'count': int, 
        #       'last_time': time, 
        #       'cool_until': time, 
        #       'blocked_until': time
        #    }
        # }

        # Thread lock for every function 
        self.session_lock = threading.Lock()

    def try_add_session(self, token: str, ip: str, expiry: float) -> bool:
        """Attempt to add a new session if under max user limit.
        
        Thread-safe method that checks current session count against the
        configured max_users limit before adding a new session.
        
        Args:
            token: Unique session token.
            ip: Client IP address.
            expiry: Session expiry timestamp (monotonic time).
        
        Returns:
            True if session was added, False if max user limit reached.
        """
        with self.session_lock:
            session_count = len(self.sessions)
            if session_count >= FileState.CONFIG['max_users']:
                return False

            self.sessions[token] = {'ip': ip, 'expiry': expiry}
            return True

    def remove_session(self, token: str) -> None:
        """Remove an active session by token.
        
        Thread-safe removal; does nothing if token doesn't exist.
        
        Args:
            token: Session token to remove.
        """
        with self.session_lock:
            if token in self.sessions:
                del self.sessions[token]

    def get_session(self, token: str) -> Optional[dict]:
        """Retrieve session data by token (creates a copy).
        
        Thread-safe retrieval that returns a copy of the session dict
        to prevent external modification of internal state.
        
        Args:
            token: Session token to look up.
        
        Returns:
            Dictionary with 'ip' and 'expiry' keys, or None if not found.
        """
        with self.session_lock:
            session = self.sessions.get(token)
            return dict(session) if session else None

    def clean_expired_sessions(self) -> None:
        """Remove all sessions with expiry time in the past.
        
        Compares session expiry against current monotonic time and logs
        each removed session with its IP address.
        """
        with self.session_lock:
            current_time = time.monotonic()
            expired = [
                t for t, s in self.sessions.items()
                if current_time > s["expiry"]
            ]

            for token in expired:
                logger.emit_info(
                    f"Session expired for User",
                    f"IP: {self.sessions[token]['ip']}"
                )
                del self.sessions[token]

    def update_attempts(self, ip: str, current_time: float) -> None:
        """Record a failed login attempt for an IP and apply cooldown/block rules.
        
        Increments attempt counter for the IP. If max_attempts threshold is reached,
        sets a cooldown period. If max_total_attempts is reached, blocks the IP
        entirely for block_time_m minutes. Logs transitions to cooldown/blocked states.
        
        Args:
            ip: Client IP address.
            current_time: Current monotonic timestamp.
        """
        with self.session_lock:
            if ip not in self.attempts:
                self.attempts[ip] = {'count': 0, 'last_time': 0}
                
            data = self.attempts[ip]
            data['count'] += 1
            data['last_time'] = current_time

            block_time = FileState.CONFIG['block_time_m']
            cooldown_s = FileState.CONFIG['cooldown_s']

            if data['count'] >= FileState.CONFIG['max_total_attempts']:
                data['blocked_until'] = current_time + block_time * 60
                logger.emit_warning(
                    f"Blocked User for {block_time} minutes due to excessive attempts",
                    f"IP: {ip}"
                )
                return

            if data['count'] % FileState.CONFIG['max_attempts'] == 0:
                data['cool_until'] = current_time + cooldown_s
                logger.emit_info(
                    f"User is in cool-down for {cooldown_s} seconds due to excessive attempts",
                    f"IP: {ip}"
                )

    def is_inCool(self, ip: str, current_time: float) -> bool:
        """Check if an IP is currently in cooldown period.
        
        Args:
            ip: Client IP address.
            current_time: Current monotonic timestamp.
        
        Returns:
            True if IP has a cooldown period and current_time is before cool_until.
        """
        with self.session_lock:
            return ip in self.attempts and self.attempts[ip].get('cool_until', 0) > current_time
        
    def is_blocked(self, ip: str, current_time: float) -> bool:
        """Check if an IP is currently blocked due to excessive attempts.
        
        Args:
            ip: Client IP address.
            current_time: Current monotonic timestamp.
        
        Returns:
            True if IP has a block period and current_time is before blocked_until.
        """
        with self.session_lock:
            return ip in self.attempts and self.attempts[ip].get('blocked_until', 0) > current_time

    def clean_expired_attempts(self) -> None:
        """Remove IPs that have completed their block period or timed out.
        
        Removes IPs from attempt tracking if:
        - They have completed their block period (blocked_until timestamp passed), or
        - Their last attempt was older than cleanup_timeout_m minutes.
        
        Logs each IP as it transitions from blocked to unblocked state.
        """
        with self.session_lock:
            cleanup_timeout_s = FileState.CONFIG['cleanup_timeout_m']*60
            current_time = time.monotonic()
            expired_ips = []

            for ip, data in list(self.attempts.items()):
                # Clean expired blocks
                if 'blocked_until' in data and current_time >= data['blocked_until']:
                    logger.emit_info("Unblocked User", f"IP: {ip}")
                    expired_ips.append(ip)

                elif 'last_time' in data and current_time - data['last_time'] > cleanup_timeout_s:
                    expired_ips.append(ip)

            # Remove fully expired entries
            for ip in expired_ips:
                del self.attempts[ip]
