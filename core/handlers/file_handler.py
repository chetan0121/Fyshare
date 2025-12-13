import time
import os
import http.server as http_server
from pathlib import Path
from urllib.parse import parse_qs
from .html_handler import HTMLHandler
from ..utils import logger
from .. import credentials, server
from .security_mixin import SecurityMixin
from ..state import FileState, ServerState

class FileHandler(SecurityMixin, http_server.SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FileState.ROOT_DIR), **kwargs)

    def copyfile(self, source, outputfile):
        try:
            super().copyfile(source, outputfile)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        session_manager = ServerState.SESSION_MANAGER
        client_ip = self.client_address[0]
        current_time = time.monotonic()

        if session_manager.is_blocked(client_ip, current_time):
            self.send_response(403, "Access Denied")
            self.send_security_headers()
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTMLHandler.blocked_html_message)
            return

        if self.path == '/favicon.ico':
            favicon_path = FileState.STATIC_DIR / 'favicon.ico'
            if favicon_path.exists():
                with favicon_path.open('rb') as f:
                    self.send_response(200)
                    self.send_security_headers(cache_time=FileState.CONFIG['cache_time_out_s'])
                    self.send_header('Content-Type', 'image/x-icon')
                    self.end_headers()
                    self.wfile.write(f.read())
                return    
            else:
                self.send_error(404, "Favicon not found")
                return

        if self.path == '/logout':
            session_token = self.get_session_token()
            session = session_manager.get_session(session_token)
            if session_token and session:
                client_ip = session['ip']
                logger.emit_info(f"User({client_ip}) logged-out")
                session_manager.remove_session(session_token)

            self.send_response(302)
            self.send_security_headers()
            self.send_header('Location', '/')
            self.send_header('Set-Cookie', 'session_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/')
            self.end_headers()
            return

        if self.path.startswith('/static/'):
            file_path = FileState.STATIC_DIR / self.path[len('/static/'):]
            
            if not file_path.exists() or not file_path.is_file():
                self.send_error(404, "File not found")
                logger.emit_warning(f"User[{client_ip}] tried to access invalid static file.")
                return

            try:
                content_type = 'application/octet-stream'
                ext = str(file_path.suffix).lower()
                if ext == '.css':
                    content_type = 'text/css'
                elif ext in ('.js', '.mjs'):
                    content_type = 'application/javascript'
                elif ext == '.png':
                    content_type = 'image/png'
                elif ext in ('.jpg', '.jpeg'):
                    content_type = 'image/jpeg'
                elif ext == '.ico':
                    content_type = 'image/x-icon'

                file_size = file_path.stat().st_size
                self.send_response(200)
                self.send_security_headers(cache_time=FileState.CONFIG['cache_time_out_s'])
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(file_size))
                self.end_headers()

                with file_path.open('rb') as f:
                    while (chunk := f.read(65536)): # 64KB chunk
                        self.wfile.write(chunk)
                return  # Exit after success   
            
            except Exception as e:
                self.send_error(500, f"Internal Server Error")
                logger.emit_error(f"Serving file: {str(e)}")
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
                    self.send_security_headers(cache_time=FileState.CONFIG['cache_time_out_s'])
                    self.send_header('Content-Type', 'text/html')
                    self.send_header('Content-Length', str(file_size))
                    self.end_headers()

                    with file_path.open('rb') as f:
                        while (chunk:= f.read(8192)):   # 8KB chunk
                            self.wfile.write(chunk)
                except Exception as e:
                    self.send_error(500, f"Error: Something went wrong.")
                    logger.emit_error(f"Serving html file: {str(e)}")
            else:
                self.send_error(404, "File not found")
        else:
            super().do_GET()

    def do_POST(self):
        client_ip = self.client_address[0]
        current_time = time.monotonic()

        if ServerState.SESSION_MANAGER.is_blocked(client_ip, current_time):
            self.send_response(403)
            self.send_security_headers()
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTMLHandler.blocked_html_message)
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

        if not self.validate_credentials(submitted_username, submitted_otp, timeout_seconds):
            self.send_login_page(message="Invalid input! Please check your username and OTP format.")
            return

        if len(ServerState.SESSION_MANAGER.sessions) >= FileState.CONFIG['max_users']:
            self.send_login_page(message="Server busy—too many users. Try again later.")
            return
        
        if submitted_username == ServerState.USERNAME and submitted_otp == ServerState.OTP:
            session_token = credentials.generate_session_token()
            ServerState.SESSION_MANAGER.add_session(session_token, client_ip, current_time + timeout_seconds)

            self.send_response(302)
            self.send_security_headers()
            self.send_header('Location', '/')
            self.send_header('Set-Cookie', f'session_token={session_token}; Path=/; HttpOnly; Max-Age={timeout_seconds}; SameSite=Strict')
            self.end_headers()

            logger.emit_info(f"User[{client_ip}] logged-in")
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

    def send_login_page(self, message=None):
        try:
            html = FileState.LOGIN_HTML
            html = html.replace('{{message}}', message or '')
            self.send_response(200)
            self.send_security_headers()
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        except Exception as e:
            self.send_error(500, f"Error: Something went wrong.")
            logger.emit_error(f"Rendering login page: {str(e)}")

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
            logger.emit_error(f"Directory-listing {path}: {str(e)}")
            return None

        file_list.sort(key=lambda a: (not a.is_dir(), a.name.lower()))
        displaypath = os.path.relpath(path, str(FileState.ROOT_DIR)).strip('/.') or '.'

        try:
            response = HTMLHandler.generate_html(file_list, displaypath)
            encoded = response.encode('utf-8')
            self.send_response(200)
            self.send_security_headers()
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
        except Exception as e:
            self.send_error(500, f"Error generating response.")
            logger.emit_error(f"Generating response: {str(e)}")

    