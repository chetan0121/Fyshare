from pathlib import Path
from ..utils import helper

class StateError(Exception): pass

class FileState:
    # === Global ===
    CONFIG: dict 
    ROOT_DIR: Path
    STATIC_DIR: Path

    LOGIN_HTML: str
    FYSHARE_HTML: str

    # Config path
    config_path: str | Path

    # Base dir of project
    base_dir: Path = None

    # For github CI
    ci_mod = False

    # Must set CONFIG before using this
    def set_root_path():
        if FileState.ci_mod:
            FileState.ROOT_DIR = FileState.base_dir
            return

        saved_path = Path(FileState.CONFIG["root_directory"]).expanduser()
        try:
           helper.is_valid_dir(saved_path)
        except helper.UtilityError:
            saved_path = Path("~").expanduser()

        # === Path selection by User ===
        print("\nSelect path to host:")
        print(f"1. Default ({saved_path})")
        print( "2. Save and use new path")
        print( "3. Use temp path")

        # Handle invalid input
        try:
            opt = int(input("\nEnter option => "))
        except ValueError:
            raise StateError("Invalid input")
        
        # Handle user input
        if opt == 2 or opt == 3:
            saved_path = input("\nEnter new path: ")
        elif opt != 1:
            raise StateError("Invalid option")
        
        # Refine path
        path = helper.refine_path(saved_path)

        # Path validation
        helper.is_valid_dir(path)
        
        # Check if path is not in project folders to avoid conflicts
        if FileState.base_dir in path.parents or path == FileState.base_dir:
            raise StateError(f"Root directory '{path}' cannot be inside FyShare folder")
        
        # Save new path to config as default
        if opt == 2:
            def key_update(j):
                j["root_directory"] = str(path)

            helper.update_json(
                FileState.config_path,
                key_update
            )

        # Set root dir
        FileState.ROOT_DIR = path

    def set_templates(path):
        path = helper.refine_path(path)
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
        helper.is_valid_dir(path)
        FileState.STATIC_DIR = path   