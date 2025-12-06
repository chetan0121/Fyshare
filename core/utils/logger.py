import logging
import sys
from pathlib import Path

class CodeDict(dict):
    __setattr__ = dict.__setitem__
    RESET = "\033[0m"

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)
    
    @staticmethod
    def join_codes(codes: list):
        return f"\033[{';'.join(codes)}m"

COLORS = CodeDict({
    "black": 30,
    "red": 31,
    "green": 32,
    "yellow": 33,
    "blue": 34,
    "magenta": 35,
    "cyan": 36,
    "white": 37
})

def set_logger(file: str) -> None:
    """
    Configure rotating file logger
    - Automatically creates log directory if it doesn't exist
    - 1 MB per file, keeps last 3 backups
    - UTF-8 encoding
    - Timestamp format: 2025-12-06 14:32:10

    Param: file -> Name and path of a log file
    
    Usage:
        set_logger("logs/fyshare.log")
        Log something using:
            e.g. logger.log_error("Server started")
    """
    from logging.handlers import RotatingFileHandler
    
    Path(file).parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        force=True,  # Removes previous handlers
        handlers=[
            RotatingFileHandler(
                file,
                maxBytes=1_000_000,
                backupCount=3,
                encoding='utf-8'
            )
        ]
    )

# Check for int
def __parse_int(txt) -> int | None:
    try:
        num = int(txt)
        return num
    except (TypeError, ValueError):
        return None

# Print text with optional ANSI escape codes
def print_custom(txt="", *codes, end="\n"):
    """
    Prints styled text to the console using ANSI escape codes.

    Args:
        - txt (str): The text to print. Defaults to an empty string.
        - *ansi_codes: Variable-length list of ANSI codes (int/str)
                     to style the text. Example: 31 for red, 1 for bold.
        - end (str): String appended after the text. Defaults to a newline.
    Notes:
        - ANSI codes are applied to the text only; `end` is printed as-is.
        - If no valid ANSI codes are provided, the text is printed as it is.
        - Invalid ANSI codes (non-integer/non-string/non-ANSI) are ignored.
    """
    
    valid_codes = [str(c) for c in codes if __parse_int(c) is not None]

    msg = txt
    if valid_codes:
        prefix = CodeDict.join_codes(valid_codes)
        msg = f"{prefix}{txt}{CodeDict.RESET}"
    
    sys.stdout.write(f"{msg}{end}")

# === Utils ===
def __set_level(txt: str, level: str, enable: bool):
    return f"[{level}] {txt}" if enable else txt

def __print_level(
    txt: str,
    prefix: str,
    end: str,
    color: str | int,
    is_bright: bool,
    is_bold: bool
):
    """Private Function to style txt of printers (e.g. print_error())"""

    color = __parse_int(color) 
    if color not in COLORS.values():
        color = 37  # White as default

    codes = []
    if is_bright:
        codes.append(color + 60)
    else:
        codes.append(color)    

    if is_bold:
        codes.append(1)

    print_custom(f"{prefix}{txt}", *codes, end=end)

# ========= Printer functions =========
def print_error(*msg, sep=" | ", prefix="\n", end="\n\n", lvl_tag=True, bright=True, bold=False):
    message = sep.join(msg)
    message = __set_level(message, "ERROR", lvl_tag)

    __print_level(
        message,
        prefix,
        end,
        color=31,
        is_bright=bright,
        is_bold=bold
    )

def print_warning(*msg, sep=" | ", prefix="\n", end="\n\n", lvl_tag=True, bright=True, bold=False):
    message = sep.join(msg)
    message = __set_level(message, "WARNING", lvl_tag)

    __print_level(
        message,
        prefix,
        end,
        color=33,
        is_bright=bright,
        is_bold=bold
    )

def print_info(*msg, sep=" | ", prefix="\n", end="\n\n", lvl_tag=True, bright=True, bold=False):
    message = sep.join(msg)
    message = __set_level(message, "INFO", lvl_tag)

    __print_level(
        message,
        prefix,
        end,
        color=37,
        is_bright=bright,
        is_bold=bold
    )

# ========= Logging functions =========
def log_error(*msg, sep=" | ", lvl_tag=True, prefix=""):
    message = sep.join(msg)
    message = __set_level(message, "ERROR", lvl_tag)

    logging.error(f"{prefix}{message}")

def log_warning(*msg, sep=" | ", lvl_tag=True, prefix=""):
    message = sep.join(msg)
    message = __set_level(message, "WARNING", lvl_tag)

    logging.warning(f"{prefix}{message}")
    
def log_info(*msg, sep=" | ", lvl_tag=True, prefix=""):
    message = sep.join(msg)
    message = __set_level(message, "INFO", lvl_tag)

    logging.info(f"{prefix}{message}")

# ===== Logging and Printing =====
def __emit_print(txt: str, color: int):
    # print error
    __print_level(
        txt,
        "\n",
        "\n\n",
        color=color,
        is_bright=True,
        is_bold=False
    )

def emit_error(*msg, sep=" | ", lvl_tag = True):
    message = sep.join(msg)
    message = __set_level(message, "ERROR", lvl_tag)

    # Print error
    __emit_print(message, 31)

    # Log error
    logging.error(f"{message}")

def emit_warning(*msg, sep=" | ", lvl_tag = True):
    message = sep.join(msg)
    message = __set_level(message, "WARNING", lvl_tag)

    # print warning
    __emit_print(message, 33)

    # Log warning
    logging.warning(f"{message}")
    
def emit_info(*msg, sep=" | ", lvl_tag = True):
    message = sep.join(msg)
    message = __set_level(message, "INFO", lvl_tag)

    # print info
    __emit_print(message, 37)

    # Log info
    logging.info(f"{message}")
