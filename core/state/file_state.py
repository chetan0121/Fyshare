from pathlib import Path
from ..utils import helper
from typing import Union

class StateError(Exception): pass

class FileState:
    # === Global ===
    CONFIG: dict 
    ROOT_DIR: Path
    STATIC_DIR: Path

    LOGIN_HTML: str
    FYSHARE_HTML: str

    # Config path
    config_path: Path

    # Base dir of project
    base_dir: Path

    # For github CI
    ci_mod = False

    # Session timeout options (CONSTANT)
    OPTIONS = [
        (5, "5 minutes"),
        (15, "15 minutes"),
        (30, "30 minutes"),
        (60, "1 hour"),
        (120, "2 hours"),
    ]

    @staticmethod
    def set_root_path() -> None:
        """Setup root path - Run this only after Config loaded"""
        if not FileState.CONFIG:
            raise StateError("Refined CONFIG not found")
        
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
            raise StateError(
                f"Root directory '{path}' cannot be inside FyShare folder"
            )
        
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

    @staticmethod
    def set_templates(path: Union[str, Path]) -> None:
        """Load templates (htmls)"""
        path = helper.refine_path(path, False)
        helper.is_valid_dir(path)
        
        try:
            with (path / 'login.html').open('r', encoding="utf-8") as f:
                login_html = f.read()
            with (path / 'fyshare.html').open('r', encoding="utf-8") as f:
                FileState.FYSHARE_HTML = f.read()  
        except (OSError, UnicodeDecodeError) as e:
            raise StateError(f"Reading template: {str(e)}") from e
        
        # Set timeout options in login template
        FileState.OPTIONS.sort(key=lambda x: x[0])
        
        opt_list_html = [
            f'<option value="{mins*60}">{label}</option>'
            for mins, label in FileState.OPTIONS
        ]    

        options_html = "\n".join(opt_list_html)
        FileState.LOGIN_HTML = login_html.replace('{{options}}', options_html)

    @staticmethod
    def set_static_dir(path: Union[str, Path]) -> None:
        """Set and validate static directory path before using it"""
        path = helper.refine_path(path, False)
        helper.is_valid_dir(path)
        FileState.STATIC_DIR = path   
