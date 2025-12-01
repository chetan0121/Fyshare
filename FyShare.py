# Standard library imports
import http.server, socketserver
import os
import socket
import time
import threading
import re, string
import secrets
import json
import logging
from sys import stderr
from logging.handlers import RotatingFileHandler
from html import escape
from urllib.parse import quote, parse_qs
from pathlib import Path

# Custom Func for Styled text-printing
def printCustom(txt="\n", *ansiCode):
    ansiCode = [str(a) for a in ansiCode if isinstance(a, int)]
    ansiCodes = "\033[" + ";".join(ansiCode) + "m"
    msg = str(ansiCodes + txt + "\033[0m")
    stderr.write(f"{msg}\n")  

def printError(msg="\n", end="\n"):
    stderr.write(f"\033[91;1m{msg}\033[0m{end}")  # Text in Red

def printWarning(msg="\n", end="\n"):
    stderr.write(f"\033[33m{msg}\033[0m{end}")  # Text in yellow

# Create Log file in logs
LOG_FILE = Path(__file__).parent / "logs" / "server.log"
LOG_FILE.parent.mkdir(exist_ok=True)

# Logs config
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    datefmt = f"%Y-%m-%d %H:%M:%S"
)

# Handle logging files
file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=1_000_000,
    backupCount=3,
    encoding='utf-8'
)

