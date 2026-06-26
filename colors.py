import json
from pathlib import Path
from typing import Literal, Optional

StyleName = Literal["reset", "bold", "dim", "italic", "underline", "blink", "reverse", "hidden"]

FgColorName = Literal[
    "reset", "black", "red", "green", "yellow", "blue", "magenta", "cyan", "white",
    "bright_black", "bright_red", "bright_green", "bright_yellow",
    "bright_blue", "bright_magenta", "bright_cyan", "bright_white",
    "orange", "dark_orange", "brown", "dark_brown", "pink", "hot_pink",
    "lime", "mint", "teal", "olive", "navy", "purple", "violet", "lavender",
    "gold", "beige", "dark_gray", "gray", "silver"
]

BgColorName = Literal[
    "black", "red", "green", "yellow", "blue", "magenta", "cyan", "white",
    "bright_black", "bright_red", "bright_green", "bright_yellow",
    "bright_blue", "bright_magenta", "bright_cyan", "bright_white"
]

script_path = Path(__file__).resolve()
JSON_PATH = script_path.parent / "colors.json"

with open(JSON_PATH, "r") as f:
    json_object = json.load(f)

def _decode_dict(target_dict : dict):
    return {name: seq.encode().decode("unicode_escape") for name, seq in target_dict.items()}

STYLE = _decode_dict(json_object["styles"])
FOREGROUND = _decode_dict(json_object["foreground"])
BACKGROUND = _decode_dict(json_object["background"])


def colortext(text : str, foregorund: Optional[FgColorName] = None, background: Optional[BgColorName] = None, style: Optional[StyleName] = None) -> str:
    buffer = ""
    if style : buffer += STYLE[style]
    if foregorund : buffer += FOREGROUND[foregorund]
    if background : buffer += BACKGROUND[background]
    if not buffer: return text
    return f"{buffer}{text}{FOREGROUND['reset']}"

def colorprint(text : str, foregorund: Optional[FgColorName] = None, background: Optional[BgColorName] = None, style: Optional[StyleName] = None) -> None:
    print(colortext(text, foregorund, background, style))

