import json
import socket
import os
from pathlib import Path

class UtilityError(Exception): pass

def get_local_ip() -> str:
    # Connect to a public DNS server to discover outgoing interface
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as socket_conn:
        socket_conn.connect(("8.8.8.8", 80))
        local_ip = str(socket_conn.getsockname()[0])
        
        # Verify it's not a localhost
        if not local_ip.startswith("127."):
            return local_ip
    
    # Bind to all available network interfaces (for LAN)
    return "0.0.0.0"

# Refine path
def refine_path(path):
   path = str(path).strip()
   return Path(path).expanduser().resolve()

# Check if its valid directory
def is_valid_dir(path: Path | str):
    """
    Validates that the given path is an existing, real directory.
    Returns the Path object if valid (so you can chain calls).

    Raises:
        UtilityError - with clear message on any failure
    """
    # Convert string to Path
    if isinstance(path, str):
        path = Path(path)

    # Empty or whitespace-only path
    if not path or str(path).strip() == "":
        raise UtilityError("Path cannot be empty")

    # Doesn't exist
    if not path.exists():
        raise UtilityError(f"Path does not exist: '{path}'")

    # Exists but is a file
    if path.is_file():
        raise UtilityError(f"Path is a file, not a directory: '{path}'")

    # Exists but is not a directory
    if not path.is_dir():
        raise UtilityError(f"Path is not a directory: '{path}'")

    # If no read permission
    if not os.access(path, os.R_OK):
        raise UtilityError(f"No read permission for directory: '{path}'")

# Get Configuration
def get_json(path):
    json_path = Path(path)
    if not json_path.exists():
        raise UtilityError(f"File('{json_path}') not found")

    try:
        with json_path.open("r") as f:
            config = json.load(f)
    except json.JSONDecodeError:
        raise UtilityError(f"Invalid json code in '{json_path}'")
    
    return config

# Update json file with func as provided
def update_json(path: Path | str, update_func):
    """
    Atomically update a JSON file using a callback function.
    Thread-safe and works on Windows.
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

    except Exception as e:
        # Always clean up temp file on error
        if temp_path.exists():
            try:
                temp_path.unlink()
            except:
                pass
        raise e

def copy_file(source, destination):
    """
    Creates a NEW file at 'destination' with:
        - Same content as 'source'
        - Current date/time as creation & modification time
    """
    src = refine_path(source)
    dst = refine_path(destination)

    if not src.is_file():
        raise UtilityError(f"Source is not a file: '{src}'")
    
    # If destination is a directory → use source's filename inside it
    if dst.is_dir():
        dst = dst / src.name
    
    # Ensure parent directories exist
    dst.parent.mkdir(parents=True, exist_ok=True)
    
    # Read from source, write to destination → this gives fresh timestamps
    with open(src, 'rb') as fsrc:
        content = fsrc.read()
    
    with open(dst, 'wb') as fdst:
        fdst.write(content)
        fdst.flush()             # Make sure data is written
    