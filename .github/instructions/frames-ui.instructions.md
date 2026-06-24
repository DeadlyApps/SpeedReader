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
- HIGH-RISK: pyttsx3's SAPI5 engine is a **COM object** — it MUST be created, pumped (`startLoop`), and have its callbacks delivered on the **SAME thread**. Creating it on the tkinter main thread but pumping it elsewhere crashes the process (`PyEval_RestoreThread ... thread state NULL`) on Python 3.12+/3.14. `MainFrame.__init__` calls `self.speech.prime_async(500)` to create AND pump it on one dedicated daemon thread, BEFORE `get_voices()`. Never call `pyttsx3.init()` on the main thread.
- The engine is created **once** and reused on that loop thread. `get_voices()` returns voices the loop thread enumerated (cached/waited-for, never created on the caller); `speak()` waits for the engine (`_await_engine`) instead of creating it; `startLoop()` runs at most once (guarded by `_started`). Never re-init or call `startLoop()` twice.
- Apply BOTH rate and the selected voice on every utterance (`set_voice()` is store-only — applied per-utterance so the main thread never touches the COM engine); the voice is shared by the GUI and the MCP server.
- Word highlighting uses single-line Text indices `"1.{char_offset}"`; input newlines are replaced with spaces in `speak()`. Keep the `TAG_CURRENT_WORD` constant defined at module level.
