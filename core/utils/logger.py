import logging
import sys
from pathlib import Path

def set_logger(file: Path | str):
    from logging.handlers import RotatingFileHandler
    
    log_file = Path(file)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        force=True,  # Removes previous handlers
        handlers=[
            RotatingFileHandler(
                str(log_file),
                maxBytes=1_000_000,
                backupCount=3,
                encoding='utf-8'
            )
        ]
    )

# Print text with optional ANSI escape codes
def print_custom(txt="", *ansiCodes, end="\n"):
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
    
    def __is_int(s):
        """Helper to check if a value can be converted to an integer."""
        try:
            int(s)
            return True     
        except (ValueError, TypeError):
            return False
        
    clean_codes = []
    for a in ansiCodes:
        if isinstance(a, int) or __is_int(a):
            clean_codes.append(str(a))

    if clean_codes:
        prefix = "\033[" + ";".join(clean_codes) + "m"
        msg = str(prefix + txt + "\033[0m")
    else:
        msg = txt
        
    sys.stdout.write(f"{msg}{end}")    

def __print_level(
    msg="", 
    level="", 
    st="", 
    end="", 
    color=37, 
    bright=True, 
    bold=False
):
    """Private Function to style txt of printers (e.g. print_error())"""

    if level:
        level.strip().upper()
        msg = f"[{level}] {msg}"

    codes = []
    if bright:
        codes.append(color + 60)
    else:
        codes.append(color)    

    if bold:
        codes.append(1)

    print_custom(f"{st}{msg}", *codes, end=end)


# ========= Printer functions =========
def print_error(*msg, sep=" | ", st="\n", end="\n\n", lvl_tag=True, bright=True, bold=False):
    message = sep.join(msg)
    lvl = "Error" if lvl_tag else ""

    __print_level(
        message,
        level=lvl,
        st=st,
        end=end,
        color=31,
        bright=bright,
        bold=bold
    )

def print_warning(*msg, sep=" | ", st="\n", end="\n\n", lvl_tag=True, bright=True, bold=False):
    message = sep.join(msg)
    lvl = "Warning" if lvl_tag else ""

    __print_level(
        message,
        level=lvl,
        st=st,
        end=end,
        color=33,
        bright=bright,
        bold=bold
    )

def print_info(*msg, sep=" | ", st="\n", end="\n\n", lvl_tag=True, bright=True, bold=False):
    message = sep.join(msg)
    lvl = "Info" if lvl_tag else ""

    __print_level(
        message,
        level=lvl,
        st=st,
        end=end,
        color=37,
        bright=bright,
        bold=bold
    )


# ========= Logging functions =========
def log_error(*msg, sep=" | ", lvl_tag=False, st=""):
    message = sep.join(msg)
    if lvl_tag:
        message = f"[ERROR] {message}"

    logging.error(f"{st}{message}")

def log_warning(*msg, sep=" | ", lvl_tag=False, st=""):
    message = sep.join(msg)
    if lvl_tag:
        message = f"[WARNING] {message}"

    logging.warning(f"{st}{message}")    

def log_info(*msg, sep=" | ", lvl_tag=False, st=""):
    message = sep.join(msg)
    if lvl_tag:
        message = f"[INFO] {message}"

    logging.info(f"{st}{message}")    
