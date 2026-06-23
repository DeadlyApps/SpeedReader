---
description: "Use when editing tkinter UI code under Frames/ — covers grid layout, widget state idioms, and the pyttsx3 callback/threading model."
applyTo: "Frames/**/*.py"
---
# Frame / UI conventions

Apply these when adding or changing widgets and behavior in [MainFrame.py](../../Frames/MainFrame.py).

## Layout
- Lay out widgets with manual `grid` using the running `row_index` counter. Increment `row_index` after each row; do not hardcode row numbers.
- Configure column/row weights via `grid_columnconfigure` / `grid_rowconfigure` for anything that should stretch.

## Button state idiom
- Set state with `widget['state'] = NORMAL` / `DISABLED`.
- Read state by comparing the stringified value: `widget['state'].__str__() == NORMAL`. Follow this exact pattern for any new buttons — guard handlers the way `speak()` and `stop()` do.

## TTS / threading model (do not break)
- Speech runs on a **daemon `threading.Thread`** (`speak_on_thread`); the UI stays responsive and is updated only from `pyttsx3` callbacks.
- The engine is created **once** and reused. Creating the engine (and connecting callbacks) is separate from starting the run loop: `get_voices()` may create it early to populate the voice picker, and `startLoop()` is started at most once (guarded by `_started`) by the first `speak` or by `ensure_loop()`. Never re-init or call `startLoop()` twice.
- Apply BOTH rate and the selected voice on every utterance (`set_voice()` records the choice); the voice is shared by the GUI and the MCP server.
- Word highlighting uses single-line Text indices `"1.{char_offset}"`; input newlines are replaced with spaces in `speak()`. Keep the `TAG_CURRENT_WORD` constant defined at module level.
