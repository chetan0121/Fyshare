import time
import os
from pathlib import Path
import urllib.parse
from http import HTTPStatus

from .html_handler import HTMLHandler
from .response_handler import ResponseHandler
from .security_mixin import SecurityMixin
from .. import credentials, server
from ..utils import logger
from ..state import FileState, ServerState


class FileHandler(SecurityMixin):
    """HTTP request handler for file serving with authentication and security."""

    def __init__(self, *args, **kwargs):
        """Initialize FileHandler with root directory and session manager."""
        self.config = FileState.CONFIG
        self.session_manager = ServerState.session_manager

        super().__init__(*args, directory=str(FileState.ROOT_DIR), **kwargs)

    def copyfile(self, source, outputfile, chunk_kb: float = 64.0) -> None:
        """Copy file data in chunks while handling connection errors gracefully.
        
        Args:
            source: Open file object to read from.
            outputfile: Open file-like object to write to.
            chunk_kb: Chunk size in kilobytes (default 64 KB).
            
        Raises:
            ValueError: If chunk_kb is not positive.
        """
        if chunk_kb <= 0:
            raise ValueError("chunk_size must be a positive integer")
        
        # Convert to KB
        chunk_size = int(chunk_kb * 1024)       
        try:
            while (data := source.read(chunk_size)):
                outputfile.write(data)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def do_GET(self) -> None:
        """Handle GET requests with authentication, rate limiting, and file serving."""
        client_ip = self.client_address[0]
        current_time = time.monotonic()

        if self.session_manager.is_blocked(client_ip, current_time):
            ResponseHandler.send_blocked_response(
                self, HTMLHandler.blocked_html_message
            )
            return

        if self.path == '/favicon.ico':
            favicon_path = FileState.favicon_path
            if favicon_path.exists():
                ResponseHandler.send_http_response(
                    self, file_path=favicon_path
                )
            else:
                self.send_error(404, "Favicon not found")
            return

        if self.path == '/logout':
            session_token = self.get_session_token()
            session = self.session_manager.get_session(session_token)
            if session_token and session:
                curr_ip = session['ip']
                logger.emit_info("User logged-out", f"IP: {curr_ip}")
                self.session_manager.remove_session(session_token)

            ResponseHandler.redirect_home(
                self,
                'session_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/'
            )
            return

        if self.path.startswith('/static/'):
            static_dir = FileState.STATIC_DIR
            rel_dir = self.path[len('/static/'):]
            file_path = self.translate_path(rel_dir, static_dir)
            
            if file_path == static_dir:
                self.send_error(403, "Permission denied")
                return
            
            if not file_path.exists() or not file_path.is_file():
                self.send_error(404, "File not found")
                return

            try:
                ResponseHandler.send_http_response(
                    self, file_path=file_path, chunk_size=64
                )
            except Exception as e:
                self.send_error(500, "Internal Server Error")
                logger.emit_error(
                    f"During static file serve: {str(e)}",
                    f"IP: {client_ip}",
                    f"File: {file_path}"
                )
                
            return

        if not self.check_authentication():
            ResponseHandler.send_login_page(self)
            return

        if self.path.endswith('.html'):
            file_path = self.translate_path(self.path)
            if file_path.exists() and file_path.is_file():
                try:
                    ResponseHandler.send_http_response(
                        self, file_path=file_path
                    )
                except Exception as e:
                    self.send_error(500, f"Error: Something went wrong.")
                    logger.emit_error(
                        f"Serving html file: {str(e)}",
                        f"IP: {client_ip}",
                        f"File: {file_path}"
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

    def do_POST(self) -> None:
        """Handle POST requests for login with OTP validation and session management."""
        client_ip = self.client_address[0]
        current_time = time.monotonic()

        if self.session_manager.is_blocked(client_ip, current_time):
            ResponseHandler.send_blocked_response(
                self, 
                HTMLHandler.blocked_html_message
            )
            return
        
        if self.session_manager.is_inCool(client_ip, current_time):
            ResponseHandler.send_login_page(
                self, message="Too many attempts. Try again later."
            )
            return
        
        try:
            # Validate Content-Length is reasonable (max 10KB for login form)
            max_body_size = 10 * 1024
            
            content_length = int(self.headers.get('Content-Length', 0))
            
            if content_length < 0 or content_length > max_body_size:
                logger.emit_error(f"Invalid Content-Length: {content_length}", f"IP: {client_ip}")
                self.send_error(413, "Payload too large")
                return
            
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = urllib.parse.parse_qs(post_data)
        except Exception as e:
            logger.emit_error(f"Decoding POST data: {str(e)}", f"IP: {client_ip}")
            self.send_error(400, "Error decoding your request")    
            return

        try:
            submitted_otp = str(params.get('otp', [''])[0])
            timeout_seconds = int(params.get('timeout', ['0'])[0])
        except ValueError:
            ResponseHandler.send_login_page(self, message="Invalid input values.")
            return

        if not self.validate_credentials(
            submitted_otp,
            timeout_seconds
        ):
            ResponseHandler.send_login_page(
                self, 
                message="Invalid input! Please check your otp format."
            )
            return

        if submitted_otp == ServerState.otp:
            session_token = credentials.generate_session_token()
            was_added = self.session_manager.try_add_session(
                session_token,
                client_ip,
                current_time + timeout_seconds,
            )

            if not was_added:
                ResponseHandler.send_login_page(
                    self,
                    message="Server busy—too many users. Try again later."
                )
                return

            cookie = (
                f'session_token={session_token}; '
                f'Path=/; HttpOnly; Max-Age={timeout_seconds}; SameSite=Strict'
            )
            ResponseHandler.redirect_home(self, cookie)
            
            logger.emit_info("User logged-in", f"IP: {client_ip}")

        else:
            security_shutdown_threshold = self.config['max_users']*100
            credential_rotation_threshold = self.config['max_users']*10
            self.session_manager.update_attempts(client_ip, current_time)

            logger.emit_info(
                f"User tried to login with invalid otp \'{submitted_otp}\'",
                f"IP: {client_ip}"
            )

            with ServerState.credentials_lock:
                ServerState.global_attempts += 1
                attempts = ServerState.global_attempts

            if attempts > security_shutdown_threshold:
                server.shutdown_server(
                    "Security shutdown triggered "
                    f"after {attempts} rapid login attempts"
                )
                return

            if attempts % credential_rotation_threshold == 0:
                credentials.generate_credentials("Too many failed attempts on server")

            ResponseHandler.send_login_page(self, message="Invalid otp.")

    def list_dir(self, path: Path) -> None:
        """Generate and send directory listing as HTML table.
        
        Args:
            path: Filesystem path to list.
            
        Returns:
            None if there was an error, otherwise void function.
        """
        try:
            with os.scandir(str(path)) as entries:
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
        display_path = str(path.relative_to(FileState.ROOT_DIR))

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
        """Handle HEAD requests and send file/directory with proper headers.
        
        Returns:
            Open file object if file should be sent, None if handled as directory redirect.
        """
        path = self.translate_path(self.path)

        if path.is_dir():
            if not self.path.endswith('/'):
                self.send_response(HTTPStatus.MOVED_PERMANENTLY)
                self.send_header("Location", self.path + "/")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return None
            
            return self.list_dir(path)
            
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None
        
        f = None
        try:
            f = open(path, 'rb')
            fs = os.fstat(f.fileno())
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            if f: f.close()
            return None

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-type", self.guess_type(path))
        self.send_header("Content-Length", str(fs.st_size))
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.end_headers()
        return f
