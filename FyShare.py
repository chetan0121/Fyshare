# Standard library imports
import http.server, socketserver
import os
import posixpath
import socket
import random
import time
import threading
import re
import string
import secrets
import json
from html import escape
from urllib.parse import quote, parse_qs
from pathlib import Path

# Configuration loading
CONFIG_PATH = Path(__file__).parent / "config.json"
if not CONFIG_PATH.exists():
    print("\n\nError: config.json file not found!\n")
    exit(1)

try:
    with CONFIG_PATH.open("r") as f:
        config = json.load(f)
except json.JSONDecodeError:
    print("\nError: Invalid JSON in config.json!\n")
    exit(1)

CONFIG = {
    "root_directory": str(config["root_directory"]),  # Serving root directory
    "max_users": int(config["max_users"]),  # Max users to access server
    "idle_timeout_minutes": int(config["idle_timeout_minutes"]),  # Auto stopping server based on inactivity
    "refresh_time_seconds": float(config["refresh_time_seconds"]),  # Server Refresh time
    "max_attempts_per_ip": int(config["max_attempts_per_ip"]),  # legal attempts before cool-down
    "cooldown_seconds": float(config["cooldown_seconds"]),    # IP in coolDown if exceed max_attempts
    "max_total_attempts_per_ip": int(config["max_total_attempts_per_ip"]),
    "block_time_minutes": int(config["block_time_minutes"]),    # IP Blocked if exceed max_total_attempts
    "cleanup_timeout": int(config["cleanup_timeout_minutes"]),  # Clean up old attempts, by timeout in minutes
    "update_credentials_after_attempts": int(config["update_credentials_after_attempts"]),
    "cache_time_out_seconds": float(config["default_cache_time_out_seconds"]) # Cache for static files (Webpage, html, css)
}

# Global variables
TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"
USERNAME = None  # Initialized later
PORT = random.randint(1500, 9500)
GLOBAL_TOTAL_ATTEMPTS = 0
INACTIVITY_START = None
LAST_UPDATED_CRED = None

# Global thread_lock for credential related updates
credentials_lock = threading.Lock()

# Session timeout options
OPTIONS = [
    (5, "5 minutes"),
    (15, "15 minutes"),
    (30, "30 minutes"),
    (60, "1 hour"),
    (120, "2 hours")
]


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
            current_time = time.time()
            expired = [t for t, s in self.sessions.items() if current_time > s['expiry']]
            for token in expired:
                print(f"\n- Session expired for IP: [{self.sessions[token]['ip']}]\n")
                del self.sessions[token]

    def update_attempts(self, ip, current_time):
        with self.lock:
            if ip not in self.attempts:
                self.attempts[ip] = {'count': 1, 'last_time': current_time}
            else:
                data = self.attempts[ip]
                data['count'] += 1
                data['last_time'] = current_time

                if data['count'] >= CONFIG['max_total_attempts_per_ip']:
                    data['blocked_until'] = current_time + CONFIG['block_time_minutes'] * 60
                    print(f"\n- Blocked IP[{ip}] for {CONFIG['block_time_minutes']} minutes due to excessive attempts.\n")
                    return

                if data['count'] % CONFIG['max_attempts_per_ip'] == 0:
                    data['cool_until'] = current_time + CONFIG['cooldown_seconds']
                    print(f"\n- UserIP[{ip}] is in cool-down for {CONFIG['cooldown_seconds']} seconds due to excessive attempts.\n")
                    return


    def is_inCool(self, ip, current_time):
        with self.lock:
            return ip in self.attempts and self.attempts[ip].get('cool_until', 0) > current_time
        
    def is_blocked(self, ip, current_time):
        with self.lock:
            return ip in self.attempts and self.attempts[ip].get('blocked_until', 0) > current_time

    def clean_expired_attempts(self):
        with self.lock:
            current_time = time.time()
            expired_ips = []

            for ip, data in list(self.attempts.items()):
                # Clean expired blocks
                if 'blocked_until' in data and current_time >= data['blocked_until']:
                    print(f"\n- Unblocked IP: {ip}\n")
                    expired_ips.append(ip)
                    continue

                # Clean raw attempts
                if 'last_time' in data and current_time - data['last_time'] > CONFIG['cleanup_timeout']*60:
                    expired_ips.append(ip)

            # Remove fully expired entries
            for ip in expired_ips:
                del self.attempts[ip]


