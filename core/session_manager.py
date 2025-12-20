import time
import threading
from .utils import logger
from .state import FileState

class SessionManager:
    def __init__(self):
        # {token: {'ip': client_ip, 'expiry': timestamp}}
        self.sessions = {}      

        self.attempts = {}  # {
                            #    ip: {
                            #       'count': int, 
                            #       'last_time': time, 
                            #       'cool_until: time', 
                            #       'blocked_until': time
                            #    }
                            # }

        # Thread lock for every function 
        self.session_lock = threading.Lock()

    def add_session(self, token, ip, expiry):
        with self.session_lock:
            self.sessions[token] = {'ip': ip, 'expiry': expiry}

    def remove_session(self, token):
        with self.session_lock:
            if token in self.sessions:
                del self.sessions[token]

    def get_session(self, token):
        with self.session_lock:
            session = self.sessions.get(token)
            return dict(session) if session else None

    def clean_expired_sessions(self):
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

    def update_attempts(self, ip, current_time):
        with self.session_lock:
            if ip not in self.attempts:
                self.attempts[ip] = {'count': 1, 'last_time': current_time}
            else:
                data = self.attempts[ip]
                data['count'] += 1
                data['last_time'] = current_time

                block_time = FileState.CONFIG['block_time_m']
                cooldown_s = FileState.CONFIG['cooldown_s']

                if data['count'] >= FileState.CONFIG['max_total_attempts']:
                    data['blocked_until'] = current_time + block_time * 60
                    logger.emit_warning(f"Blocked User[{ip}] for {block_time} minutes due to excessive attempts")
                    return

                if data['count'] % FileState.CONFIG['max_attempts'] == 0:
                    data['cool_until'] = current_time + cooldown_s
                    logger.emit_info(f"User[{ip}] is in cool-down for {cooldown_s} seconds due to excessive attempts")
                    return

    def is_inCool(self, ip, current_time):
        with self.session_lock:
            return ip in self.attempts and self.attempts[ip].get('cool_until', 0) > current_time
        
    def is_blocked(self, ip, current_time):
        with self.session_lock:
            return ip in self.attempts and self.attempts[ip].get('blocked_until', 0) > current_time

    def clean_expired_attempts(self):
        with self.session_lock:
            cleanup_timeout_s = FileState.CONFIG['cleanup_timeout_m']*60
            current_time = time.monotonic()
            expired_ips = []

            for ip, data in list(self.attempts.items()):
                # Clean expired blocks
                if 'blocked_until' in data and current_time >= data['blocked_until']:
                    logger.emit_info(f"Unblocked User[{ip}]")
                    expired_ips.append(ip)

                elif 'last_time' in data and current_time - data['last_time'] > cleanup_timeout_s:
                    expired_ips.append(ip)

            # Remove fully expired entries
            for ip in expired_ips:
                del self.attempts[ip]
