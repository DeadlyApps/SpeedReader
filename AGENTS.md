# SpeedReader — Agent Instructions

Desktop GUI app that uses text-to-speech to read pasted text aloud at high WPM, while highlighting the current word. Python + tkinter, packaged to a Windows EXE. See [README.md](README.md) for background and usage tips.

## Architecture

Thin MVC split — keep new UI logic in the frame, not in entry points:

- [SpeedReader.py](SpeedReader.py) — entry point. Instantiates the controller and runs `mainloop()`. Keep it minimal.
- [Controllers/SpeedReaderController.py](Controllers/SpeedReaderController.py) — subclass of `tkinter.Tk`. Owns the window (title, grid weights) and mounts `MainFrame`.
- [Frames/MainFrame.py](Frames/MainFrame.py) — subclass of `ttk.Frame`. Holds nearly all logic: widget layout (manual `grid` with `row_index` counter), TTS engine wiring, and key bindings.

## TTS engine model (the core pattern)

- Speech runs on a **daemon `threading.Thread`** (`speak_on_thread`) so the tkinter UI stays responsive. UI updates are driven by `pyttsx3` callbacks, not by polling.
- The engine is initialized **once** and reused. On first `speak`, `engine.startLoop()` is called and event callbacks are connected; subsequent calls only `setProperty('rate', ...)` and `say(...)`. Do not re-init or call `startLoop()` again.
- Callbacks map to UI state:
  - `started-utterance` → `onStart` (toggle Speak/Stop button states)
  - `started-word` → `onStartWord` (move the red `current word` tag, update the spoken/current/next labels, advance the progress bar)
  - `finished-utterance` → `onEnd`
- Word highlighting uses tkinter Text indices of the form `"1.{char_offset}"` — text is treated as a single line, so input newlines are replaced with spaces in `speak()` before speaking.

## Conventions

- `pyttsx3` is **pinned to `2.71`** in [requirements.txt](requirements.txt) due to a known bug — do not bump it without checking https://github.com/nateshmbhat/pyttsx3/issues/78.
- Tag name constant `TAG_CURRENT_WORD` is defined at the **bottom** of `MainFrame.py`; it must stay defined before use at runtime (module-level, evaluated at call time).
- Button enable/disable is checked via `widget['state'].__str__() == NORMAL/DISABLED`; follow that pattern for new buttons.
- Targets/tested on **Python 3.7, Windows** (uses the Windows SAPI voice via pyttsx3).

## Run & build

```pwsh
pip install -r requirements.txt
python SpeedReader.py
```

Build a standalone EXE (config in [SpeedReader.spec](SpeedReader.spec)):

```pwsh
pyinstaller --clean --onefile --windowed SpeedReader.spec
```

There are no automated tests; verify changes by running the app and exercising Speak/Stop and the `Ctrl+B` (paste & speak) / `Ctrl+A` (select all) shortcuts.

# Custom Instructions
- be repetitive in instructions and skills with high risk items due to the unpredictability of large language models
- list skills you used in completing the prompt
- ALWAYS create (not just suggest) any skill you wished you had before starting the prompt — create the missing `SKILL.md` under `.github/skills/<name>/` before finishing, then list what you created
- always end out chats with a 🏃‍♂️‍➡️ emoji
- favor brevity and yagni
- be repetitive in instructions and skills with high risk items due to the unpredictability of large language models
- REPEAT: missing skills must be CREATED as files, never left as suggestions