SESSION_MANAGER = SessionManager()

def checkConfig():  # To validate config.json 
    if CONFIG['max_users'] <= 0:
        return False
    if CONFIG['idle_timeout_minutes'] <= 1:
        return False
    if CONFIG['refresh_time_seconds'] <= 0 or CONFIG['refresh_time_seconds'] > 600:
        print("\nError CONFIG : Invalid refresh time.")
        return False
    if not CONFIG['max_attempts_per_ip'] < CONFIG['max_total_attempts_per_ip'] or CONFIG['max_attempts_per_ip'] <= 1:
        print("\nError CONFIG : Bad attempt config.")
        return False
    if CONFIG['cooldown_seconds'] <= 1 or not CONFIG['cooldown_seconds'] < CONFIG['block_time_minutes']*60 or CONFIG['block_time_minutes'] > CONFIG['cleanup_timeout']:
        print("\nError CONFIG : Bad time config.")
        return False
    if CONFIG['update_credentials_after_attempts'] < 5 or CONFIG['cache_time_out_seconds'] < 0:
        return False

    return True

def generate_username():
    # pick 4–5 letters
    chars = ''.join(secrets.choice(string.ascii_lowercase) for _ in range(secrets.choice([4, 5])))

    # pick 3–4 digits
    digits = ''.join(secrets.choice(string.digits) for _ in range(secrets.choice([3, 4])))

    return chars + digits   # return generated letters and digits as a single string

def generate_otp(length=6):
    return ''.join(secrets.choice(string.digits) for _ in range(length))

def generate_session_token():
    return secrets.token_hex(32)

def get_local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"  # Fallback to local

def update_credentials(message = "\n\n ⚠️  Warning: Only run this on your private networks."):
    global USERNAME, GLOBAL_TOTAL_ATTEMPTS
    with credentials_lock:
        local_ip = get_local_ip()
        USERNAME = generate_username()
        FileHandler.current_otp = generate_otp()
        
        print(f"\n{str(message)}")
        print("---------------------------------------------")
        print(f"\n📍 Serving \"{ROOT_DIR}\" at:")
        print(f"🌐 Access  : http://{local_ip}:{PORT}  <- PORT")

        print(f"\n🔐 Credentials:")
        print(f"   👤 Username  : {USERNAME}")
        print(f"   🔑 OTP       : {FileHandler.current_otp}")
        print(f"   👥 Max users : {CONFIG['max_users']} Allowed")
        print(f"   ⏳ Time Out  : {CONFIG['idle_timeout_minutes']} minutes of inactivity")
        print("\n---------------------------------------------")

        if GLOBAL_TOTAL_ATTEMPTS > CONFIG['update_credentials_after_attempts']*10:
            print(f"\n- Total attempts exceeded the limit {CONFIG['update_credentials_after_attempts']*10} attempts.")
            print("\nShutting down the server...\n", flush=True)
            exit(1)


