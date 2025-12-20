import re
import sys
from typing import Union, Optional

def _parse_int(txt) -> Optional[int]:
    try:
        num = int(txt)
        return num
    except (TypeError, ValueError):
        return None

class Style:
    ESC = "\033["
    RESET = f"{ESC}0m"

    def _to_escape(codes: list[str]):
        """Convert Numbers to ANSI escape code if valid"""
        if not codes:
            return ""
        return f"{Style.ESC}{';'.join(str(c) for c in codes)}m"
    
    def _resolve(codes: Union[list, tuple, set]) -> list:
        """
        Handle Code list and resolve custom codes
        """
        # Check if empty
        if not codes:
            return None
        
        # Extract all valid integers
        raw_codes = []
        for c in codes:
            num = _parse_int(c)
            if num is not None and num >= 0:
                raw_codes.append(num)

        # Cache valid color values
        valid_fgs = [int(v) for k, v in Color.__dict__.items() if not k.startswith('_')]
        valid_bgs = [int(v) for k, v in Bg.__dict__.items() if not k.startswith('_')]

        # State trackers
        color = None
        bg = None
        apply_bright_color = False
        apply_bright_bg = False
        normal_codes = []

        # Classify each code
        for code in raw_codes:
            if code in valid_fgs:
                color = code
            elif code in valid_bgs:
                bg = code
            elif code == TextStyle.BRIGHT:
                apply_bright_color = True
            elif code == TextStyle.BRIGHT_BG:
                apply_bright_bg = True
            else:
                normal_codes.append(code)

        # Apply brightness if requested
        if color is not None:
            if apply_bright_color and color != Color.DEFAULT:
                color += 60
            normal_codes.append(color)    

        if bg is not None:
            if apply_bright_bg and bg != Bg.DEFAULT:
                bg += 60    
            normal_codes.append(bg)    

        return normal_codes
    
    def strip(text: str) -> str:
        """Remove all ANSI escape codes from text."""
        return re.sub(r"\033\[[0-9;]*m", "", text)
    
    def styled(text: str, *styles) -> str:
        """
        Return Styled Text wrapped with ANSI escape codes
        
        :param text: Text to be styled
        :param styles: Styles to be applied, tuple of raw integers (from ANSI codes)
            
        Usage: 
            1. red_txt = styled("I am Bold Red", Colors.RED, TextStyle.BOLD)
            2. yellow_txt = styled("Manually styling, Bold yellow txt", 1, 33)
        """
        # Check if empty
        if not styles:
            return text
        
        resolved = Style._resolve(styles)
        escape_seq = Style._to_escape(resolved)

        return f"{escape_seq}{text}{Style.RESET}"
    
    def print_style(txt="", *codes, prefix="", end="\n"):
        """
        Prints styled text to the console using ANSI escape codes.

        Args:
            - txt: The text to print. Defaults to an empty string.
            - *ansi_codes: Variable-length list of ANSI codes (int/str)
                        to style the text. Example: 31 for red, 1 for bold.
            - end: String appended after the text. Defaults to a newline.
        Notes:
            - ANSI codes are applied to the text only; 
                `end` and 'prefix' are printed as-is.
            - If no valid ANSI codes are provided, the text is printed as it is.
            - Invalid ANSI codes (non-integer/non-string/non-ANSI) are ignored.
        """
        msg = Style.styled(txt, *codes)
        sys.stdout.write(f"{prefix}{msg}{end}")


class TextStyle:
    """Text styles"""
    BOLD      = 1
    DIM       = 2
    UNDERLINE = 4
    BLINK     = 5
    REVERSE   = 7
    HIDDEN    = 8    

    # Custom style
    BRIGHT = 200
    BRIGHT_BG = 300

class Color:
    """All Foreground color codes(integers)"""
    BLACK   = 30
    RED     = 31
    GREEN   = 32
    YELLOW  = 33
    BLUE    = 34
    MAGENTA = 35
    CYAN    = 36
    WHITE   = 37

    # Others
    PURPLE  = MAGENTA
    RESET = 39
    DEFAULT = 39

class Bg:
    """All Background color codes(integers)"""
    BLACK   = 40
    RED     = 41
    GREEN   = 42
    YELLOW  = 43
    BLUE    = 44
    MAGENTA = 45
    CYAN    = 46
    WHITE   = 47

    # Others
    PURPLE  = MAGENTA
    RESET = 49
    DEFAULT = 49
