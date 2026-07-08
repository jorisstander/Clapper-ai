"""Tile codes — the single source of truth for what each int on a Grid means.

The numbering follows Vestaboard's character codes so a real board can be a
drop-in display later:

    0        blank
    1-26     A-Z
    27-36    digits 1,2,...,9,0  (note: 0 is code 36, after 9)
    63-69    color tiles: red, orange, yellow, green, blue, violet, white

TODO: punctuation codes (37-62) can be filled in from Vestaboard's official
Character Codes reference later.
"""

BLANK = 0

# Character → tile code. Unknown characters are not in this map;
# text_to_grid renders them as blanks.
CHAR_TO_CODE: dict[str, int] = {" ": BLANK}
for i, letter in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ", start=1):
    CHAR_TO_CODE[letter] = i
for i, digit in enumerate("1234567890", start=27):
    CHAR_TO_CODE[digit] = i

# Color tiles have no character; address them by name.
COLOR_CODES: dict[str, int] = {
    "red": 63,
    "orange": 64,
    "yellow": 65,
    "green": 66,
    "blue": 67,
    "violet": 68,
    "white": 69,
}

# Everything a full board accepts. A specific board may pass a smaller
# subset to validate_grid — the gate enforces whatever the target allows.
ALLOWED_CODES: set[int] = set(CHAR_TO_CODE.values()) | set(COLOR_CODES.values())

# Code → character, for debugging and for displays that render text.
CODE_TO_CHAR: dict[int, str] = {code: char for char, code in CHAR_TO_CODE.items()}
