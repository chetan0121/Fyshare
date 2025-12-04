import logging
from sys import stdout
from pathlib import Path
from logging.handlers import RotatingFileHandler

def set_logger(file: Path | str):
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
        - *ansi_codes: Variable-length list of ANSI codes (as integers or strings)
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
        
    stdout.write(f"{msg}{end}")    

# ========= Printer functions =========
def print_error(*msg, sep=" | ", st="\n", end="\n\n", info_tag=True, bright=True, bold=False):
    message = sep.join(msg)
    if info_tag:
        message = f"[ERROR] {message}"

    codes = [91 if bright else 31]
    if bold:
        codes.append(1)

    print_custom(f"{st}{message}", *codes, end=end)

def print_warning(*msg, sep=" | ", st="\n", end="\n\n", info_tag=True, bright=True, bold=False):
    message = sep.join(msg)
    if info_tag:
        message = f"[WARNING] {message}"

    codes = [93 if bright else 33]
    if bold:
        codes.append(1) # appending 1 to make the txt bold

    print_custom(f"{st}{message}", *codes, end=end)

def print_info(*msg, sep=" | ", st="\n", end="\n\n", info_tag=True, bright=True, bold=False):
    message = sep.join(msg)
    if info_tag:
        message = f"[INFO] {message}"

    codes = [97 if bright else 37]
    if bold:
        codes.append(1) # appending 1 to make the txt bold

    print_custom(f"{st}{message}", *codes, end=end)


# ========= Logging functions =========
def log_error(*msg, sep=" | ", info_tag=False, st=""):
    message = sep.join(msg)
    if info_tag:
        final_msg = f"{st}[ERROR] {message}"
    else:
        final_msg = f"{st}{message}"
    logging.error(final_msg)

def log_warning(*msg, sep=" | ", info_tag=False, st=""):
    message = sep.join(msg)
    if info_tag:
        final_msg = f"{st}[WARNING] {message}"
    else:
        final_msg = f"{st}{message}"
    logging.warning(final_msg)    

def log_info(*msg, sep=" | ", info_tag=False, st=""):
    message = sep.join(msg)
    if info_tag:
        final_msg = f"{st}[INFO] {message}"
    else:
        final_msg = f"{st}{message}"
    logging.info(final_msg)    