# Format for Logging
formatter = logging.Formatter(
    fmt='%(asctime)s | %(levelname)-8s | %(threadName)-12s | %(ip)-15s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)

# Load Configuration
CONFIG_PATH = Path(__file__).parent / "config.json"
if not CONFIG_PATH.exists():
    printError("\n[Error]: config.json file not found!\n")
    exit(1)
    
try:
    with CONFIG_PATH.open("r") as f:
        config = json.load(f)
except json.JSONDecodeError:
    printError("\n[Error]: Invalid JSON code in config.json\n")
    exit(1)

# Create dict and Normalize value types of config
CONFIG = {
    "root_directory": str(config["root_directory"]),                        # Root directory served by the server
    "max_users": int(config["max_users"]),                                  # Maximum number of users allowed to access the server
    "idle_timeout_m": int(config["idle_timeout_minutes"]),                  # Automatically stop server after this many minutes of inactivity
    "refresh_time_s": float(config["refresh_time_seconds"]),                # Server refresh/update interval in seconds
    "max_attempts": int(config["max_attempts_per_ip"]),                     # Allowed failed attempts per IP before cooldown
    "cooldown_s": int(config["cooldown_seconds"]),                          # Cooldown duration for an IP after exceeding "max_attempts"
    "max_total_attempts": int(config["max_total_attempts_per_ip"]),         # Total allowed attempts before IP is blocked
    "block_time_m": int(config["block_time_minutes"]),                      # Duration of an IP remains blocked (after reaching "max_total_attempts")
    "cleanup_timeout_m": int(config["cleanup_timeout_minutes"]),            # Time in minutes, before old attempts are cleaned up
    "cache_time_out_s": float(config["default_cache_time_out_seconds"])     # Cache duration for static files (HTML, CSS, etc...)
}

# ==== Global variables and Constants ====
TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"

GLOBAL_TOTAL_ATTEMPTS = 0
LAST_UPDATED_CRED = None
INACTIVITY_START = None

# Global thread_lock for credential related updates
credentials_lock = threading.Lock()

# Session timeout options (CONSTANT)
OPTIONS = [
    (5, "5 minutes"),
    (15, "15 minutes"),
    (30, "30 minutes"),
    (60, "1 hour"),
    (120, "2 hours"),
]
OPTIONS.sort(key=lambda x: x[0])
# ========================================

# Session Manage class (Handles users/session)
class SessionManager:
    def __init__(self):
        self.sessions = {}  # {token: {'ip': ip, 'expiry': timestamp}}
        self.attempts = {}  # {ip: {'count': int, 'last_time': time, 'cool_until: time', 'blocked_until': time}}
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
                print(f"\n- Session expired for User[{self.sessions[token]['ip']}]\n")
                logging.info(f"Session expired for User[{self.sessions[token]['ip']}]")
                del self.sessions[token]

    def update_attempts(self, ip, current_time):
        with self.lock:
            if ip not in self.attempts:
                self.attempts[ip] = {'count': 1, 'last_time': current_time}
            else:
                data = self.attempts[ip]
                data['count'] += 1
                data['last_time'] = current_time

                if data['count'] >= CONFIG['max_total_attempts']:
                    data['blocked_until'] = current_time + CONFIG['block_time_m'] * 60
                    printWarning(f"\n- Blocked IP[{ip}] for {CONFIG['block_time_m']} minutes due to excessive attempts.\n")
                    logging.warning(f"Blocked User[{ip}] for {CONFIG['block_time_m']} minutes")
                    return

                if data['count'] % CONFIG['max_attempts'] == 0:
                    data['cool_until'] = current_time + CONFIG['cooldown_s']
                    print(f"\n- User[{ip}] is in cool-down for {CONFIG['cooldown_s']} seconds due to excessive attempts.\n")
                    logging.info(f"User[{ip}] is in cool-down for {CONFIG['cooldown_s']} seconds")
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
                    print(f"\n- Unblocked User[{ip}]\n")
                    logging.info(f"Unblocked User[{ip}]")
                    expired_ips.append(ip)
                    continue

                # Clean raw attempts
                if 'last_time' in data and current_time - data['last_time'] > CONFIG['cleanup_timeout_m']*60:
                    expired_ips.append(ip)

            # Remove fully expired entries
            for ip in expired_ips:
                del self.attempts[ip]

# Create Obj Of SessionManager Class
SESSION_MANAGER = SessionManager()

# Custom Exception (Inherited Exception class)
class ConfigError(Exception): pass

def checkConfig():
    if CONFIG['max_users'] <= 0 or CONFIG['max_users'] > 100:
        raise ConfigError("max_users must be a natural number from 1 to 100")

    if CONFIG['idle_timeout_m'] <= 1 or CONFIG['idle_timeout_m'] > 1440:
        raise ConfigError("idle_timeout_minutes must be between 1 and 1440 (24-hours)")

    if CONFIG['refresh_time_s'] <= 0 or CONFIG['refresh_time_s'] > 30:
        raise ConfigError("Refresh_time_seconds must be between 1 and 30 seconds")

    if CONFIG['max_attempts'] < 1 or CONFIG['max_attempts'] >= CONFIG['max_total_attempts']:
        raise ConfigError("Invalid attempt limits")
    
    if CONFIG['max_total_attempts'] > 50:
        raise ConfigError("max_total_attempts_per_ip can't be more than 50 numbers")

    if CONFIG['cooldown_s'] < 0 or CONFIG['cooldown_s'] >= CONFIG['block_time_m']*60:
        raise ConfigError("Invalid cooldown_seconds and block_time configuration")
    
    if CONFIG['block_time_m'] > CONFIG['cleanup_timeout_m']:
        raise ConfigError("block_time_minutes can't be more than cleanup_timeout_minutes")
    
    if CONFIG['cleanup_timeout_m'] < 10 or CONFIG['cleanup_timeout_m'] > 120:
        raise ConfigError("cleanup_timeout_minutes must be between 10 and 120 minutes")

    if CONFIG['cache_time_out_s'] < 0 or CONFIG['cache_time_out_s'] > 86400:
        raise ConfigError("default_cache_time_out_seconds must be between 1 and 86400")

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
        local_ip = socket_conn.getsockname()[0]
        
        # Verify it's not a localhost
        if not local_ip.startswith("127."):
            return local_ip
    
    # Bind to all available network interfaces (for LAN)
    return "0.0.0.0"

def generate_credentials(message = str("")):
    global USERNAME, GLOBAL_TOTAL_ATTEMPTS, LOCAL_IP
    with credentials_lock:
        USERNAME = generate_username()
        FileHandler.current_otp = generate_otp()
        
        printWarning(f"\n\n{message}")
        printCustom("---------------------------------------------", 1)
        printCustom(f"\nServing directory: \"{ROOT_DIR}\"", 1)
        printCustom(f"Open in browser: http://{LOCAL_IP}:{PORT}", 1)

        printCustom(f"\nCredentials:", 36, 1)
        print(f"   - Username  : {USERNAME}")
        print(f"   - OTP       : {FileHandler.current_otp}")
        print(f"   - Max users : {CONFIG['max_users']} Allowed")
        print(f"   - Time Out  : {CONFIG['idle_timeout_m']} {'minute' if CONFIG['idle_timeout_m'] == 1 else 'minutes'} of inactivity")
        printCustom("\n---------------------------------------------", 1)

        logging.info(f"Generated New Credentials | Message: {message or 'Nothing'}")


class FileHandler(http.server.SimpleHTTPRequestHandler):
    current_otp = str("")   # Empty string

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT_DIR, **kwargs)

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

    def do_GET(self):
        client_ip = self.client_address[0]
        current_time = time.monotonic()

        if SESSION_MANAGER.is_blocked(client_ip, current_time):
            self.send_response(403, "Access Denied")
            self.send_security_headers()
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b'<h1>403 Forbidden</h1><p>Blocked due to excessive attempts. Try again later.</p>')
            return

        if self.path == '/favicon.ico':
            favicon_path = STATIC_DIR / 'favicon.ico'
            if favicon_path.exists():
                with favicon_path.open('rb') as f:
                    self.send_response(200)
                    self.send_security_headers(cache_time=CONFIG['cache_time_out_s'])
                    self.send_header('Content-Type', 'image/x-icon')
                    self.end_headers()
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "Favicon not found")
                return

        if self.path == '/logout':
            session_token = self.get_session_token()
            if session_token and SESSION_MANAGER.get_session(session_token):
                client_ip = SESSION_MANAGER.get_session(session_token)['ip']
                print(f"\n- User[{client_ip}] logged-out.\n", flush=True)
                logging.info(f"User[{client_ip}] logged-out")
                SESSION_MANAGER.remove_session(session_token)

            self.send_response(302)
            self.send_security_headers()
            self.send_header('Location', '/')
            self.send_header('Set-Cookie', 'session_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/')
            self.end_headers()
            return

        if self.path.startswith('/static/'):
            file_path = STATIC_DIR / self.path[len('/static/'):]
            
            if not file_path.exists() or not file_path.is_file():
                self.send_error(404, "File not found")
                printWarning(f"\n- User[{client_ip}] tried to access invalid static file.\n")
                logging.warning(f"User[{client_ip}] tried to access invalid static file")
                return

            try:
                content_type = 'application/octet-stream'
                if file_path.suffix == '.css':
                    content_type = 'text/css'
                elif file_path.suffix == '.js':
                    content_type = 'application/javascript'
                elif file_path.suffix in ('.png', '.jpg', '.jpeg'):
                    content_type = 'image/' + ('png' if file_path.suffix == '.png' else 'jpeg')
                elif file_path.suffix == '.ico':
                    content_type = 'image/x-icon'

                file_size = file_path.stat().st_size
                self.send_response(200)
                self.send_security_headers(cache_time=CONFIG['cache_time_out_s'])
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(file_size))
                self.end_headers()

                with file_path.open('rb') as f:
                    chunk = f.read(65536)   # 64KB chunk
                    while chunk:
                        self.wfile.write(chunk)
                        chunk = f.read(65536)
                return  # Exit after success   
            
            except Exception as e:
                self.send_error(500, f"Internal Server Error")
                printError(f"\nError [Serving file]: {str(e)}\n")
                logging.error(f"Error [Serving file]: {str(e)}")
                return

        if not self.check_authentication():
            self.send_login_page()
            return

        if self.path.endswith('.html'):
            file_path = Path(self.translate_path(self.path))
            if file_path.exists() and file_path.is_file():
                try:
                    file_size = file_path.stat().st_size
                    self.send_response(200)
                    self.send_security_headers(cache_time=CONFIG['cache_time_out_s'])
                    self.send_header('Content-Type', 'text/html')
                    self.send_header('Content-Length', str(file_size))
                    self.end_headers()
                    with file_path.open('rb') as f:
                        chunk = f.read(8192)
                        while chunk:
                            self.wfile.write(chunk)
                            chunk = f.read(8192)
                except Exception as e:
                    self.send_error(500, f"Error: Something went wrong.")
                    printError(f"\nError: Serving html file {str(e)}.\n")
                    logging.error(f"Error [Serving html]: {str(e)}")
            else:
                self.send_error(404, "File not found")
        else:
            super().do_GET()

    def do_POST(self):
        client_ip = self.client_address[0]
        current_time = time.monotonic()

        SESSION_MANAGER.clean_expired_attempts()
        if SESSION_MANAGER.is_blocked(client_ip, current_time):
            self.send_response(403)
            self.send_security_headers()
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b'<h1>403 Forbidden</h1><p>Blocked due to excessive attempts. Try again later.</p>')
            return
        
        if SESSION_MANAGER.is_inCool(client_ip, current_time):
            self.send_login_page(message="Too many attempts. Try again later.")
            return
        
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        params = parse_qs(post_data)

        # Safely type conversion
        try:
            submitted_username = str(params.get('username', [''])[0])
            submitted_otp = str(params.get('otp', [''])[0])
            timeout_seconds = float(params.get('timeout', ['0'])[0])
        except ValueError:
            self.send_login_page(message="Invalid input values.")
            return

        if not self.validate_credentials(submitted_username, submitted_otp, timeout_seconds):
            self.send_login_page(message="Invalid input. Please check your username and OTP format.")
            return

        if len(SESSION_MANAGER.sessions) >= CONFIG['max_users']:
            self.send_login_page(message="Server busy—too many users. Try again later.")
            return

        with credentials_lock:
            if submitted_username == USERNAME and submitted_otp == self.current_otp:
                session_token = secrets.token_hex(32)
                SESSION_MANAGER.add_session(session_token, client_ip, current_time + timeout_seconds)
                max_age = int(timeout_seconds)

                self.send_response(302)
                self.send_security_headers()
                self.send_header('Location', self.path)
                self.send_header('Set-Cookie', f'session_token={session_token}; Path=/; HttpOnly; Max-Age={max_age}; SameSite=Strict')
                self.end_headers()

                print(f"\n- User[{client_ip}] logged-in on seconds: {max_age}\n")
                logging.info(f"User[{client_ip}] logged-in")
            else:
                SESSION_MANAGER.update_attempts(client_ip, current_time)
                global GLOBAL_TOTAL_ATTEMPTS
                GLOBAL_TOTAL_ATTEMPTS += 1
                if GLOBAL_TOTAL_ATTEMPTS > CONFIG['max_users']*100:
                    printWarning(f"\n- Total attempts exceeded the limit {CONFIG['max_users']*100} attempts.")
                    print("\nShutting down the server...\n", flush=True)
                    logging.warning(f"Shutting down server after Total {GLOBAL_TOTAL_ATTEMPTS} rapid attempts of login")
                    exit(1)

                if GLOBAL_TOTAL_ATTEMPTS % CONFIG['max_users']*10 == 0:
                    global LAST_UPDATED_CRED
                    LAST_UPDATED_CRED = None
                    generate_credentials("Too many failed attempts on server")

                self.send_login_page(message="Invalid username or OTP.")

    def validate_credentials(self, username, otp, timeout):
        # Validate username: 6–20 alphanumeric characters
        is_valid_username = bool(re.fullmatch(r'[a-zA-Z0-9]{6,20}', username))

        # Validate OTP: exactly 6 digits
        is_valid_otp = bool(re.fullmatch(r'\d{6}', otp))

        # Validate timeout: must be between min and max allowed seconds
        is_valid_timeout = bool((OPTIONS[0][0]*60) <= timeout <= (OPTIONS[-1][0]*60))

        return is_valid_username and is_valid_otp and is_valid_timeout

    def check_authentication(self):
        session_token = self.get_session_token()
        session_data = SESSION_MANAGER.get_session(session_token)

        if not session_token or not session_data:
            return False
        if session_data['ip'] != self.client_address[0]:
            printWarning(f"\n- Session-token stolen from {session_data['ip']}, Request terminated!\n")
            logging.warning(f"Session-token stolen from User[{session_data['ip']}]")
            SESSION_MANAGER.remove_session(session_token)
            return False
        if time.monotonic() >= session_data['expiry']:
            SESSION_MANAGER.remove_session(session_token)
            return False
        
        return True

    def send_login_page(self, message=None):
        try:
            html = LOGIN_TEMPLATE
            options_html = "\n".join(f'<option value="{mins*60}">{label}</option>' for mins, label in OPTIONS)
            html = html.replace('{{options}}', options_html)
            html = html.replace('{{message}}', message or '')
            self.send_response(200)
            self.send_security_headers()
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        except Exception as e:
            self.send_error(500, f"Error: Something went wrong.")
            printError(f"\nError [Rendering login page]: {str(e)}\n", flush=True)
            logging.error(f"Error [Rendering login page]: {str(e)}")

    def translate_path(self, path):
        path = super().translate_path(path)
        real_path = Path(path).resolve()
        if not str(real_path).startswith(str(Path(ROOT_DIR).resolve())):
            self.send_error(403, "Access denied")
            return None
        
        return str(real_path)

    def list_directory(self, path):
        try:
            with os.scandir(path) as entries:
                file_list = list(entries)
        except PermissionError:
            self.send_error(403, "Permission denied")
            return None
        except FileNotFoundError:
            self.send_error(404, "Directory not found.")
            return None
        except Exception as e:
            self.send_error(500, "Internal Server Error")
            printError(f"\nError generating directory list for {path}: {str(e)}\n")
            logging.error(f"Error generating directory list for {path}: {str(e)}")
            return None

        file_list.sort(key=lambda a: (not a.is_dir(), a.name.lower()))
        displaypath = os.path.relpath(path, ROOT_DIR).strip('/.') or '.'

        try:
            response = self.generate_html(file_list, displaypath)
            encoded = response.encode('utf-8')
            self.send_response(200)
            self.send_security_headers()
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
        except Exception as e:
            self.send_error(500, f"Error generating response.")
            printError(f"\nError [generating response]: {str(e)}\n")
            logging.error(f"Error [generating response]: {str(e)}")

    def generate_html(self, file_list, displaypath):
        if not FILE_MANAGER_TEMPLATE:
            self.send_error(500, "Something went wrong.")
            printError("\nError: FILE_MANAGER_TEMPLATE is undefined or empty\n", flush=True)
            exit(1)
        
        template = FILE_MANAGER_TEMPLATE
        breadcrumbs = self.generate_breadcrumbs(displaypath)
        table_rows = ""
        if displaypath != '.':
            table_rows += """
                <tr>
                    <td>
                        <a href="../">
                            <span class="icon">📁</span>
                            <span> /.. </span>
                        </a>
                    </td>
                    <td class="size">-</td>
                    <td></td>
                </tr>
            """
            
        for entry in file_list:
            if entry.name.startswith('.'):
                continue

            try:
                is_dir = entry.is_dir()
                display_name = escape(entry.name)
                link_name = quote(entry.name)
                icon = self.get_file_icon(entry.name, is_dir)
                size = '-' if is_dir else self.format_size(entry.stat().st_size)
                action = self.get_action_button(entry.name, is_dir)
                table_rows += f"""
                <tr>
                    <td>
                        <a href="{link_name}">
                            <span class="icon">{icon}</span>
                            <span>{display_name}</span>
                        </a>
                    </td>
                    <td class="size">{size}</td>
                    <td>{action}</td>
                </tr>"""
            except Exception as e:
                printError(f"\nError processing {entry.name}: {str(e)}\n")
                continue
            
        return template.replace('{{breadcrumbs}}', breadcrumbs).replace('{{table_rows}}', table_rows)

    def join_posix(self, a, b):
        a = (a or "").rstrip('/')
        b = (b or "").lstrip('/')
        if not a:
            return b
        return f"{a}/{b}"

    def generate_breadcrumbs(self, path):
        path = path.replace('\\', '/').strip('/. ')
        parts = path.split('/')
        breadcrumbs = ['<a href="/">🏠 Home</a>']
        current_path = ""

        for part in parts:
            if not part or part == '.':
                continue

            current_path = self.join_posix(current_path, part)
            breadcrumbs.append(
                f'<span class="breadcrumb-sep">/</span>'
                f'<a href="/{quote(current_path)}">{escape(part)}</a>'
            )
        return ''.join(breadcrumbs)

    def get_file_icon(self, filename, is_dir):
        if is_dir:
            return "📁"
        
        ext = os.path.splitext(filename)[1].lower()
        icons = {
            '.pdf': '📕', '.doc': '📄', '.docx': '📄', '.xls': '📊', '.xlsx': '📊', '.ppt': '📑',
            '.pptx': '📑', '.txt': '📝', '.csv': '📋', '.jpg': '🖼️', '.jpeg': '🖼️', '.png': '🖼️',
            '.gif': '🖼️', '.bmp': '🖼️', '.svg': '🖼️', '.mp3': '🎵', '.wav': '🎵', '.ogg': '🎵',
            '.mp4': '🎬', '.avi': '🎬', '.mkv': '🎬', '.zip': '📦', '.rar': '📦', '.7z': '📦',
            '.apk': '📱', '.exe': '⚙️', '.py': '🐍', '.html': '🌐', '.js': '📜', '.json': '📜'
        }
        return icons.get(ext, '📄')

    def get_action_button(self, filename, is_dir):
        if is_dir:
            return ""
        return f'<a class="download-btn" href="{quote(filename)}" download>⬇️ Download</a>'

    def format_size(self, size_bytes):
        try:
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if size_bytes < 1024.0:
                    return f"{size_bytes:.1f} {unit}"
                size_bytes /= 1024.0
            return f"{size_bytes:.1f} PB"
        except TypeError:
            return "N/A"

