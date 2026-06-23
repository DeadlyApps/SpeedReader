# SpeedReader — Agent Instructions

Desktop GUI app that uses text-to-speech to read pasted text aloud at high WPM, while highlighting the current word. Python + tkinter, packaged to a Windows EXE. See [README.md](README.md) for background and usage tips.

## Architecture

Thin MVC split — keep new UI logic in the frame, not in entry points:

- [SpeedReader.py](SpeedReader.py) — entry point. Instantiates the controller and runs `mainloop()`. Keep it minimal.
- [Controllers/SpeedReaderController.py](Controllers/SpeedReaderController.py) — subclass of `tkinter.Tk`. Owns the window (title, grid weights) and mounts `MainFrame`.
- [Frames/MainFrame.py](Frames/MainFrame.py) — subclass of `ttk.Frame`. Holds nearly all logic: widget layout (manual `grid` with `row_index` counter), TTS engine wiring, and key bindings.
- [Core/](Core/) — GUI-free, unit-tested logic shared by the GUI and the MCP server: text preprocessing/word-window ([Core/text_processing.py](Core/text_processing.py)), the GUI callback engine ([Core/speech_engine.py](Core/speech_engine.py)), the headless blocking speak ([Core/speech.py](Core/speech.py)), the shared-rate TTS entry point ([Core/speak_service.py](Core/speak_service.py)), microphone/"in a call" detection ([Core/call_detection.py](Core/call_detection.py)), and opt-in MCP hosting config ([Core/config.py](Core/config.py)). No tkinter/pyttsx3 imports leak into tests — `pyttsx3` is injected for mocking.
- [mcp_server.py](mcp_server.py) — locally hosted MCP server exposing a `speak` tool so agents can read text aloud on the host. Runs **stdio** standalone (`python mcp_server.py`) or is **hosted over HTTP in-process by the running GUI** (`start_http_in_thread`) when the user enables it. Reuses `Core`; VS Code connects via [.vscode/mcp.json](.vscode/mcp.json).


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
- Targets/tested on **Python 3.14, Windows** (uses the Windows SAPI voice via pyttsx3); originally developed on 3.7.

## Run & build

```pwsh
pip install -r requirements.txt
python SpeedReader.py
```

Run the MCP server so an agent can call the `speak` tool. Two modes:

- **Standalone (stdio)** for dev/agent-spawned use:

```pwsh
python mcp_server.py
```

- **Hosted in-process by the running GUI (HTTP)** so the user speaks text AND agents speak through the same app. Opt in via [config.json](config.json) (`{"mcp": {"enabled": true, "host": "127.0.0.1", "port": 8765}}`); the GUI then starts the server on a daemon thread at startup. Agent speech uses the **rate currently set in the UI** (shared via `SpeakService`). VS Code connects to the running app via [.vscode/mcp.json](.vscode/mcp.json) (`type: http`, `http://127.0.0.1:8765/mcp`). HIGH-RISK/REPEAT: hosting from the already-running GUI requires HTTP, not stdio, and the uvicorn server must run on a non-main daemon thread.

Build a standalone EXE (config in [SpeedReader.spec](SpeedReader.spec)):

```pwsh
pyinstaller --clean --onefile --windowed SpeedReader.spec
```

GUI-free logic lives in [Core/](Core/) so it can be unit tested (and is reused by the MCP server) without tkinter or audio. Run the tests with:

```pwsh
pip install -r requirements-dev.txt
python -m pytest -q
```

The tests mock `pyttsx3` (see [tests/test_speech_engine.py](tests/test_speech_engine.py)) — they cover our logic, not the external engine. The GUI still has no automated coverage; verify UI changes by running the app and exercising Speak/Stop and the `Ctrl+B` (paste & speak) / `Ctrl+A` (select all) shortcuts.

# Custom Instructions
- ALWAYS dogfood your own MCP server. Whenever you need to ask me a question or finish a task, use the MCP to read it out loud. If the MCP is not available, remind me to turn it on for dogfooding purposes.
- be repetitive in instructions and skills with high risk items due to the unpredictability of large language models
- list skills you used in completing the prompt
- ALWAYS create (not just suggest) any skill you wished you had before starting the prompt — create the missing `SKILL.md` under `.github/skills/<name>/` before finishing, then list what you created
- always end out chats with a 🏃‍♂️‍➡️ emoji
- favor brevity and yagni
- ALWAYS keep [README.md](README.md) up to date for GitHub users when behavior, setup, run/build steps, or user-facing features change (e.g. the MCP server, config, shortcuts) — update it in the same change, never defer it
- be repetitive in instructions and skills with high risk items due to the unpredictability of large language models
- REPEAT: missing skills must be CREATED as files, never left as suggestions
- REPEAT: user-facing changes are not done until [README.md](README.md) reflects them