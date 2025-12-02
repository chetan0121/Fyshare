import time
from core.utils import logger

class FileHandler(http.server.SimpleHTTPRequestHandler):
    current_otp = str("")   # Empty string

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT_DIR, **kwargs)

    def get_session_token(self):
        cookies = self.headers.get('Cookie', '')
        for cookie in cookies.split(';'):
            cookie = cookie.strip()
            if cookie.startswith('session_token='):
                return cookie.split('=', 1)[1].strip()
        return None

    def send_security_headers(self, cache_time = 0):
        self.send_header("X-Frame-Options", "DENY")
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self';")
        self.send_header('Referrer-Policy', 'no-referrer')
        if cache_time > 0:
            self.send_header('Cache-Control', f'max-age={cache_time}')
        else:
            self.send_header('Cache-Control', 'no-store, must-revalidate')

    def do_GET(self):
        client_ip = self.client_address[0]
        current_time = time.monotonic()

        if SESSION_MANAGER.is_blocked(client_ip, current_time):
            self.send_response(403, "Access Denied")
            self.send_security_headers()
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b'<h1>403 Forbidden</h1><p>Blocked due to excessive attempts. Try again later.</p>')
            return

        if self.path == '/favicon.ico':
            favicon_path = STATIC_DIR / 'favicon.ico'
            if favicon_path.exists():
                with favicon_path.open('rb') as f:
                    self.send_response(200)
                    self.send_security_headers(cache_time=CONFIG['cache_time_out_s'])
                    self.send_header('Content-Type', 'image/x-icon')
                    self.end_headers()
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "Favicon not found")
                return

        if self.path == '/logout':
            session_token = self.get_session_token()
            if session_token and SESSION_MANAGER.get_session(session_token):
                client_ip = SESSION_MANAGER.get_session(session_token)['ip']
                logger.print_info(f"User[{client_ip}] logged-out.\n")
                logger.log_info(f"User[{client_ip}] logged-out")
                SESSION_MANAGER.remove_session(session_token)

            self.send_response(302)
            self.send_security_headers()
            self.send_header('Location', '/')
            self.send_header('Set-Cookie', 'session_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/')
            self.end_headers()
            return

        if self.path.startswith('/static/'):
            file_path = STATIC_DIR / self.path[len('/static/'):]
            
            if not file_path.exists() or not file_path.is_file():
                self.send_error(404, "File not found")
                printWarning(f"\n- User[{client_ip}] tried to access invalid static file.\n")
                logging.warning(f"User[{client_ip}] tried to access invalid static file")
                return

            try:
                content_type = 'application/octet-stream'
                if file_path.suffix == '.css':
                    content_type = 'text/css'
                elif file_path.suffix == '.js':
                    content_type = 'application/javascript'
                elif file_path.suffix in ('.png', '.jpg', '.jpeg'):
                    content_type = 'image/' + ('png' if file_path.suffix == '.png' else 'jpeg')
                elif file_path.suffix == '.ico':
                    content_type = 'image/x-icon'

                file_size = file_path.stat().st_size
                self.send_response(200)
                self.send_security_headers(cache_time=CONFIG['cache_time_out_s'])
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(file_size))
                self.end_headers()

                with file_path.open('rb') as f:
                    chunk = f.read(65536)   # 64KB chunk
                    while chunk:
                        self.wfile.write(chunk)
                        chunk = f.read(65536)
                return  # Exit after success   
            
            except Exception as e:
                self.send_error(500, f"Internal Server Error")
                printError(f"\nError [Serving file]: {str(e)}\n")
                logging.error(f"Error [Serving file]: {str(e)}")
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
                    self.send_security_headers(cache_time=CONFIG['cache_time_out_s'])
                    self.send_header('Content-Type', 'text/html')
                    self.send_header('Content-Length', str(file_size))
                    self.end_headers()
                    with file_path.open('rb') as f:
                        chunk = f.read(8192)
                        while chunk:
                            self.wfile.write(chunk)
                            chunk = f.read(8192)
                except Exception as e:
                    self.send_error(500, f"Error: Something went wrong.")
                    printError(f"\nError: Serving html file {str(e)}.\n")
                    logging.error(f"Error [Serving html]: {str(e)}")
            else:
                self.send_error(404, "File not found")
        else:
            super().do_GET()

    def do_POST(self):
        client_ip = self.client_address[0]
        current_time = time.monotonic()

        SESSION_MANAGER.clean_expired_attempts()
        if SESSION_MANAGER.is_blocked(client_ip, current_time):
            self.send_response(403)
            self.send_security_headers()
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b'<h1>403 Forbidden</h1><p>Blocked due to excessive attempts. Try again later.</p>')
            return
        
        if SESSION_MANAGER.is_inCool(client_ip, current_time):
            self.send_login_page(message="Too many attempts. Try again later.")
            return
        
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        params = parse_qs(post_data)

        # Safely type conversion
        try:
            submitted_username = str(params.get('username', [''])[0])
            submitted_otp = str(params.get('otp', [''])[0])
            timeout_seconds = float(params.get('timeout', ['0'])[0])
        except ValueError:
            self.send_login_page(message="Invalid input values.")
            return

        if not self.validate_credentials(submitted_username, submitted_otp, timeout_seconds):
            self.send_login_page(message="Invalid input. Please check your username and OTP format.")
            return

        if len(SESSION_MANAGER.sessions) >= CONFIG['max_users']:
            self.send_login_page(message="Server busy—too many users. Try again later.")
            return

        with credentials_lock:
            if submitted_username == USERNAME and submitted_otp == self.current_otp:
                session_token = secrets.token_hex(32)
                SESSION_MANAGER.add_session(session_token, client_ip, current_time + timeout_seconds)
                max_age = int(timeout_seconds)

                self.send_response(302)
                self.send_security_headers()
                self.send_header('Location', self.path)
                self.send_header('Set-Cookie', f'session_token={session_token}; Path=/; HttpOnly; Max-Age={max_age}; SameSite=Strict')
                self.end_headers()

                print(f"\n- User[{client_ip}] logged-in on seconds: {max_age}\n")
                logging.info(f"User[{client_ip}] logged-in")
            else:
                SESSION_MANAGER.update_attempts(client_ip, current_time)
                global GLOBAL_TOTAL_ATTEMPTS
                GLOBAL_TOTAL_ATTEMPTS += 1
                if GLOBAL_TOTAL_ATTEMPTS > CONFIG['max_users']*100:
                    printWarning(f"\n- Total attempts exceeded the limit {CONFIG['max_users']*100} attempts.")
                    print("\nShutting down the server...\n", flush=True)
                    logging.warning(f"Shutting down server after Total {GLOBAL_TOTAL_ATTEMPTS} rapid attempts of login")
                    exit(1)

                if GLOBAL_TOTAL_ATTEMPTS % CONFIG['max_users']*10 == 0:
                    global LAST_UPDATED_CRED
                    LAST_UPDATED_CRED = None
                    generate_credentials("Too many failed attempts on server")

                self.send_login_page(message="Invalid username or OTP.")

    def validate_credentials(self, username, otp, timeout):
        # Validate username: 6–20 alphanumeric characters
        is_valid_username = bool(re.fullmatch(r'[a-zA-Z0-9]{6,20}', username))

        # Validate OTP: exactly 6 digits
        is_valid_otp = bool(re.fullmatch(r'\d{6}', otp))

        # Validate timeout: must be between min and max allowed seconds
        is_valid_timeout = bool((OPTIONS[0][0]*60) <= timeout <= (OPTIONS[-1][0]*60))

        return is_valid_username and is_valid_otp and is_valid_timeout

    def check_authentication(self):
        session_token = self.get_session_token()
        session_data = SESSION_MANAGER.get_session(session_token)

        if not session_token or not session_data:
            return False
        if session_data['ip'] != self.client_address[0]:
            printWarning(f"\n- Session-token stolen from {session_data['ip']}, Request terminated!\n")
            logging.warning(f"Session-token stolen from User[{session_data['ip']}]")
            SESSION_MANAGER.remove_session(session_token)
            return False
        if time.monotonic() >= session_data['expiry']:
            SESSION_MANAGER.remove_session(session_token)
            return False
        
        return True

    def send_login_page(self, message=None):
        try:
            html = LOGIN_TEMPLATE
            options_html = "\n".join(f'<option value="{mins*60}">{label}</option>' for mins, label in OPTIONS)
            html = html.replace('{{options}}', options_html)
            html = html.replace('{{message}}', message or '')
            self.send_response(200)
            self.send_security_headers()
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        except Exception as e:
            self.send_error(500, f"Error: Something went wrong.")
            printError(f"\nError [Rendering login page]: {str(e)}\n", flush=True)
            logging.error(f"Error [Rendering login page]: {str(e)}")

    def translate_path(self, path):
        path = super().translate_path(path)
        real_path = Path(path).resolve()
        if not str(real_path).startswith(str(Path(ROOT_DIR).resolve())):
            self.send_error(403, "Access denied")
            return None
        
        return str(real_path)

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
            printError(f"\nError generating directory list for {path}: {str(e)}\n")
            logging.error(f"Error generating directory list for {path}: {str(e)}")
            return None

        file_list.sort(key=lambda a: (not a.is_dir(), a.name.lower()))
        displaypath = os.path.relpath(path, ROOT_DIR).strip('/.') or '.'

        try:
            response = self.generate_html(file_list, displaypath)
            encoded = response.encode('utf-8')
            self.send_response(200)
            self.send_security_headers()
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
        except Exception as e:
            self.send_error(500, f"Error generating response.")
            printError(f"\nError [generating response]: {str(e)}\n")
            logging.error(f"Error [generating response]: {str(e)}")

    def generate_html(self, file_list, displaypath):
        if not FILE_MANAGER_TEMPLATE:
            self.send_error(500, "Something went wrong.")
            printError("\nError: FILE_MANAGER_TEMPLATE is undefined or empty\n", flush=True)
            exit(1)
        
        template = FILE_MANAGER_TEMPLATE
        breadcrumbs = self.generate_breadcrumbs(displaypath)
        table_rows = ""
        if displaypath != '.':
            table_rows += """
                <tr>
                    <td>
                        <a href="../">
                            <span class="icon">📁</span>
                            <span> /.. </span>
                        </a>
                    </td>
                    <td class="size">-</td>
                    <td></td>
                </tr>
            """
            
        for entry in file_list:
            if entry.name.startswith('.'):
                continue

            try:
                is_dir = entry.is_dir()
                display_name = escape(entry.name)
                link_name = quote(entry.name)
                icon = self.get_file_icon(entry.name, is_dir)
                size = '-' if is_dir else self.format_size(entry.stat().st_size)
                action = self.get_action_button(entry.name, is_dir)
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
                printError(f"\nError processing {entry.name}: {str(e)}\n")
                continue
            
        return template.replace('{{breadcrumbs}}', breadcrumbs).replace('{{table_rows}}', table_rows)

    def join_posix(self, a, b):
        a = (a or "").rstrip('/')
        b = (b or "").lstrip('/')
        if not a:
            return b
        return f"{a}/{b}"

    def generate_breadcrumbs(self, path):
        path = path.replace('\\', '/').strip('/. ')
        parts = path.split('/')
        breadcrumbs = ['<a href="/">🏠 Home</a>']
        current_path = ""

        for part in parts:
            if not part or part == '.':
                continue

            current_path = self.join_posix(current_path, part)
            breadcrumbs.append(
                f'<span class="breadcrumb-sep">/</span>'
                f'<a href="/{quote(current_path)}">{escape(part)}</a>'
            )
        return ''.join(breadcrumbs)

    def get_file_icon(self, filename, is_dir):
        if is_dir:
            return "📁"
        
        ext = os.path.splitext(filename)[1].lower()
        icons = {
            '.pdf': '📕', '.doc': '📄', '.docx': '📄', '.xls': '📊', '.xlsx': '📊', '.ppt': '📑',
            '.pptx': '📑', '.txt': '📝', '.csv': '📋', '.jpg': '🖼️', '.jpeg': '🖼️', '.png': '🖼️',
            '.gif': '🖼️', '.bmp': '🖼️', '.svg': '🖼️', '.mp3': '🎵', '.wav': '🎵', '.ogg': '🎵',
            '.mp4': '🎬', '.avi': '🎬', '.mkv': '🎬', '.zip': '📦', '.rar': '📦', '.7z': '📦',
            '.apk': '📱', '.exe': '⚙️', '.py': '🐍', '.html': '🌐', '.js': '📜', '.json': '📜'
        }
        return icons.get(ext, '📄')

    def get_action_button(self, filename, is_dir):
        if is_dir:
            return ""
        return f'<a class="download-btn" href="{quote(filename)}" download>⬇️ Download</a>'

    def format_size(self, size_bytes):
        try:
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if size_bytes < 1024.0:
                    return f"{size_bytes:.1f} {unit}"
                size_bytes /= 1024.0
            return f"{size_bytes:.1f} PB"
        except TypeError:
            return "N/A"