if __name__ == "__main__":
    # Verify configuration settings
    try:
        checkConfig()
    except ConfigError as e:
        printError(f"\nError[Config]: {e}")
        print("Result: Stopped initializing server")
        exit(1)

    # Default OS Root directory detection
    if CONFIG["root_directory"] == "%DEFAULT%":
        CONFIG["root_directory"] = os.path.expanduser("~")

    # Define Root directory as selected
    ROOT_DIR = Path(CONFIG["root_directory"])

    # Path selection by User
    print("\nSelect path to host:")
    print(f"1. Default ({ROOT_DIR})")
    print( "2. Custom path")
    try:
        opt = int(input("\nEnter option => "))
        if opt == 2:
            ROOT_DIR = Path(input("\nEnter path: "))
        elif opt != 1:
            printError("\nError: Invalid option\n")
            exit(1)
    except ValueError:
        printError("\nError [ValueError]: Invalid input\n")
        exit(1)
    
    # Verify all paths
    if not ROOT_DIR.exists():
        printError(f"\nError: Root directory {ROOT_DIR} not found!")
        exit(1)
    if not TEMPLATES_DIR.exists():
        printError(f"\nError: Templates directory {TEMPLATES_DIR} not found!")
        exit(1)
    if not STATIC_DIR.exists():
        printError(f"\nError: Static directory {STATIC_DIR} not found!")
        exit(1)
    if not os.access(ROOT_DIR, os.R_OK):
        printError(f"\nError: No read permissions for {ROOT_DIR}")
        exit(1)

    # Verify and load template files
    try:
        with (TEMPLATES_DIR / 'login.html').open('r', encoding="utf-8") as f:
            LOGIN_TEMPLATE = f.read()
        with (TEMPLATES_DIR / 'fyshare.html').open('r', encoding="utf-8") as f:
            FILE_MANAGER_TEMPLATE = f.read()
    except FileNotFoundError as e:
        printError(f"\nError [Template files not found]: {e}\n")
        logging.error(f"Error [Template files not found]: {e}")
        exit(1)

    # Randomly select port between 1500 and 9500
    PORT = secrets.choice(range(1500, 9500))

    # Fetch Current device's IP
    LOCAL_IP = get_local_ip()

    # Initialize the server and check if randomly selected port is available
    try:
        server = socketserver.ThreadingTCPServer(("", PORT), FileHandler)
        server.timeout = CONFIG["refresh_time_s"]
    except OSError as e:
        printError(f"\nError [Initializing server]: Failed to bind to port[{PORT}], Please try again.")
        print("Details:", e)
        exit(1)
    except Exception as e:
        printError(f"\nError [Initializing server]: {str(e)}")
        exit(1)

    # Generate and print new credentials
    generate_credentials()
    print("Refer to ReadMe.md for secure file-sharing instructions.\n")

    logging.info(f"Started server 'http://{LOCAL_IP}:{PORT}' | Root directory: '{ROOT_DIR}'")

    # Constant configs
    cleanup_time_s = CONFIG['cleanup_timeout_m'] * 60
    idle_timeout_s = CONFIG['idle_timeout_m'] * 60

    try:
        while True:
            # Clean expired sessions and update current time
            SESSION_MANAGER.clean_expired_sessions()
            current_time = time.monotonic()

            # Auto update credentials after cleanUp time
            if LAST_UPDATED_CRED is None:
                LAST_UPDATED_CRED = current_time
            elif current_time - LAST_UPDATED_CRED > cleanup_time_s:
                LAST_UPDATED_CRED = current_time
                generate_credentials("Old Credentials expired!")

            # Handle inactivity timeout
            if not SESSION_MANAGER.sessions and INACTIVITY_START is None:
                INACTIVITY_START = current_time
            elif SESSION_MANAGER.sessions:
                INACTIVITY_START = None

            # Continually handle incoming requests, one at a time (return after server.timeout)
            server.handle_request()

            # Shutdown server automatically after idle-timeout
            if INACTIVITY_START and (current_time - INACTIVITY_START) > idle_timeout_s:
                minutePrint = 'minute' if CONFIG['idle_timeout_m'] == 1 else 'minutes'
                print(f"\n- Server closed after {CONFIG['idle_timeout_m']} {minutePrint} of inactivity.\n")
                logging.info(f"Server closed after {CONFIG['idle_timeout_m']} {minutePrint} of inactivity\n")
                break

    # Handle manual shutdown in the terminal (e.g. Ctrl+C)
    except KeyboardInterrupt:
        print("\n\n- Server stopped manually!")
        logging.info("Server stopped manually\n")
