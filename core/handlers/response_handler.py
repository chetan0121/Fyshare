import mimetypes
from pathlib import Path
from typing import Optional, Union, Sequence

from ..handlers.html_handler import HTMLHandler
from ..handlers.security_mixin import SecurityMixin
from ..utils import logger

class ResponseHandler:
    """Centralized response management"""
    security_headers = [
        ("X-Frame-Options", "DENY"),
        ("X-Content-Type-Options", "nosniff"),
        ("Content-Security-Policy", "default-src 'self';"),
        ("Referrer-Policy", "no-referrer"),
    ]

    @staticmethod
    def send_extra_headers(
        handler: SecurityMixin,
        status: int = 200, 
        msg: Optional[str] = None,
        headers: Optional[Sequence[tuple[str, str]]] = None,
    ) -> None:
        """Send HTTP response headers with security headers included.
        
        Args:
            handler: HTTP request handler.
            status: HTTP status code (default 200).
            msg: Optional reason phrase for status line.
            headers: Optional sequence of (key, value) tuples for additional headers.
        """
        handler.send_response(status, msg)

        # Send security headers
        for key, val in ResponseHandler.security_headers:
            handler.send_header(key, val)

        # Send extra headers from param
        if headers:
            for key, val in headers:
                handler.send_header(key, val)

        handler.end_headers()
        
    @staticmethod
    def redirect_home(handler: SecurityMixin, cookie: Optional[str] = None) -> None:
        """
        Redirect to '/' with optional Set-Cookie header.

        Args:
            handler: HTTP request handler
            cookie: full cookie string (e.g. "session_token=...; Path=/")
        """
        headers = [("Location", "/")]

        if cookie:
            headers.append(("Set-Cookie", cookie))

        ResponseHandler.send_extra_headers(
            handler,
            status=302,
            headers=headers
        )
        
    @staticmethod
    def send_login_page(handler: SecurityMixin, message: Optional[str] = None) -> None:
        """Send login page HTML to client.
        
        Args:
            handler: HTTP request handler.
            message: Optional message to display on login page.
        """
        try:
            html = HTMLHandler.get_login_html(message)
            ResponseHandler.send_http_response(
                handler,
                content_type='text/html',
                content=html
            )
        except Exception as e:
            handler.send_error(500, f"Error: Something went wrong.")
            logger.emit_error(f"Rendering login page: {str(e)}")

    @staticmethod
    def send_blocked_response(handler: SecurityMixin, content: str) -> None:
        """Send 403 Forbidden response with provided HTML content.
        
        Args:
            handler: HTTP request handler.
            content: HTML content to send as response body.
        """
        ResponseHandler.send_http_response(
            handler,
            403, "Access Denied",
            content_type='text/html; charset=utf-8',
            content=content
        )
        
    @staticmethod
    def send_http_response(
        handler: SecurityMixin,
        status: int = 200,
        message: Optional[str] = None,
        content_type: str = "text/plain",
        content: Optional[Union[str, bytes]] = None,
        file_path: Optional[Union[str, Path]] = None,
        chunk_size: float = 32.0
    ) -> None:
        """
        Send an HTTP response (headers + body) from either an in-memory content
        (str or bytes) or a file on disk.
        
        ### Parameters
        
        - handler: HTTP request handler instance (must support send_response,
          send_header, end_headers and have a writable .wfile).
        - status: HTTP status code to send (default 200).
        - message: Optional reason phrase to include with the status line.
        - content_type: Content-Type header value. If sending a file_path and
          content_type is the default, MIME will be guessed from filename.
        - content: The content to send (Optional if you gives file_path)
        - file_path: Path to file to stream. Used only when content is None.
        - chunk_size: Size of each write to handler.wfile (bytes). Default 32 KiB.
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be a positive integer")

        # Convert to bytes
        chunk = int(chunk_size * 1024)  

        # Check if file exist
        path = Path(file_path) if file_path else None
        is_path = path.is_file() if path else False
        
        # Handle Content and File Path
        if content is not None:
            # got both content and file path
            if is_path:
                #  content by default
                is_path = False

            if isinstance(content, str):
                body = content.encode("utf-8")
            else:
                body = bytes(content)

            file_size = len(body)

        elif is_path:
            file_size = path.stat().st_size

        else:
            raise ValueError("Got no response to send")
        
        # Guess the MIME type
        if is_path and content_type == "text/plain":
            guessed = mimetypes.guess_type(path.name)[0]
            if guessed:
                content_type = str(guessed)

        # Send headers
        extra_headers = [
            ("Content-Type", content_type),
            ("Content-Length", str(file_size)),
        ]
        
        try:
            # Send headers
            ResponseHandler.send_extra_headers(
                handler,
                status, message,
                extra_headers
            )
            
            # Send Body
            if is_path:
                with path.open('rb') as f:
                    while (data := f.read(chunk)):
                        handler.wfile.write(data)
            else:
                for i in range(0, file_size, chunk):
                    handler.wfile.write(body[i:i + chunk])
        except (BrokenPipeError, ConnectionError):
            logger.emit_info("Client disconnected during http-response")
