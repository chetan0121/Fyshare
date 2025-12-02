import logging
from sys import stdout
from pathlib import Path
from logging.handlers import RotatingFileHandler

def set_logger(file):
    log_file = Path(file)
    log_file.parent.mkdir(exist_ok=True)
    root_logger = logging.getLogger()

    # Logs config
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s | %(message)s',
        datefmt = f"%Y-%m-%d %H:%M:%S"
    )

    # Handle logging files
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=1_000_000,
        backupCount=3,
        encoding='utf-8'
    )

    # Format for Logging
    formatter = logging.Formatter(
        fmt = '%(asctime)s | %(message)s',
        datefmt = f'%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)


# To check if its int or not
def __is_int(s):
    try:
        int(s)
        return True     
    except ValueError:
        return False

# Print text with optional ANSI escape codes
def print_custom(txt="\n", *ansiCode, end="\n"):
    ansiCode = [str(a) for a in ansiCode if isinstance(int, a) or __is_int(a)]
    if ansiCode:
        ansiCodes = "\033[" + ";".join(ansiCode) + "m"
        msg = str(ansiCodes + txt + "\033[0m")
    else:
        msg = txt
        
    stdout.write(f"{msg}{end}")    

# ========= Printer functions =========
def print_error(*msg, sep=" | ", st="\n", end="\n", bright=True, bold=False):
    message = sep.join(msg)
    final_msg = f"{st}[ERROR] {message}"

    codes = [91 if bright else 31]
    if bold:
        codes.append(1)

    print_custom(final_msg, ansiCode=codes, end=end)

def print_warning(*msg, sep=" | ", st="\n", end="\n", bright=True, bold=False):
    message = sep.join(msg)
    final_msg = f"{st}[WARNING] {message}"

    codes = [93 if bright else 33]
    if bold:
        codes.append(1) # appending 1 to make the txt bold

    print_custom(final_msg, ansiCode=codes, end=end)

def print_info(*msg, sep=" | ", st="\n", end="\n", info_tag=True, bright=True, bold=False):
    message = sep.join(msg)
    if info_tag:
        final_msg = f"{st}[INFO] {message}"
    else:
        final_msg = f"{st}{message}"

    codes = [97 if bright else 37]
    if bold:
        codes.append(1) # appending 1 to make the txt bold

    print_custom(final_msg, ansiCode=codes, end=end)

# ========= Logging functions =========
def log_error(*msg, sep=" | ", st=""):
    message = sep.join(msg)
    final_msg = f"{st}[ERROR] {message}"
    logging.error(final_msg)

def log_warning(*msg, sep=" | ", st=""):
    message = sep.join(msg)
    final_msg = f"{st}[WARNING] {message}"
    logging.warning(final_msg)    

def log_info(*msg, sep=" | ", info_tag=False, st=""):
    message = sep.join(msg)
    if info_tag:
        final_msg = f"{st}[INFO] {message}"
    else:
        final_msg = f"{st}{message}"
    logging.info(final_msg)    
