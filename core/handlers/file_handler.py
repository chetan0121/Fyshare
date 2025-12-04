from html import escape
import time
import http.server
import os
from pathlib import Path
from urllib.parse import parse_qs, quote
from core import credentials, server
from core.utils import logger, helper
from core.utils.security import Security
from core.state import FileState, ServerState

class FileHandler(http.server.SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FileState.ROOT_DIR), **kwargs)

    def do_GET(self):
        client_ip = self.client_address[0]
        current_time = time.monotonic()

        if ServerState.SESSION_MANAGER.is_blocked(client_ip, current_time):
            self.send_response(403, "Access Denied")
            Security.send_security_headers(self)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b'<h1>403 Forbidden</h1><p>Blocked due to excessive attempts. Try again later.</p>')
            return

        if self.path == '/favicon.ico':
            favicon_path = FileState.STATIC_DIR / 'favicon.ico'
            if favicon_path.exists():
                with favicon_path.open('rb') as f:
                    self.send_response(200)
                    Security.send_security_headers(self, cache_time=FileState.CONFIG['cache_time_out_s'])
                    self.send_header('Content-Type', 'image/x-icon')
                    self.end_headers()
                    self.wfile.write(f.read())
                return    
            else:
                self.send_error(404, "Favicon not found")
                return

        if self.path == '/logout':
            session_token = Security.get_session_token(self)
            session = ServerState.SESSION_MANAGER.get_session(session_token)
            if session_token and session:
                client_ip = session['ip']
                logger.print_info(f"User[{client_ip}] logged-out.\n")
                logger.log_info(f"- User[{client_ip}] logged-out")
                ServerState.SESSION_MANAGER.remove_session(session_token)

            self.send_response(302)
            Security.send_security_headers(self)
            self.send_header('Location', '/')
            self.send_header('Set-Cookie', 'session_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/')
            self.end_headers()
            return

        if self.path.startswith('/static/'):
            file_path = FileState.STATIC_DIR / self.path[len('/static/'):]
            
            if not file_path.exists() or not file_path.is_file():
                self.send_error(404, "File not found")
                logger.print_warning(f"User[{client_ip}] tried to access invalid static file.\n")
                logger.log_warning(f"User[{client_ip}] tried to access invalid static file")
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
                Security.send_security_headers(self, cache_time=FileState.CONFIG['cache_time_out_s'])
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
                logger.print_error(f"Serving file: {str(e)}\n")
                logger.log_error(f"Serving file: {str(e)}")
                return

        if not self.check_authentication():
            self.send_login_page()
            return

        if self.path.endswith('.html'):
            file_path = self.translate_path(self.path)
            if file_path.exists() and file_path.is_file():
                try:
                    file_size = file_path.stat().st_size
                    self.send_response(200)
                    Security.send_security_headers(self, cache_time=FileState.CONFIG['cache_time_out_s'])
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
                    logger.print_error(f"Serving html file: {str(e)}.\n")
                    logger.log_error(f"Serving html file: {str(e)}")
            else:
                self.send_error(404, "File not found")
        else:
            super().do_GET()

    def do_POST(self):
        client_ip = self.client_address[0]
        current_time = time.monotonic()

        ServerState.SESSION_MANAGER.clean_expired_attempts()
        if ServerState.SESSION_MANAGER.is_blocked(client_ip, current_time):
            self.send_response(403)
            Security.send_security_headers(self)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b'<h1>403 Forbidden</h1><p>Blocked due to excessive attempts. Try again later.</p>')
            return
        
        if ServerState.SESSION_MANAGER.is_inCool(client_ip, current_time):
            self.send_login_page(message="Too many attempts. Try again later.")
            return
        
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        params = parse_qs(post_data)

        # Safely type conversion
        try:
            submitted_username = str(params.get('username', [''])[0])
            submitted_otp = str(params.get('otp', [''])[0])
            timeout_seconds = int(params.get('timeout', ['0'])[0])
        except ValueError:
            self.send_login_page(message="Invalid input values.")
            return

        if not Security.validate_credentials(self, submitted_username, submitted_otp, timeout_seconds):
            self.send_login_page(message="Invalid input. Please check your username and OTP format.")
            return

        if len(ServerState.SESSION_MANAGER.sessions) >= FileState.CONFIG['max_users']:
            self.send_login_page(message="Server busy—too many users. Try again later.")
            return
        
        if submitted_username == ServerState.USERNAME and submitted_otp == ServerState.OTP:
            session_token = credentials.generate_session_token()
            ServerState.SESSION_MANAGER.add_session(session_token, client_ip, current_time + timeout_seconds)

            self.send_response(302)
            Security.send_security_headers(self)
            self.send_header('Location', '/')
            self.send_header('Set-Cookie', f'session_token={session_token}; Path=/; HttpOnly; Max-Age={timeout_seconds}; SameSite=Strict')
            self.end_headers()

            logger.print_info(f"User[{client_ip}] logged-in")
            logger.log_info(f"- User[{client_ip}] logged-in")
        else:
            ServerState.SESSION_MANAGER.update_attempts(client_ip, current_time)

            with ServerState.credentials_lock:
                ServerState.GLOBAL_TOTAL_ATTEMPTS += 1

            attempts = ServerState.GLOBAL_TOTAL_ATTEMPTS
            if attempts > FileState.CONFIG['max_users']*100:
                server.shutdown_server(f"- Security shutdown triggered after {attempts} rapid login attempts")

            if attempts % (FileState.CONFIG['max_users']*10) == 0:
                credentials.generate_credentials("Too many failed attempts on server")

            self.send_login_page(message="Invalid username or OTP.")

    def check_authentication(self):
        session_token = Security.get_session_token(self)
        session_data = ServerState.SESSION_MANAGER.get_session(session_token)

        if not session_token or not session_data:
            return False
        if session_data['ip'] != self.client_address[0]:
            logger.print_warning(f"Session-token stolen from {session_data['ip']}", "Request terminated!\n")
            logger.log_warning(f"Session-token stolen from User[{session_data['ip']}]")
            ServerState.SESSION_MANAGER.remove_session(session_token)
            return False
        if time.monotonic() >= session_data['expiry']:
            ServerState.SESSION_MANAGER.remove_session(session_token)
            return False
        
        return True

    def send_login_page(self, message=None):
        try:
            html = FileState.LOGIN_HTML
            options_html = "\n".join(f'<option value="{mins*60}">{label}</option>' for mins, label in ServerState.OPTIONS)
            html = html.replace('{{options}}', options_html)
            html = html.replace('{{message}}', message or '')
            self.send_response(200)
            Security.send_security_headers(self)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        except Exception as e:
            self.send_error(500, f"Error: Something went wrong.")
            logger.print_error(f"Rendering login page: {str(e)}\n")
            logger.log_error(f"Rendering login page: {str(e)}")

    def translate_path(self, path) -> Path | None:
        path = super().translate_path(path)
        real_path = helper.refine_path(path)
        if not str(real_path).startswith(str(FileState.ROOT_DIR)):
            self.send_error(403, "Access denied")
            return None
        
        return real_path

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
            logger.print_error(f"Directory-listing {path}: {str(e)}\n")
            logger.log_error(f"Directory-listing {path}: {str(e)}")
            return None

        file_list.sort(key=lambda a: (not a.is_dir(), a.name.lower()))
        displaypath = os.path.relpath(path, FileState.ROOT_DIR).strip('/.') or '.'

        try:
            response = self.generate_html(file_list, displaypath)
            encoded = response.encode('utf-8')
            self.send_response(200)
            Security.send_security_headers(self)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
        except Exception as e:
            self.send_error(500, f"Error generating response.")
            logger.print_error(f"Generating response: {str(e)}\n")
            logger.log_error(f"Generating response: {str(e)}")

    def generate_html(self, file_list, displaypath):
        template = FileState.FYSHARE_HTML
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
                logger.print_error(f"\nProcessing {entry.name}: {str(e)}\n")
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