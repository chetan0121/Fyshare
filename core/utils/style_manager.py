import re
import sys
from typing import Final, Union, Optional

from . import helper

class TextStyle:
    """Text style codes (immutable constants)."""
    BOLD: Final = 1
    DIM: Final = 2
    UNDERLINE: Final = 4
    BLINK: Final = 5
    REVERSE: Final = 7
    HIDDEN: Final = 8

    # Custom styles (bright variants handled separately)
    BRIGHT: Final = 200
    BRIGHT_BG: Final = 300
    
    def __call__(self, text: str) -> str:
        """Allow using as TextStyle.BOLD(text) for compatibility."""
        return Style.styled(text, self)

class Color:
    """Foreground color codes (immutable constants)."""
    BLACK: Final = 30
    RED: Final = 31
    GREEN: Final = 32
    YELLOW: Final = 33
    BLUE: Final = 34
    MAGENTA: Final = 35
    CYAN: Final = 36
    WHITE: Final = 37

    # Aliases and defaults
    PURPLE: Final = MAGENTA
    RESET: Final = 39
    DEFAULT: Final = 39
    
    def __call__(self, text: str) -> str:
        """Allow using as Color.RED(text) for compatibility."""
        return Style.styled(text, self)

class Bg:
    """Background color codes (immutable constants)."""
    BLACK: Final = 40
    RED: Final = 41
    GREEN: Final = 42
    YELLOW: Final = 43
    BLUE: Final = 44
    MAGENTA: Final = 45
    CYAN: Final = 46
    WHITE: Final = 47

    # Aliases and defaults
    PURPLE: Final = MAGENTA
    RESET: Final = 49
    DEFAULT: Final = 49
    
    def __call__(self, text: str) -> str:
        """Allow using as Bg.BLUE(text) for compatibility."""
        return Style.styled(text, self)
    

class Style:
    """ANSI escape code builder and text styling utilities."""
    ESC: Final = "\033["
    RESET: Final = f"{ESC}0m"
    
    _VALID_ANSI: Final = re.compile(r'\033\[[0-?]*[ -/]*[@-~]')
    
    # Cache valid color values as immutable sets for fast lookup.
    _VALID_FGS: Final = frozenset(
        v for k, v in Color.__dict__.items()
        if not k.startswith('_') and isinstance(v, int)
    )
    _VALID_BGS: Final = frozenset(
        v for k, v in Bg.__dict__.items()
        if not k.startswith('_') and isinstance(v, int)
    )

    @staticmethod
    def _to_escape(codes: Optional[list[int]]) -> str:
        """Convert numbers to ANSI escape code sequence."""
        if not codes:
            return ""
        return f"{Style.ESC}{';'.join(str(c) for c in codes)}m"
    
    @staticmethod
    def _resolve(codes: Union[list, tuple, set]) -> Optional[list[int]]:
        """Resolve ANSI codes and classify into colors, backgrounds, and styles.
        
        Args:
            codes: Sequence of integers or objects representing ANSI codes.
        
        Returns:
            Sorted list of final ANSI codes, or None if empty.
        """
        if not codes:
            return None
        
        # Extract all valid integers (skip non-numeric inputs)
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
        """Apply ANSI styles to text and return the styled string.
        
        Args:
            text: Text to style.
            *styles: ANSI codes (integers, objects with __int__) or aliases.
        
        Returns:
            Text wrapped with ANSI escape codes (or original text if no styles).
        
        Raises:
            TypeError: If text is not a string.
        
        Example:
            Style.styled("Error", Color.RED, TextStyle.BOLD)
        """
        if not isinstance(text, str):
            raise TypeError("text must be type str")
        
        if not styles:
            return text
        
        resolved = Style._resolve(styles)
        escape_seq = Style._to_escape(resolved)
        
        return f"{escape_seq}{text}{Style.RESET}"
    
    @staticmethod
    def print(txt: str = "", *codes, prefix: str = "", end: str = "\n") -> None:
        """Print styled text to stdout using ANSI escape codes.

        Args:
            txt: Text to print (default empty string).
            *codes: ANSI codes to apply (integers or style objects).
            prefix: String to print before the styled text.
            end: String to print after the styled text (default newline).
        
        Notes:
            - ANSI codes style only the text, not prefix or end.
            - Invalid codes are silently ignored.
        
        Example:
            Style.print("Success", Color.GREEN, TextStyle.BOLD, end="\\n")
        """
        msg = Style.styled(txt, *codes)
        sys.stdout.write(f"{prefix}{msg}{end}")
