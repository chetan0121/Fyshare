import time
import os
from pathlib import Path
import urllib.parse
from http import HTTPStatus
from http import server as http_server

from .html_handler import HTMLHandler
from ..utils import logger
from .. import credentials, server
from .response_handler import ResponseHandler
from .security_mixin import SecurityMixin
from ..state import FileState, ServerState

class FileHandler(SecurityMixin, http_server.SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        self.config = FileState.CONFIG
        self.root_dir = str(FileState.ROOT_DIR)
        super().__init__(*args, directory=str(FileState.ROOT_DIR), **kwargs)

    def copyfile(self, source, destination, chunk_kb = 64.0):
        """
        copies data from source to destination
        chunk_kb: By default 64 in KB
        """
        if chunk_kb <= 0:
            raise ValueError("chunk_size must be a positive integer")
        
        # Convert to KB
        chunk_size = int(chunk_kb * 1024)       
        try:
            while (data := source.read(chunk_size)):
                destination.write(data)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def do_GET(self):
        session_manager = ServerState.session_manager
        client_ip = self.client_address[0]
        current_time = time.monotonic()

        if session_manager.is_blocked(client_ip, current_time):
            ResponseHandler.send_blocked_response(
                self, HTMLHandler.blocked_html_message
            )
            return

        if self.path == '/favicon.ico':
            favicon_path = FileState.STATIC_DIR / 'favicon.ico'
            if favicon_path.exists():
                ResponseHandler.send_http_response(
                    self, file_path=favicon_path
                )
            else:
                self.send_error(404, "Favicon not found")
            return

        if self.path == '/logout':
            session_token = self.get_session_token()
            session = session_manager.get_session(session_token)
            if session_token and session:
                curr_ip = session['ip']
                logger.emit_info("User logged-out", f"IP: {curr_ip}")
                session_manager.remove_session(session_token)

            # Headers
            home_page = ('Location', '/')
            set_cookie = (
                'Set-Cookie',
                'session_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/'
            )

            ResponseHandler.send_extra_headers(
                self,
                status=302,
                headers=[home_page, set_cookie]
            )
            return

        if self.path.startswith('/static/'):
            file_path = FileState.STATIC_DIR / self.path[len('/static/'):]
            
            if not file_path.exists() or not file_path.is_file():
                self.send_error(404, "File not found")
                logger.emit_warning(
                     "User tried to access invalid static file.",
                    f"IP: {client_ip}",
                    f"Path: {file_path}"
                )
                return

            try:
                ResponseHandler.send_http_response(
                    self, file_path=file_path, chunk_size=64
                )
                return
            except Exception as e:
                self.send_error(500, f"Internal Server Error")
                logger.emit_error(
                    f"During static file serve: {str(e)}",
                    f"File: {file_path}"
                )
                return

        if not self.check_authentication():
            HTMLHandler.send_login_page(self)
            return

        if self.path.endswith('.html'):
            file_path = Path(self.translate_path(self.path))
            if file_path.exists() and file_path.is_file():
                try:
                    ResponseHandler.send_http_response(
                        self, file_path=file_path
                    )
                except Exception as e:
                    self.send_error(500, f"Error: Something went wrong.")
                    logger.emit_error(
                        f"Serving html file: {str(e)}",
                        f"HTML FILE: {file_path}"
                    )
            else:
                self.send_error(404, "File not found")
            return    
        
        # handle directory/file serving
        file_obj = self.send_head()
        if file_obj:
            try:
                self.copyfile(file_obj, self.wfile)
            finally:
                file_obj.close()

    def do_POST(self):
        client_ip = self.client_address[0]
        current_time = time.monotonic()
        session_manager = ServerState.session_manager

        if session_manager.is_blocked(client_ip, current_time):
            ResponseHandler.send_blocked_response(
                self, 
                HTMLHandler.blocked_html_message
            )
            return
        
        if session_manager.is_inCool(client_ip, current_time):
            HTMLHandler.send_login_page(
                self, message="Too many attempts. Try again later." 
            )
            return
        
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = urllib.parse.parse_qs(post_data)
        except Exception as e:
            logger.emit_error(f"Decoding POST data: {str(e)}", f"IP: {client_ip}")
            self.send_error(400, "Error decoding your request")    
            return

        try:
            submitted_username = str(params.get('username', [''])[0])
            submitted_otp = str(params.get('otp', [''])[0])
            timeout_seconds = int(params.get('timeout', ['0'])[0])
        except ValueError:
            HTMLHandler.send_login_page(self, message="Invalid input values.")
            return

        if not self.validate_credentials(
            submitted_username,
            submitted_otp, 
            timeout_seconds
        ):
            HTMLHandler.send_login_page(
                self, 
                message="Invalid input! Please check your username and otp format."
            )
            return

        if len(session_manager.sessions) >= self.config['max_users']:
            HTMLHandler.send_login_page(
                self, 
                message="Server busy—too many users. Try again later."
            )
            return
        
        if submitted_username == ServerState.username \
            and submitted_otp == ServerState.otp:

            session_token = credentials.generate_session_token()
            session_manager.add_session(
                session_token, 
                client_ip, 
                current_time + timeout_seconds
            )

            home_page = ('Location', '/')
            set_cookie = (
                'Set-Cookie', 
                f'session_token={session_token}; '
                f'Path=/; HttpOnly; Max-Age={timeout_seconds}; SameSite=Strict'
            )
            ResponseHandler.send_extra_headers(
                self,
                status=302,
                headers=[home_page, set_cookie]
            )
            logger.emit_info("User logged-in", f"IP: {client_ip}")

        else:
            security_shutdown_threshold = self.config['max_users']*100
            credential_rotation_threshold = self.config['max_users']*10
            session_manager.update_attempts(client_ip, current_time)

            with ServerState.credentials_lock:
                ServerState.global_attempts += 1
                attempts = ServerState.global_attempts

            if attempts > security_shutdown_threshold:
                server.shutdown_server(
                    "Security shutdown triggered "
                    f"after {attempts} rapid login attempts"
                )

            if attempts % credential_rotation_threshold == 0:
                credentials.generate_credentials("Too many failed attempts on server")

            HTMLHandler.send_login_page(self, message="Invalid username or otp.")

    def list_directory(self, path: str):
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
        display_path = os.path.relpath(path, self.root_dir or '.')

        try:
            response = HTMLHandler.generate_html(file_list, display_path)
            ResponseHandler.send_http_response(
                self,
                content_type='text/html; charset=utf-8',
                content=response
            )
        except Exception as e:
            self.send_error(500, f"Error generating response.")
            logger.emit_error(f"Generating response: {str(e)}")   

    def send_head(self):
        path = self.translate_path(self.path)

        if os.path.isdir(path):
            if not self.path.endswith(('/', '%2f', '%2F')):
                self.send_response(HTTPStatus.MOVED_PERMANENTLY)
                self.send_header("Location", self.path + "/")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return None
            
            return self.list_directory(path)
            
        if path.endswith("/"):
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None
        
        try:
            f = open(path, 'rb')
            fs = os.fstat(f.fileno())
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            f.close()
            return None

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-type", self.guess_type(path))
        self.send_header("Content-Length", str(fs.st_size))
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.end_headers()
        return f
