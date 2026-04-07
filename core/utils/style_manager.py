import re
import sys
from typing import Final, Union, Optional
from enum import IntEnum
from . import helper

class TextStyle(IntEnum):
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
    
    # Allows using enum values as callable methods
    # e.g. TextStyle.BOLD("Hello")
    def __call__(self, text):
        return Style.styled(text, self)

class Color(IntEnum):
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
    
    # Allows using enum values as callable methods
    # e.g. Color.BLUE("Hello")
    def __call__(self, text):
        return Style.styled(text, self)

class Bg(IntEnum):
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
    
    # Allows using enum values as callable methods
    # e.g. Bg.BLUE("Hello")
    def __call__(self, text):
        return Style.styled(text, self)
    

class Style:
    ESC: Final = "\033["
    RESET: Final = f"{ESC}0m"
    
    _VALID_ANSI: Final = re.compile(r'\033\[[0-?]*[ -/]*[@-~]')
    
    # Cache valid color values
    _VALID_FGS = (int(v) for k, v in Color.__dict__.items() if not k.startswith('_'))
    _VALID_BGS = (int(v) for k, v in Bg.__dict__.items() if not k.startswith('_'))

    @staticmethod
    def _to_escape(codes: Optional[list[str]]):
        """Convert Numbers to ANSI escape code if valid"""
        if not codes:
            return ""
        return f"{Style.ESC}{';'.join(str(c) for c in codes)}m"
    
    @staticmethod
    def _resolve(codes: Union[list, tuple, set]) -> Optional[list]:
        """
        Handle Code list and resolve custom codes
        """
        # Check if empty
        if not codes:
            return None
        
        # Extract all valid integers
        raw_codes = []
        for c in codes:
            num = helper.try_parse_int(c)
            if num is not None and num >= 0:
                raw_codes.append(num)

        # State trackers
        color = None
        bg = None
        bright_fg = False
        bright_bg = False
        normal_codes = []

        # Classify each code
        for code in raw_codes:
            if code in Style._VALID_FGS:
                color = code
            elif code in Style._VALID_BGS:
                bg = code
            elif code == TextStyle.BRIGHT:
                bright_fg = True
            elif code == TextStyle.BRIGHT_BG:
                bright_bg = True
            else:
                normal_codes.append(code)

        # Apply brightness if requested
        if color is not None:
            if bright_fg and color != Color.DEFAULT:
                color += 60
            normal_codes.append(color)    

        if bg is not None:
            if bright_bg and bg != Bg.DEFAULT:
                bg += 60    
            normal_codes.append(bg)    

        return normal_codes
    
    @staticmethod
    def strip(text: str) -> str:
        """Remove all ANSI escape codes from text."""
        if not text:
            return ""
        return Style._VALID_ANSI.sub('', text)
    
    @staticmethod
    def styled(text: str, *styles) -> str:
        """
        Return Styled Text wrapped with ANSI escape codes
        
        :param text: Text to be styled
        :param styles: Styles to be applied, like tuple of integers, 
        
        Usage: 
            1. red_txt = styled("I am Bold Red", Colors.RED, TextStyle.BOLD)
            2. yellow_txt = styled("Manually styling, Bold yellow txt", 1, 33)
        """
        if not isinstance(text, str):
            raise TypeError("text must be type str")
        
        # Check if empty
        if not styles:
            return text
        
        resolved = Style._resolve(styles)
        escape_seq = Style._to_escape(resolved)

        return f"{escape_seq}{text}{Style.RESET}"
    
    @staticmethod
    def print(txt="", *codes, prefix="", end="\n"):
        """
        Prints styled text to the console using ANSI escape codes.

        Args:
            - txt: The text to print. Defaults to an empty string.
            - *codes: Variable-length list of ANSI codes (int/str)
                        to style the text. Example: 31 for red, 1 for bold.
            - prefix: String appended before the styled txt.
            - end: String appended after the styled text.
        Notes:
            - ANSI codes are applied to the text only; 
                `end` and 'prefix' are printed as-is.
            - If no valid ANSI codes are provided, the text is printed as it is.
            - Invalid ANSI codes (non-integer/non-string/non-ANSI) are ignored.
        """
        msg = Style.styled(txt, *codes)
        sys.stdout.write(f"{prefix}{msg}{end}")
