import os
from pathlib import Path

def refine_path(path):
   path = str(path).strip()
   return Path(path).expanduser().resolve()

class StateError(Exception): pass

class ServerState:
    PORT = str()
    OTP = str()
    USERNAME = str()


class FileState:
    # === Global ===
    CONFIG = dict()         # Assigned in Fyshare.py
    ROOT_DIR = Path()       # Assigned in set_root_path
    TEMPLATE_DIR = Path()   # Assigned
    STATIC_DIR = Path()

    LOGIN_HTML = Path()
    FYSHARE_HTML = Path()

    config_path = str()
    raw_config = dict()

    # Must set CONFIG before using this
    @staticmethod
    def set_root_path():
        if not FileState.CONFIG:
            raise StateError("config not found")

        saved_path = refine_path(FileState.CONFIG["root_directory"])

        # Path selection by User
        print("\nSelect path to host:")
        print(f"1. Default ('{saved_path}')")
        print( "2. Set path")
        try:
            opt = int(input("\nEnter option => "))
            if opt == 2:
                saved_path = input("\nEnter new path: ")
            elif opt != 1:
                raise StateError("Invalid option")
        except ValueError:
            raise StateError("ValueError: Invalid input")
        
        path = refine_path(saved_path)

        if not path.exists():
            raise StateError(f"{path} does not exist")
        elif not path.is_dir():
            raise StateError(f"{path} is not a directory")
        
        base_dir = Path(__file__).resolve().parents[2]
        if base_dir in path.parents or path == base_dir:
            raise StateError("Root directory cannot be inside FyShare folder")
        else:
            print("Base_dir:", base_dir)
        
        FileState.ROOT_DIR = path

    @staticmethod
    def set_template_dir(path):
        path = refine_path(path)

        if not path.is_dir():
            raise StateError(f"Template directory: No such directory '{path}'")
        
        try:
            with (path / 'login.html').open('r', encoding="utf-8") as f:
                FileState.LOGIN_HTML = f.read()
            with (path / 'fyshare.html').open('r', encoding="utf-8") as f:
                FileState.FYSHARE_HTML = f.read()  

        except (OSError, UnicodeDecodeError) as e:
            raise StateError(f"Reading template : {str(e)}") from e
        
    def set_static_dir(path):
        path = refine_path(path)

        if not path.is_dir():
            raise StateError(f"Static directory: No such directory '{path}'")
        
        FileState.STATIC_DIR = path
        

        
        
