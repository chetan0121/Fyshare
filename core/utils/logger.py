import logging
from pathlib import Path
from .style_manager import *
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
def __set_level(*txt, sep: str, level: str, enable: bool):
    msg = sep.join(txt)
    return f"[{level}] {msg}" if enable else msg

def __print_level(
    txt: str,
    prefix: str,
    end: str,
    color: int,
    is_bright: bool,
    is_bold: bool
):
    """Private Function to apply limited styles to txt of print_*()"""
    codes = [color]
    if is_bright:
        codes.append(TextStyle.BRIGHT)

    if is_bold:
        codes.append(TextStyle.BOLD)

    Style.print_style(txt, *codes, prefix=prefix, end=end)

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
def log_error(*msg, sep=" | ", lvl_tag=True, prefix="", end=""):
    message = __set_level(*msg, sep=sep, level="ERROR", enable=lvl_tag)

    logging.error(f"{message}{end}", extra={'prefix': prefix})

def log_warning(*msg, sep=" | ", lvl_tag=True, prefix="", end=""):
    message = __set_level(*msg, sep=sep, level="WARNING", enable=lvl_tag)

    logging.warning(f"{message}{end}", extra={'prefix': prefix})
    
def log_info(*msg, sep=" | ", lvl_tag=True, prefix="", end=""):
    message = __set_level(*msg, sep=sep, level="INFO", enable=lvl_tag)

    logging.info(f"{message}{end}", extra={'prefix': prefix})


# ===== Logging and Printing in one =====
def __emit_print(txt: str, color: int):
    __print_level(
        txt,
        "\n",
        "\n\n",
        color=color,
        is_bright=True,
        is_bold=False
    )

def emit_error(*msg, sep=" | ", lvl_tag = True):
    message = __set_level(*msg, sep=sep, level="ERROR", enable=lvl_tag)

    __emit_print(message, Color.RED)
    logging.error(f"{message}", extra={'prefix': ""})

def emit_warning(*msg, sep=" | ", lvl_tag = True):
    message = __set_level(*msg, sep=sep, level="WARNING", enable=lvl_tag)

    __emit_print(message, Color.YELLOW)
    logging.warning(f"{message}", extra={'prefix': ""})
    
def emit_info(*msg, sep=" | ", lvl_tag = True):
    message = __set_level(*msg, sep=sep, level="INFO", enable=lvl_tag)

    __emit_print(message, Color.WHITE)
    logging.info(f"{message}", extra={'prefix': ""})
