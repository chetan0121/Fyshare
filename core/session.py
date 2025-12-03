import time, threading
from core.utils import logger
from core.state import FileState

# Session Manage class (Handles users/session)
class SessionManager:
    def __init__(self):
        self.sessions = {}      # {token: {'ip': ip, 'expiry': timestamp}}
        self.attempts = {}      # {ip: {'count': int, 'last_time': time, 'cool_until: time', 'blocked_until': time}}
        self.lock = threading.Lock()

    def add_session(self, token, ip, expiry):
        with self.lock:
            self.sessions[token] = {'ip': ip, 'expiry': expiry}

    def remove_session(self, token):
        with self.lock:
            if token in self.sessions:
                del self.sessions[token]

    def get_session(self, token):
        with self.lock:
            return self.sessions.get(token)

    def clean_expired_sessions(self):
        with self.lock:
            current_time = time.monotonic()
            expired = [t for t, s in self.sessions.items() if current_time > s['expiry']]
            for token in expired:
                logger.print_info(f"Session expired for User[{self.sessions[token]['ip']}].\n")
                logger.log_info(f"- Session expired", f"User[{self.sessions[token]['ip']}]")
                del self.sessions[token]

    def update_attempts(self, ip, current_time):
        with self.lock:
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
                    logger.print_warning(f"Blocked User[{ip}] for {block_time} minutes due to excessive attempts.\n")
                    logger.log_warning(f"- Blocked User[{ip}] for {block_time} minutes", "excessive attempts")
                    return

                if data['count'] % FileState.CONFIG['max_attempts'] == 0:
                    data['cool_until'] = current_time + cooldown_s
                    logger.print_info(f"User[{ip}] is in cool-down for {cooldown_s} seconds due to excessive attempts.\n")
                    logger.log_info(f"- User[{ip}] is in cool-down for {cooldown_s} seconds")
                    return


    def is_inCool(self, ip, current_time):
        with self.lock:
            return ip in self.attempts and self.attempts[ip].get('cool_until', 0) > current_time
        
    def is_blocked(self, ip, current_time):
        with self.lock:
            return ip in self.attempts and self.attempts[ip].get('blocked_until', 0) > current_time

    def clean_expired_attempts(self):
        with self.lock:
            current_time = time.monotonic()
            expired_ips = []

            for ip, data in list(self.attempts.items()):
                # Clean expired blocks
                if 'blocked_until' in data and current_time >= data['blocked_until']:
                    logger.print_info(f"Unblocked User[{ip}]\n")
                    logger.log_info(f"- Unblocked User[{ip}]")
                    expired_ips.append(ip)
                    continue

                # Clean raw attempts
                if 'last_time' in data and current_time - data['last_time'] > FileState.CONFIG['cleanup_timeout_m']*60:
                    expired_ips.append(ip)

            # Remove fully expired entries
            for ip in expired_ips:
                del self.attempts[ip]