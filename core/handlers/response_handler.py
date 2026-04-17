import mimetypes
from pathlib import Path
from typing import Optional, Union, Sequence
from http import HTTPStatus

from ..handlers.html_handler import HTMLHandler
from ..handlers.security_mixin import SecurityMixin
from ..utils import logger

class ResponseHandler:
    """Utilities for sending HTTP responses, redirects, and common pages.

    Assumes the given `handler` implements the BaseHTTPRequestHandler
    interface and exposes a writable `wfile`.
    """
    security_headers = [
        ("X-Frame-Options", "DENY"),
        ("X-Content-Type-Options", "nosniff"),
        ("Content-Security-Policy", "default-src 'self';"),
        ("Referrer-Policy", "no-referrer"),
    ]

    @staticmethod
    def send_extra_headers(
        handler: SecurityMixin,
        status: int = HTTPStatus.OK, 
        msg: Optional[str] = None,
        headers: Optional[Sequence[tuple[str, str]]] = None,
        send_security_headers = True
    ) -> None:
        """Send status and headers. Optionally include security headers.

        `headers` should be an iterable of (name, value) pairs.
        """
        handler.send_response(status, msg)

        # Send security headers
        if send_security_headers:
            for key, val in ResponseHandler.security_headers:
                handler.send_header(key, val)

        # Send extra headers from param
        if headers:
            for key, val in headers:
                handler.send_header(key, val)

        handler.end_headers()
        
    @staticmethod
    def redirect_to(
        handler: SecurityMixin, 
        status: int = HTTPStatus.FOUND, 
        location: str = '/', 
        cookie: Optional[str] = None
    ) -> None:
        """Send a redirect to `location`. Optionally include a cookie header.

        Uses minimal headers and disables caching for the redirect.
        """

        headers = [
            ("Location", location),
            ("Content-Length", "0"),
            ("Cache-Control", "no-cache, no-store, must-revalidate"),
            ("Pragma", "no-cache"),
            ("Expires", "0"),
        ]
        
        if cookie:
            headers.append(("Set-Cookie", cookie))
            
        ResponseHandler.send_extra_headers(
            handler,
            status=status,
            headers=headers,
            send_security_headers=False
        )
        
    @staticmethod
    def redirect_home(handler: SecurityMixin, cookie: Optional[str] = None) -> None:
        """Redirect to root ('/'). Optionally set a cookie."""
        ResponseHandler.redirect_to(handler, cookie=cookie)
        
    @staticmethod
    def send_login_page(handler: SecurityMixin, message: Optional[str] = None) -> None:
        """Render and send the login page HTML (text/html)."""
        try:
            html = HTMLHandler.get_login_html(message)
            ResponseHandler.send_http_response(
                handler,
                content_type='text/html',
                content=html
            )
        except Exception as e:
            handler.send_error(HTTPStatus.INTERNAL_SERVER_ERROR)
            logger.emit_error(f"Rendering login page: {str(e)}")

    @staticmethod
    def send_blocked_response(handler: SecurityMixin, content: str) -> None:
        """Send a 403 Forbidden response with the provided HTML body."""
        ResponseHandler.send_http_response(
            handler,
            HTTPStatus.FORBIDDEN, "Access Denied",
            content_type='text/html; charset=utf-8',
            content=content
        )
        
    @staticmethod
    def send_http_response(
        handler: SecurityMixin,
        status: int = HTTPStatus.OK,
        message: Optional[str] = None,
        content_type: str = "text/plain",
        content: Optional[Union[str, bytes]] = None,
        file_path: Optional[Union[str, Path]] = None,
        chunk_size: float = 32.0,
        extra_headers: Optional[Sequence[tuple[str, str]]] = None,
    ) -> None:
        """Send headers and body from memory or by streaming a file.

        - If `content` is provided (str/bytes) it is sent in chunks.
        - Otherwise `file_path` is streamed from disk.

        `chunk_size` is in kilobytes (KB) and must be > 0.
        
        - raise ValueError if chunk_size <= 0 OR  no content is provided
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
        response_headers = [
            ("Content-Type", content_type),
            ("Content-Length", str(file_size)),
        ]
        
        # Add any extra headers provided
        if extra_headers:
            response_headers.extend(extra_headers)
        
        try:
            # Send headers
            ResponseHandler.send_extra_headers(
                handler,
                status, message,
                response_headers
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
