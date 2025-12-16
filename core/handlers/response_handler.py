import mimetypes
from pathlib import Path
from http.server import SimpleHTTPRequestHandler as req_handler
from ..utils import logger

_MAX_SIZE = 10 * 1024**3  # bytes (10 GiB)

class ResponseHandler:
    """Centralized response management"""

    @staticmethod
    def send_security_headers(self: req_handler, cache_time = 0.0):
        self.send_header("X-Frame-Options", "DENY")
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self';")
        self.send_header('Referrer-Policy', 'no-referrer')
        if cache_time > 0:
            self.send_header('Cache-Control', f'max-age={cache_time}')
        else:
            self.send_header('Cache-Control', 'no-store, must-revalidate')

    @staticmethod
    def send_extra_headers(
        handler: req_handler, 
        status=200, 
        msg="", 
        headers: list[tuple[str, str]] = None,
        cache_time = 0.0
    ) -> None:
        
        if msg:
            handler.send_response(status, msg)
        else:
            handler.send_response(status)    

        ResponseHandler.send_security_headers(handler, cache_time)
        if headers:
            for key, val in headers:
                handler.send_header(key, val)

        handler.end_headers()    
    
    @staticmethod
    def send_http_response(
        handler: req_handler,
        status: int = 200,
        message: str | None = None,
        cache_duration: float = 0.0,
        content_type: str = "text/plain",
        content: str | bytes | None = None,
        file_path: str | None = None,
        chunk_size: int = 32
    ) -> None:
        """
        Send an HTTP response (headers + body) from either an in-memory content
        (str or bytes) or a file on disk.
        
        <h3>Parameters</h3>
        
        - handler: HTTP request handler instance (must support send_response,
          send_header, end_headers and have a writable .wfile).
        - status: HTTP status code to send (default 200).
        - message: Optional reason phrase to include with the status line.
        - cache_duration: Cache-Control max-age value in seconds.
        - content_type: Content-Type header value. If sending a file_path and
          content_type is the default, MIME will be guessed from filename.
        - content: The content to send (Optional if you gives file_path)
        - file_path: Path to file to stream. Used only when content is None.
        - chunk_size: Size of each write to handler.wfile (bytes). Default 32 KiB.
        - encoding: Encoding used when content is str (default utf-8).
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be a positive integer (bytes)")

        # Convert to bytes
        chunk_size = chunk_size * 1024     

        # Check if file exist
        path = Path(file_path) if file_path else None
        is_path = path.is_file() if path else False
        
        if content:
            if is_path:
                logger.emit_warning(
                    "Response handling: got content and file path both",
                    "Using content by default"
                )
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
        
        # Size limit check
        if file_size > _MAX_SIZE:
            logger.emit_warning(
                f"Response handling: Unable to send file",
                "Exceeded the max file size limit"
            )
            return
        
        # Send status code with/without message
        handler.send_response(status, message)

        # Guess the MIME type
        if is_path and content_type == "text/plain":
            guessed = mimetypes.guess_type(path.name)[0]
            if guessed:
                content_type = str(guessed)

        # Headers
        ResponseHandler.send_security_headers(handler, cache_duration)
        handler.send_header("Content-Type", content_type)
        handler.send_header("Content-Length", str(file_size))
        handler.end_headers()    

        # Body
        if is_path:
            with path.open('rb') as f:
                while (chunk := f.read(chunk_size)):
                    handler.wfile.write(chunk)
        else:
            for i in range(0, file_size, chunk_size):
                handler.wfile.write(body[i:i + chunk_size])
