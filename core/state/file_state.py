"""File and template related state management for FyShare-server.

Handles initialization of:
  - Root directory for file serving
  - HTML templates (login and main)
  - Static asset directory
  - Session timeout options
"""

from pathlib import Path
from typing import Union

from ..utils import helper
from ..utils import style_manager as S

class StateError(Exception):
    """Exception raised for state configuration errors."""
    pass

class FileState:
    """Manages static file and template state for the server.
    
    Attributes:
        CONFIG: Configuration dictionary loaded from config.json.
        ROOT_DIR: Root directory where files are served from.
        STATIC_DIR: Directory containing static assets (CSS, JS, etc.).
        LOGIN_HTML: Cached login page HTML with options rendered.
        FYSHARE_HTML: Cached main file browser HTML template.
        config_path: Path to config.json file.
        base_dir: Base directory of FyShare project.
        ci_mod: Flag for CI/CD environments (skips user prompts).
        OPTIONS: Tuple of (minutes, label) for session timeout choices.
    """
    
    # Directory and template paths
    ROOT_DIR: Path
    STATIC_DIR: Path
    base_dir: Path
    
    # File paths
    favicon_path: Path
    config_path: Path
    
    # Config dict
    CONFIG: dict
    
    # HTML templates (cached)
    LOGIN_HTML: str
    FYSHARE_HTML: str
    
    # Environment flag (For github CI)
    ci_mod: bool = False
    
    # Session timeout options (CONSTANT)
    OPTIONS: list[tuple[int, str]] = [
        (5, "5 minutes"),
        (15, "15 minutes"),
        (30, "30 minutes"),
        (60, "1 hour"),
        (120, "2 hours"),
    ]

    @staticmethod
    def set_root_path() -> None:
        """Setup and persist root directory for file serving.
        
        Prompts user to select root directory (unless in CI mode),
        and validates it is accessible and outside project folder, then
        persists the choice to config if it's new.
        
        Raises:
            StateError: If CONFIG not loaded, invalid input, or path validation fails.
        """
        if not FileState.CONFIG:
            raise StateError("Config: cannot set root path, config not found")
        
        # CI/CD mode: skip prompts, use project directory
        if FileState.ci_mod:
            FileState.ROOT_DIR = FileState.base_dir
            return

        # Get saved default path from config
        saved_path = Path(FileState.CONFIG["root_directory"]).expanduser()
        try:
            helper.is_valid_dir(saved_path)
        except helper.UtilityError:
            saved_path = Path("~").expanduser()

        # Prompt user for path selection
        FileState.ROOT_DIR = FileState._get_root_path(saved_path)
    
    @staticmethod
    def _get_root_path(default_path: Path) -> Path:
        """Prompt user to select or enter root directory path.
        
        Args:
            default_path: Current default path from config.
        
        Returns:
            Validated Path object.
        
        Raises:
            StateError: If input is invalid or path validation fails.
        """
        home_dir = str(Path("~").expanduser())
        
        S.Style.print("\nSelect path to host:", S.TextStyle.BOLD, S.Color.CYAN)
        S.Style.print(f"1. Last used ({default_path})")
        S.Style.print(f"2. Home ({home_dir})")
        S.Style.print(f"3. New path")

        try:
            opt = int(input("\nEnter option => "))
        except ValueError:
            raise StateError("Invalid input. option must be a number.")
        
        if opt == 1:
            path_str = str(default_path)
        elif opt == 2:
            path_str = home_dir
        elif opt == 3:
            path_str = input("\nEnter new path: ")
        else:
            raise StateError(f"Invalid option. Choose 1, 2, or 3.")
        
        # Validate path is directory
        path = helper.refine_path(path_str)
        helper.is_valid_dir(path)
        
        # Validate path is not inside project
        if FileState.base_dir in path.parents or path == FileState.base_dir:
            raise StateError(
                f"Root directory '{path}' cannot be inside FyShare folder"
            )
        
        # Save path only if 
        if opt == 3:
            FileState._save_path_to_config(path)
        
        return path
    
    @staticmethod
    def _save_path_to_config(path: Path) -> None:
        """Save root directory path to config file.
        
        Args:
            path: Path to save.
        """
        def update_root_dir(config_dict: dict) -> None:
            config_dict["root_directory"] = str(path)
        
        helper.update_json(FileState.config_path, update_root_dir)

    @staticmethod
    def set_templates(path: Union[str, Path]) -> None:
        """Load and cache HTML templates with dynamic content.
        
        Loads login.html and fyshare.html from the specified directory,
        then injects session timeout options into login page.
        
        Args:
            path: Directory containing login.html and fyshare.html.
            
        Raises:
            StateError: If templates not found or cannot be read.
        """
        path = helper.refine_path(path)
        helper.is_valid_dir(path)
        
        # Load template files
        try:
            login_path = path / 'login.html'
            fyshare_path = path / 'fyshare.html'
            
            with login_path.open('r', encoding="utf-8") as f:
                login_html = f.read()
            with fyshare_path.open('r', encoding="utf-8") as f:
                FileState.FYSHARE_HTML = f.read()
    
        except FileNotFoundError as e:
            raise StateError(f"Template file not found: {e.filename}") from e
        
        except (OSError, UnicodeDecodeError) as e:
            raise StateError(f"Reading template: {str(e)}") from e
        
        # Inject timeout options into login template
        FileState.OPTIONS.sort(key=lambda x: x[0])
        
        opt_html_list = [
            f'<option value="{mins*60}">{label}</option>'
            for mins, label in FileState.OPTIONS
        ]
        options_html = "\n".join(opt_html_list)
        
        FileState.LOGIN_HTML = login_html.replace('{{options}}', options_html)

    @staticmethod
    def setup_static_dir(path: Union[str, Path]) -> None:
        """Set and validate static assets directory.
        
        Args:
            path: Directory containing static assets (CSS, JS, images, etc.).
            
        Raises:
            UtilityError: If path doesn't exist or is not readable.
        """
        # Set static dir
        path = helper.refine_path(path)
        helper.is_valid_dir(path)
        FileState.STATIC_DIR = path
        
        # Favicon
        FileState.favicon_path = FileState.STATIC_DIR / 'images/favicon.ico'
