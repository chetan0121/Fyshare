import json
import os
from typing import Callable, Optional, Union
from pathlib import Path

class UtilityError(Exception):
    """Exception raised for utility function errors."""
    pass

def refine_path(path: Union[str, Path], resolve: bool = True) -> Path:
    """Normalize and optionally resolve a path string.
    
    Args:
        path: Path string or Path object to normalize.
        resolve: If True, resolve to absolute path; otherwise just normalize.
    
    Returns:
        Normalized Path object.
    
    Raises:
        UtilityError: If path is None or empty.
    """
    if path is None:
        raise UtilityError("Path cannot be None")

    path_str = str(path).strip().strip('"').strip("'")
    if not path_str:
        raise UtilityError("Path cannot be empty")

    path_str = os.path.expandvars(path_str)
    final_path = Path(path_str).expanduser()
    if resolve:
        final_path = final_path.resolve(strict=False)

    return final_path    

def try_parse_int(txt: str) -> Optional[int]:
    """Attempt to parse a string as an integer.
    
    Args:
        txt: The string to parse.
    
    Returns:
        The integer value if parsing succeeds, None otherwise.
    """
    try:
        num = int(txt)
        return num
    except (TypeError, ValueError):
        return None

def is_valid_dir(path: Union[str, Path]) -> None:
    """Validate that a path is an existing, readable directory.
    
    Args:
        path: Path string or Path object to validate.
    
    Raises:
        UtilityError: If path is empty, does not exist, is not a directory,
            or is not readable.
    """
    path = str(path)
    p = Path(path)

    # Empty or whitespace-only path
    if not path or path.strip() == "":
        raise UtilityError("Path cannot be empty")
    
    # Doesn't exist
    if not p.exists():
        raise UtilityError(f"Path '{path}' does not exist")

    # Exists but is a file
    if p.is_file():
        raise UtilityError(f"Path '{path}' is a file, not a directory")

    # Exists but is not a directory
    if not p.is_dir():
        raise UtilityError(f"Path '{path}' is not a directory")

    # If no read permission
    if not os.access(p, os.R_OK):
        raise UtilityError(f"No read permission for directory '{path}'")

def get_json(path: Union[Path, str]) -> dict:
    """Load and parse a JSON file.
    
    Args:
        path: Path to the JSON file.
    
    Returns:
        Parsed JSON data as a dictionary.
    
    Raises:
        UtilityError: If the file does not exist, is not a file, cannot be read,
            or contains invalid JSON.
    """
    json_path = Path(path)

    try:
        if not json_path.is_file():
            raise UtilityError(f"File '{json_path}' not found")
        
        with json_path.open("r") as f:
            config = json.load(f)
    except json.JSONDecodeError:
        raise UtilityError(f"Invalid json code in '{json_path}'")
    except PermissionError:
        raise UtilityError(f"No permission to read json '{json_path}'")
    
    return config

# Update json file with func as provided
def update_json(path: Union[str, Path], update_func: Callable[[dict], None]) -> None:
    """Atomically update a JSON file using a callback function.
    
    Reads the JSON file, passes the parsed data to the callback for modification,
    writes to a temporary file, then atomically replaces the original. Thread-safe
    and works on Windows.
    
    Args:
        path: Path to the JSON file to update.
        update_func: Callback that modifies the JSON data in place.
    
    Raises:
        FileNotFoundError: If the JSON file does not exist.
        json.JSONDecodeError: If the file contains invalid JSON.
        Exception: Other I/O errors propagated after temp file cleanup.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")

    temp_path = path.with_suffix(".tmp")
    
    try:
        # Read the original file
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # Let caller modify the data
        update_func(data)

        # Write to temporary file
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())

        # Atomic replace
        temp_path.replace(path)

    except Exception:
        # Always clean up temp file on error
        if temp_path.exists():
            try:
                temp_path.unlink()
            except:
                pass
        raise

def copy_file(source: Union[str, Path], destination: Union[str, Path]) -> None:
    """Copy a file from source to destination.
    
    Creates the destination directory if needed. If destination is a directory,
    the source filename is used inside it.
    
    Args:
        source: Path to the source file.
        destination: Path to destination file or directory.
    
    Raises:
        UtilityError: If source file does not exist.
    """
    src = refine_path(source)
    dst = refine_path(destination)

    # Check is src file doesn't exist
    if not src.is_file():
        raise UtilityError(f"Source file not found: '{src}'")
    
    # If destination is a directory, use source's filename inside it
    if dst.is_dir():
        dst = dst / src.name
    
    # Ensure parent directories exist
    dst.parent.mkdir(parents=True, exist_ok=True)

    # Read from source
    with open(src, 'rb') as fsrc:
        content = fsrc.read()

    # write to destination
    with open(dst, 'wb') as fdst:
        fdst.write(content)
        fdst.flush()
    