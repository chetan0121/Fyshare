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
        """Send response status and headers, then terminate header section.

        Args:
            handler: Active request handler.
            status: HTTP status code.
            msg: Optional custom reason phrase.
            headers: Extra `(name, value)` header pairs.
            send_security_headers: Whether to include default security headers.
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

        Uses minimal headers and disables caching for the redirect. Security
        headers are intentionally omitted here so the redirect stays minimal.
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
        chunk_size: float = 64.0,
        extra_headers: Optional[Sequence[tuple[str, str]]] = None,
        logging: bool = False
    ) -> None:
        """Send an HTTP response from in-memory content or a file path.

        Args:
            handler: Active request handler.
            status: HTTP status code.
            message: Optional custom reason phrase.
            content_type: MIME type for `Content-Type` header.
            content: Response body bytes/string. Takes precedence over `file_path`.
            file_path: File to stream when `content` is not provided.
            chunk_size: Transfer chunk size in KiB; must be greater than 0.
            extra_headers: Additional headers to append.
            logging: Log completed/canceled transfers when True.

        Raises:
            ValueError: If `chunk_size <= 0` or neither content nor file data exists.
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be a positive value")

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

        # Variables
        bytes_sent = 0
        request_path = str(path) if is_path else str(getattr(handler, "path", ""))
        client_ip = handler.client_address[0]
        
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
                        bytes_sent += len(data)
            else:
                for i in range(0, file_size, chunk):
                    part = body[i:i + chunk]
                    handler.wfile.write(part)
                    bytes_sent += len(part)

            if logging:
                logger.emit_info(
                    "File transfer completed",
                    f"IP: {client_ip}",
                    f"Path: \"{request_path}\"",
                    f"Bytes sent: {bytes_sent}"
                )
        except (BrokenPipeError, ConnectionError) as e:
            handler.close_connection = True
            if logging:
                logger.emit_info(
                    "File transfer canceled",
                    f"Reason: {type(e).__name__}",
                    f"IP: {client_ip}",
                    f"Path: \"{request_path}\"",
                    f"Bytes sent: {bytes_sent}"
                )
