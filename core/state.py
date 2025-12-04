import threading
import secrets
from pathlib import Path
from .utils import helper

class StateError(Exception): pass

class ServerState:
    # Server
    Server = None
    is_running = False

    # Credentials
    OTP: str
    USERNAME: str
    SESSION_MANAGER = None
    credentials_lock = threading.Lock()

    # States of server
    PORT: str
    LOCAL_IP: str
    GLOBAL_TOTAL_ATTEMPTS: int = 0
    LAST_UPDATED_CRED: float | None = None
    INACTIVITY_START: float | None = None

    # Session timeout options (CONSTANT)
    OPTIONS = [
        (5, "5 minutes"),
        (15, "15 minutes"),
        (30, "30 minutes"),
        (60, "1 hour"),
        (120, "2 hours")
    ]

    def init_server_state():
        """
        Run this before starting the server (server.init_server())
        """
        ServerState.OPTIONS.sort(key=lambda x: x[0])
        ServerState.PORT = secrets.choice(range(1500, 9500))
        ServerState.LOCAL_IP = helper.get_local_ip()


class FileState:
    # === Global ===
    CONFIG: dict 
    ROOT_DIR: Path
    STATIC_DIR: Path

    LOGIN_HTML: str
    FYSHARE_HTML: str

    config_path: str | Path
    raw_config: dict

    # Must set CONFIG before using this
    def set_root_path():
        saved_path = helper.refine_path(FileState.CONFIG["root_directory"])

        # === Path selection by User ===
        print("\nSelect path to host:")
        print(f"1. Default ({saved_path})")
        print( "2. Set new path")

        # Handle invalid input
        try:
            opt = int(input("\nEnter option => "))
        except ValueError:
            raise StateError("Invalid input")
        
        # Handle user input
        if opt == 2:
            saved_path = input("\nEnter new path: ")
        elif opt != 1:
            raise StateError("Invalid option")
        
        # Refine path again (for new path)
        path = helper.refine_path(saved_path)

        # Path validation
        helper.is_valid_dir(path)
        
        # Check if path is not in project folders to avoid conflicts
        base_dir = Path(__file__).resolve().parents[1]
        if base_dir in path.parents or path == base_dir:
            raise StateError("Root directory cannot be inside FyShare folder")
        
        # Save new path to config as default
        if opt == 2:
            def key_update(j):
                j["root_directory"] = str(path)

            helper.update_json(
                FileState.config_path,
                key_update
            )

        FileState.ROOT_DIR = path

    def set_templates(path):
        path = helper.refine_path(path)

        # Path validation
        helper.is_valid_dir(path)
        
        try:
            with (path / 'login.html').open('r', encoding="utf-8") as f:
                FileState.LOGIN_HTML = f.read()
            with (path / 'fyshare.html').open('r', encoding="utf-8") as f:
                FileState.FYSHARE_HTML = f.read()  
        except (OSError, UnicodeDecodeError) as e:
            raise StateError(f"Reading template: {str(e)}") from e

    def set_static_dir(path):
        path = helper.refine_path(path)

        # Path validation
        helper.is_valid_dir(path)
        
        FileState.STATIC_DIR = path

    def backup_config():
        print("\n\nDo you want to reset the current config to default?")
        opt = input(" (y/n) => ").strip().lower()

        curr_config_path = FileState.config_path

        if opt == "y" or opt == "yes":
            source_path = curr_config_path.with_name("config_example.json")
            helper.copy_file(source_path, curr_config_path)
            print(f"\nConfig successfully reset")
            print(f"- '{curr_config_path.name}' restored from '{source_path.name}'.")

        elif opt == "n" or opt == "no":
            print(f"\nReset cancelled")
            print(f"- Current config '{curr_config_path.name}' was kept unchanged.")
            return False
        
        else:
            print(f"\nInvalid input: '{opt}'")
            print(f"- Reset cancelled.")
            return False
        
        return True
        
        
