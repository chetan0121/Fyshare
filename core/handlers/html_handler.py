from html import escape
from urllib.parse import quote
from pathlib import Path
from typing import Union
from http.server import SimpleHTTPRequestHandler as ReqHandler
from .response_handler import ResponseHandler
from ..state import FileState
from ..utils import logger

class HTMLHandler():
    blocked_html_message = (
        "<h1>403 Forbidden</h1>"
        "<p>Blocked due to excessive attempts. Try again later.</p>"
    )

    parent_dir_html = """
        <tr id="parent-dir">
            <td>
                <a href="../">
                    <span class="icon">📁</span>
                    <span> /.. </span>
                </a>
            </td>
            <td class="size">-</td>
            <td></td>
        </tr>"""
    
    FILE_ICONS = {
        ".pdf": "📕",
        ".doc": "📄", ".docx": "📄",
        ".xls": "📊", ".xlsx": "📊",
        ".ppt": "📑", ".pptx": "📑",
        ".txt": "📝", ".csv": "📋",
        ".jpg": "🖼️", ".jpeg": "🖼️", ".png": "🖼️",
        ".gif": "🖼️", ".bmp": "🖼️", ".svg": "🖼️",
        ".mp3": "🎵", ".wav": "🎵", ".ogg": "🎵",
        ".mp4": "🎬", ".avi": "🎬", ".mkv": "🎬",
        ".zip": "📦", ".rar": "📦", ".7z": "📦",
        ".apk": "📱",
        ".exe": "⚙️",
        ".py": "🐍",
        ".html": "🌐", ".js": "📜", ".json": "📜",
    }

    DIR_ICON = "📁"
    DEFAULT_FILE_ICON = "📄"

    @staticmethod
    def generate_html(file_list, displaypath):
        template = FileState.FYSHARE_HTML
        breadcrumbs = HTMLHandler.generate_breadcrumbs(displaypath)

        # Table rows
        rows = []

        # Add parent directory entry when not at root
        if displaypath != '.':
            rows.append(HTMLHandler.parent_dir_html) 
            
        for entry in map(Path, file_list):
            name = entry.name

            # Skip hidden files
            if name.startswith('.'):
                continue

            size = '-'
            btn = ""

            if not entry.is_dir():
                size = HTMLHandler.format_size(entry.stat().st_size)
                btn = HTMLHandler.get_action_button(name)

            icon = HTMLHandler.get_file_icon(entry)
            rows.append(
                HTMLHandler.add_table_row(
                    name, icon, size, btn
                )
            )

        return (
            template.replace("{{breadcrumbs}}", breadcrumbs)
                    .replace("{{table_rows}}", "".join(rows))
        )
    
    @staticmethod
    def generate_breadcrumbs(path: str):
        refined_path = str(path).replace('\\', '/').strip('/. ')
        parts = refined_path.split('/')
        breadcrumbs = ['<a href="/">🏠 Home</a>']
        current_path = ""

        for part in parts:
            if not part or part == '.':
                continue

            current_path = HTMLHandler.join_posix(current_path, part)
            breadcrumbs.append(
                f'<span class="breadcrumb-sep">/</span>'
                f'<a href="/{quote(current_path)}">{escape(part)}</a>'
            )

        return ''.join(breadcrumbs)
    
    @staticmethod
    def get_file_icon(file_name: Union[str, Path]) -> str:
        path = Path(file_name)

        # Directory check
        if path.is_dir():
            return HTMLHandler.DIR_ICON

        # Files with no extension (README, LICENSE, etc.)
        if not path.suffix:
            return HTMLHandler.DEFAULT_FILE_ICON

        return HTMLHandler.FILE_ICONS.get(
            path.suffix.lower(),
            HTMLHandler.DEFAULT_FILE_ICON
        )
    
    @staticmethod
    def add_table_row(file_name, icon, size, action) -> str:
        link = quote(file_name)
        display_name = escape(file_name)

        table_row = f"""
            <tr>
                <td>
                    <a href="{link}">
                        <span class="icon">{icon}</span>
                        <span>{display_name}</span>
                    </a>
                </td>
                <td class="size">{size}</td>
                <td>{action}</td>
            </tr>"""
        
        return table_row

    @staticmethod
    def get_action_button(filename: str) -> str:
        href = quote(filename)
        return (
            f'<a class="download-btn" href="{href}"'
            ' download>⬇️ Download</a>'
        )

    @staticmethod
    def join_posix(a: str, b: str) -> str:
        a = (a or "").rstrip('/')
        b = (b or "").lstrip('/')
        if not a:
            return b
        return f"{a}/{b}"

    @staticmethod
    def format_size(size_bytes: int):
        try:
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if size_bytes < 1024.0:
                    return f"{size_bytes:.1f} {unit}"
                size_bytes /= 1024.0
            return f"{size_bytes:.1f} PB"
        except (TypeError, OSError):
            return "N/A"

    @staticmethod
    def send_login_page(handler: ReqHandler, message=None):
        try:
            html = FileState.LOGIN_HTML
            html = html.replace('{{message}}', message or '')
            ResponseHandler.send_http_response(
                handler,
                content_type='text/html',
                content=html
            )
        except Exception as e:
            handler.send_error(500, f"Error: Something went wrong.")
            logger.emit_error(f"Rendering login page: {str(e)}")    
         