class FileHandler(http.server.SimpleHTTPRequestHandler):
    current_otp = str("") # Empty string, not None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=CONFIG["root_directory"], **kwargs)

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
        current_time = time.time()

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
                    self.send_security_headers(cache_time=CONFIG['cache_time_out_seconds'])
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
                print(f"\n- User[{client_ip}] tried to access invalid static file.\n")
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
                self.send_security_headers(cache_time=CONFIG['cache_time_out_seconds'])
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(file_size))
                self.end_headers()

                with file_path.open('rb') as f:
                    while chunk := f.read(65536):   # 64KB Chunks
                        self.wfile.write(chunk)
                return  # Exit after success   
            
            except Exception as e:
                self.send_error(500, f"Internal Server Error")
                print(f"\nError: Serving file {str(e)}\n")
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
                    self.send_security_headers(cache_time=CONFIG['cache_time_out_seconds'])
                    self.send_header('Content-Type', 'text/html')
                    self.send_header('Content-Length', str(file_size))
                    self.end_headers()
                    with file_path.open('rb') as f:
                        while chunk := f.read(8192):
                            self.wfile.write(chunk)
                except Exception as e:
                    self.send_error(500, f"Error: Something went wrong.")
                    print(f"\nError: Serving html file {str(e)}.\n")
            else:
                self.send_error(404, "File not found")
        else:
            super().do_GET()

    def do_POST(self):
        client_ip = self.client_address[0]
        current_time = time.time()

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

        submitted_username = params.get('username', [''])[0]
        submitted_otp = params.get('otp', [''])[0]

        # Safely type conversion
        try:
            timeout_seconds = float(params.get('timeout', ['0'])[0])
        except ValueError:
            self.send_login_page(message="Invalid format for session duration.")
            return

        if not self.validate_credentials(submitted_username, submitted_otp, timeout_seconds):
            self.send_login_page(message="Invalid credentials.")
            return

        if any(s['ip'] == client_ip for s in SESSION_MANAGER.sessions.values()):
            self.send_login_page(message="You already have an active session.")
            return
        
        if len(SESSION_MANAGER.sessions) >= CONFIG['max_users']:
            self.send_login_page(message="Server busy—too many users. Try again later.")
            return

        with credentials_lock:
            if submitted_username == USERNAME and submitted_otp == self.current_otp:
                session_token = generate_session_token()
                SESSION_MANAGER.add_session(session_token, client_ip, current_time + timeout_seconds)
                max_age = int(SESSION_MANAGER.get_session(session_token)['expiry'] - current_time)

                if max_age > 0:
                    self.send_response(302)
                    self.send_security_headers()
                    self.send_header('Location', self.path)
                    self.send_header('Set-Cookie', f'session_token={session_token}; Path=/; HttpOnly; Max-Age={max_age+60}; SameSite=Strict')
                    self.end_headers()
                else:
                    self.send_login_page(message="Session expired. Please log in again.")
            else:
                SESSION_MANAGER.update_attempts(client_ip, current_time)
                global GLOBAL_TOTAL_ATTEMPTS
                GLOBAL_TOTAL_ATTEMPTS += 1
                if GLOBAL_TOTAL_ATTEMPTS % CONFIG['update_credentials_after_attempts'] == 0:
                    update_credentials("⚠️ Too many failed attempts on server")

                self.send_login_page(message="Invalid username or OTP.")

    def validate_credentials(self, username, otp, timeout):
        return (re.match(r'^[a-zA-Z0-9]{6,20}$', username) and re.match(r'^\d{6}$', otp) and (60 <= timeout <= 7200))

    def check_authentication(self):
        session_token = self.get_session_token()
        session_data = SESSION_MANAGER.get_session(session_token)

        if not session_token or not session_data:
            return False
        if session_data['ip'] != self.client_address[0]:
            print(f"\n- Session-token stolen from {session_data['ip']}, Request terminated!\n")
            SESSION_MANAGER.remove_session(session_token)
            return False
        if time.time() >= session_data['expiry']:
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
            print(f"\nError: Rendering login page ({str(e)})\n", flush=True)

    def translate_path(self, path):
        path = super().translate_path(path)
        real_path = Path(path).resolve()
        if not str(real_path).startswith(str(Path(CONFIG["root_directory"]).resolve())):
            self.send_error(403, "Access denied")
            return ""
        
        return str(real_path)

    def list_directory(self, path):
        try:
            with os.scandir(path) as entries:
                file_list = list(entries)
        except PermissionError:
            self.send_error(403, "Permission denied")
            return None
        except FileNotFoundError:
            self.send_error(404, 'Directory not found.')
            return None
        except Exception as e:
            self.send_error(500, "Internal Server Error")
            print(f"\nError generating directory listing for {path}: {str(e)}\n")
            return None

        file_list.sort(key=lambda a: (not a.is_dir(), a.name.lower()))
        displaypath = os.path.relpath(path, CONFIG["root_directory"]).strip('/.') or '.'

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
            print(f"\nError generating response: {str(e)}\n")

    def generate_html(self, file_list, displaypath):
        if not FILE_MANAGER_TEMPLATE:
            self.send_error(500, "Something went wrong.")
            print("\nError: FILE_MANAGER_TEMPLATE is undefined or empty\n", flush=True)
            return ""
        
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
                </tr>"""
            
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
                print(f"\nError processing {entry.name}: {str(e)}\n")
                continue
            
        return template.replace('{{breadcrumbs}}', breadcrumbs).replace('{{table_rows}}', table_rows)

    def generate_breadcrumbs(self, path):
        path = path.replace('\\', '/').strip('/. ')
        parts = path.split('/')
        breadcrumbs = ['<a href="/">🏠 Home</a>']
        current_path = ''
        for part in parts:
            if not part or part == '.':
                continue
            current_path = posixpath.join(current_path, part)
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
    if not checkConfig():
        print("\n- Error: Invalid config!\n")
        exit(1)

    # Default OS Root directory detection
    if CONFIG["root_directory"] == "%DEFAULT%":
        CONFIG["root_directory"] = os.path.expanduser("~")

    # Path selection by User
    print("\nSelect path:")
    print(f"1. Default ({CONFIG["root_directory"]})")
    print("2. Custom path")
    opt = int(input("\nEnter option => "))
    if opt == 2:
        CONFIG["root_directory"] = str(input("\nEnter path: "))
    elif opt != 1:
        print("\nInvalid option!\n")
        exit(1)

    ROOT_DIR = Path(CONFIG["root_directory"])
    
    if not ROOT_DIR.exists():
        print(f"\nError: Root directory {ROOT_DIR} not found!\n")
        exit(1)
    if not TEMPLATES_DIR.exists():
        print(f"\nError: Templates directory {TEMPLATES_DIR} not found!\n")
        exit(1)
    if not STATIC_DIR.exists():
        print(f"\nError: Static directory {STATIC_DIR} not found!\n")
        exit(1)
    if not os.access(ROOT_DIR, os.R_OK):
        print(f"\nError: No read permissions for {ROOT_DIR}\n")
        exit(1)

    # Load template files
    try:
        with (TEMPLATES_DIR / 'login.html').open('r', encoding="utf-8") as f:
            LOGIN_TEMPLATE = f.read()
        with (TEMPLATES_DIR / 'index.html').open('r', encoding="utf-8") as f:
            FILE_MANAGER_TEMPLATE = f.read()
    except FileNotFoundError as e:
        print(f"\nError Template files not found: {e}\n")
        exit(1)

    # Checking if port available 
    Handler = FileHandler
    try:
        server = socketserver.ThreadingTCPServer(("", PORT), Handler)
    except OSError:
        print("\nError: Port selection failed, try again.")
        exit(1)

    update_credentials() # Generate new credentials
    print("- Follow instructions of ReadMe.md for secure File-Sharing.\n")

    server.timeout = CONFIG["refresh_time_seconds"]

    try:
        while True:
            SESSION_MANAGER.clean_expired_sessions()
            current_time = time.time()

            # Auto update credentials after cleanUp time
            if LAST_UPDATED_CRED is None:
                LAST_UPDATED_CRED = current_time
            elif current_time - LAST_UPDATED_CRED > CONFIG['cleanup_timeout']*60:
                LAST_UPDATED_CRED = current_time
                update_credentials(" ⏱️  Old Credentials expired: ")

            # Handle inactivity timeout
            if not SESSION_MANAGER.sessions and INACTIVITY_START is None:
                INACTIVITY_START = current_time
            elif SESSION_MANAGER.sessions:
                INACTIVITY_START = None

            server.handle_request()
            if INACTIVITY_START and current_time - INACTIVITY_START > CONFIG['idle_timeout_minutes'] * 60:
                print(f"\n- The server closed after {CONFIG['idle_timeout_minutes']} {'minute' if CONFIG['idle_timeout_minutes'] <= 1 else 'minutes'} of inactivity.\n")
                break

    except KeyboardInterrupt:
        print("\n\n- Server stopped manually!\n")
