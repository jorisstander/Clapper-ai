# Character codes

The single source of truth is `src/clapper_ai/domain/tile_codes.py`. The numbering
follows Vestaboard's character codes so a real board can be a drop-in display.

| Code | Tile |
|------|------|
| `0` | blank |
| `1`–`26` | `A`–`Z` |
| `27`–`36` | digits `1`,`2`,…,`9`,`0` (note: `0` is code `36`, after `9`) |
| `37`–`62` | *reserved: punctuation — not yet mapped* |
| `63` | red |
| `64` | orange |
| `65` | yellow |
| `66` | green |
| `67` | blue |
| `68` | violet |
| `69` | white |

Notes:

- `text_to_grid` renders any character it doesn't know as a blank (`0`).
- Punctuation (`37`–`62`) can be filled in from Vestaboard's official
  [Character Codes reference](https://docs.vestaboard.com/docs/characterCodes)
  — a good first contribution. Update `CHAR_TO_CODE` in `domain/tile_codes.py`
  and the mirror table at the top of
  `src/clapper_ai/adapters/displays/virtual/static/board.js`.
- A board that supports fewer tiles passes its own `allowed` set to
  `validate_grid`; the gate enforces whatever the target allows.
