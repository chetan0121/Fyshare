import os
from html import escape
from urllib.parse import quote
from pathlib import Path
from http.server import SimpleHTTPRequestHandler as req_handler
from .response_handler import ResponseHandler
from ..state import FileState
from ..utils import logger

class HTMLHandler():
    blocked_html_message = '<h1>403 Forbidden</h1><p>Blocked due to excessive attempts. Try again later.</p>'
    parent_dir_html = """
        <tr>
            <td>
                <a href="../">
                    <span class="icon">📁</span>
                    <span> /.. </span>
                </a>
            </td>
            <td class="size">-</td>
            <td></td>
        </tr>"""

    @staticmethod
    def generate_html(file_list, displaypath):
        template = FileState.FYSHARE_HTML
        breadcrumbs = HTMLHandler.generate_breadcrumbs(displaypath)
        table_rows = ""
        if displaypath != '.':
            table_rows += HTMLHandler.parent_dir_html
            
        for entry in file_list:
            entry = Path(entry)
            if entry.name.startswith('.'):
                continue

            try:
                is_dir = entry.is_dir()
                display_name = escape(entry.name)
                link_name = quote(entry.name)
                icon = HTMLHandler.get_file_icon(entry.name, is_dir)
                size = '-' if is_dir else HTMLHandler.format_size(entry.stat().st_size)
                action = HTMLHandler.get_action_button(entry.name, is_dir)
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
                logger.emit_error(f"Processing {entry.name}: {str(e)}")
                continue
    
        return template.replace('{{breadcrumbs}}', breadcrumbs).replace('{{table_rows}}', table_rows)
    
    @staticmethod
    def generate_breadcrumbs(path):
        path = str(path).replace('\\', '/').strip('/. ')
        parts = path.split('/')
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
    def get_file_icon(filename, is_dir):
        if is_dir:
            return "📁"
        
        ext = str(os.path.splitext(filename)[1]).lower()
        icons = {
            '.pdf': '📕', '.doc': '📄', '.docx': '📄', '.xls': '📊', '.xlsx': '📊', '.ppt': '📑',
            '.pptx': '📑', '.txt': '📝', '.csv': '📋', '.jpg': '🖼️', '.jpeg': '🖼️', '.png': '🖼️',
            '.gif': '🖼️', '.bmp': '🖼️', '.svg': '🖼️', '.mp3': '🎵', '.wav': '🎵', '.ogg': '🎵',
            '.mp4': '🎬', '.avi': '🎬', '.mkv': '🎬', '.zip': '📦', '.rar': '📦', '.7z': '📦',
            '.apk': '📱', '.exe': '⚙️', '.py': '🐍', '.html': '🌐', '.js': '📜', '.json': '📜'
        }
        return icons.get(ext, '📄')

    @staticmethod
    def get_action_button(filename, is_dir):
        if is_dir:
            return ""
        return f'<a class="download-btn" href="{quote(filename)}" download>⬇️ Download</a>'

    @staticmethod
    def join_posix(a: str, b: str):
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
        except TypeError:
            return "N/A"

    @staticmethod
    def send_login_page(handler: req_handler, message=None):
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
         
