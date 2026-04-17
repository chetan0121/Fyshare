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
        """Initialize config/session references and base handler directory."""
        self.config = FileState.CONFIG
        self.session_manager = ServerState.session_manager

        super().__init__(*args, directory=str(FileState.ROOT_DIR), **kwargs)

    def stream_file(self, source_file, destination_file, chunk_size_kb: float = 64.0) -> None:
        """Stream a file in chunks and log completion or early disconnect.

        Args:
            source_file: Readable binary file object.
            destination_file: Writable binary stream (usually `self.wfile`).
            chunk_size_kb: Chunk size in KB; must be greater than 0.

        Raises:
            ValueError: If `chunk_size_kb` is not positive.
        """
        if chunk_size_kb <= 0:
            raise ValueError("chunk_size_kb must be a positive number")
        
        chunk_size = int(chunk_size_kb * 1024)   # Convert to bytes
        bytes_sent = 0
        client_ip = self.client_address[0]
        
        try:
            while (data := source_file.read(chunk_size)):
                destination_file.write(data)
                bytes_sent += len(data)
                
            logger.emit_info(
                "File transfer completed",
                f"IP: {client_ip}",
                f"Path: \"{self.path}\"",
                f"Bytes sent: {bytes_sent}"
            )
        except (BrokenPipeError, ConnectionError):
            logger.emit_info(
                "File transfer canceled",
                f"IP: {client_ip}",
                f"Path: \"{self.path}\"",
                f"Bytes sent: {bytes_sent}"
            )

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
                self.send_error(HTTPStatus.NOT_FOUND, "Favicon not found")
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
                self.send_error(HTTPStatus.FORBIDDEN)
                return
            
            if not file_path.exists() or not file_path.is_file():
                self.send_error(HTTPStatus.NOT_FOUND)
                return

            try:
                ResponseHandler.send_http_response(
                    self, file_path=file_path, chunk_size=64
                )
            except Exception as e:
                self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR)
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
                    self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR)
                    logger.emit_error(
                        f"Serving html file: {str(e)}",
                        f"IP: {client_ip}",
                        f"File: {file_path}"
                    )
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
            return    
        
        # Handle directory and file serving
        self.send_head()

    def do_POST(self) -> None:
        """Handle OTP login submission and session creation."""
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
            # Validate Content-Length is reasonable or not (max 10KB for login form)
            max_body_size = 10 * 1024
            
            content_length = int(self.headers.get('Content-Length', 0))
            
            if content_length < 0 or content_length > max_body_size:
                logger.emit_error(f"Invalid Content-Length: {content_length}", f"IP: {client_ip}")
                self.send_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Payload too large")
                return
            
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = urllib.parse.parse_qs(post_data)
        except Exception as e:
            logger.emit_error(f"Decoding POST data: {str(e)}", f"IP: {client_ip}")
            self.send_error(HTTPStatus.BAD_REQUEST, "Error decoding your request")    
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
                    message="Server busy, too many users. Try again later."
                )
                return

            ResponseHandler.redirect_home(
                self, 
                f'session_token={session_token}; '
                f'Path=/; HttpOnly; Max-Age={timeout_seconds}; SameSite=Strict'
            )
            
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
            path: Directory path to enumerate.
        """
        try:
            with os.scandir(str(path)) as entries:
                file_list = list(entries)
        except PermissionError:
            self.send_error(HTTPStatus.FORBIDDEN)
            return None
        except FileNotFoundError:
            self.send_error(HTTPStatus.NOT_FOUND, "Directory not found.")
            return None
        except Exception as e:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR)
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
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR)
            logger.emit_error(f"Generating response: {str(e)}")   

    def send_head(self):
        """Serve the resolved path as a directory listing or streamed file.

        Handles redirecting directory URLs without a trailing slash and sends
        standard headers for files before streaming content.
        """
        path = self.translate_path(self.path)

        if path.is_dir():
            if not self.path.endswith('/'):
                ResponseHandler.redirect_to(
                    self, HTTPStatus.MOVED_PERMANENTLY,
                    self.path + "/"
                )
                return None

            return self.list_dir(path)
            
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return None
        
        f = None
        try:
            f = open(path, 'rb')
            fs = os.fstat(f.fileno())
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND)
            if f: f.close()
            return None

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Length", str(fs.st_size))
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.end_headers()
        
        # Stream file content to client in chunks
        try:
            self.stream_file(f, self.wfile)
        finally:
            f.close()
