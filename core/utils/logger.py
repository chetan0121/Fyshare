import logging
from pathlib import Path
from .style_manager import Color, Style, TextStyle
from logging.handlers import RotatingFileHandler

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
    Path(file).parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(prefix)s%(asctime)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        force=True,  # Removes previous handlers
        handlers=[
            RotatingFileHandler(
                file,
                maxBytes=1_048_576, # 1 MiB
                backupCount=3,
                encoding='utf-8'
            )
        ]
    )

# ===== Utils =====
def __set_level(*txt: object, sep: str, level: str, enable: bool) -> str:
    """Build a message with optional level tag.
    
    Args:
        txt: Message parts to join (converted to strings).
        sep: Separator for joining message parts.
        level: Level tag (e.g., 'ERROR', 'INFO').
        enable: Whether to include the level tag in output.
    
    Returns:
        Formatted message with optional level prefix.
    """
    msg = sep.join(str(part) for part in txt)
    return f"[{level}] {msg}" if enable else msg

def __print_level(
    txt: str,
    prefix: str,
    end: str,
    color: int,
    is_bright: bool,
    is_bold: bool
) -> None:
    """Print styled text using color and style options.
    
    Private helper for print_* functions.
    """
    codes = [color]
    if is_bright:
        codes.append(TextStyle.BRIGHT)

    if is_bold:
        codes.append(TextStyle.BOLD)

    Style.print(txt, *codes, prefix=prefix, end=end)

# ========= Printer functions =========
def print_error(*msg, sep=" | ", prefix="\n", end="\n\n",
                lvl_tag=True, bright=True, bold=False):
    
    message = __set_level(*msg, sep=sep, level="ERROR", enable=lvl_tag)

    __print_level(
        message,
        prefix,
        end,
        color=Color.RED,
        is_bright=bright,
        is_bold=bold
    )

def print_warning(*msg, sep=" | ", prefix="\n", end="\n\n", 
                  lvl_tag=True, bright=True, bold=False):
    
    message = __set_level(*msg, sep=sep, level="WARNING", enable=lvl_tag)

    __print_level(
        message,
        prefix,
        end,
        color=Color.YELLOW,
        is_bright=bright,
        is_bold=bold
    )

def print_info(*msg, sep=" | ", prefix="\n", end="\n\n", 
               lvl_tag=True, bright=True, bold=False):
    
    message = __set_level(*msg, sep=sep, level="INFO", enable=lvl_tag)

    __print_level(
        message,
        prefix,
        end,
        color=Color.WHITE,
        is_bright=bright,
        is_bold=bold
    )


# ========= Logging functions =========
def log_error(*msg, sep=" | ", lvl_tag=True, prefix="", end="") -> None:
    message = __set_level(*msg, sep=sep, level="ERROR", enable=lvl_tag)

    logging.error(f"{message}{end}", extra={'prefix': prefix})

def log_warning(*msg, sep=" | ", lvl_tag=True, prefix="", end="") -> None:
    message = __set_level(*msg, sep=sep, level="WARNING", enable=lvl_tag)

    logging.warning(f"{message}{end}", extra={'prefix': prefix})
    
def log_info(*msg, sep=" | ", lvl_tag=True, prefix="", end="") -> None:
    message = __set_level(*msg, sep=sep, level="INFO", enable=lvl_tag)

    logging.info(f"{message}{end}", extra={'prefix': prefix})


def __emit_print(txt: str, color: int) -> None:
    """Print styled text to stdout (helper for emit_* functions)."""
    __print_level(
        txt,
        "\n",
        "\n\n",
        color=color,
        is_bright=True,
        is_bold=False
    )

def emit_error(*msg, sep=" | ", lvl_tag = True) -> None:
    message = __set_level(*msg, sep=sep, level="ERROR", enable=lvl_tag)

    __emit_print(message, Color.RED)
    logging.error(f"{message}", extra={'prefix': ""})

def emit_warning(*msg, sep=" | ", lvl_tag = True) -> None:
    message = __set_level(*msg, sep=sep, level="WARNING", enable=lvl_tag)

    __emit_print(message, Color.YELLOW)
    logging.warning(f"{message}", extra={'prefix': ""})
    
def emit_info(*msg, sep=" | ", lvl_tag = True) -> None:
    message = __set_level(*msg, sep=sep, level="INFO", enable=lvl_tag)

    __emit_print(message, Color.WHITE)
    logging.info(f"{message}", extra={'prefix': ""})
