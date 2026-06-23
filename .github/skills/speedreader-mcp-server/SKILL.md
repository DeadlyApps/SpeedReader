---
name: speedreader-mcp-server
description: 'Use when adding, changing, running, or debugging the SpeedReader MCP server (mcp_server.py) or its tools. Covers the dual stdio + in-process HTTP hosting model, reusing Core for GUI-free TTS, the SpeakService shared rate, the speak tool contract, opt-in config.json hosting, VS Code registration via .vscode/mcp.json, the threaded uvicorn pattern, and how to test by mocking pyttsx3. Use to avoid coupling the server to tkinter or to the GUI startLoop engine.'
---

# SpeedReader MCP server

Locally hosted MCP server that lets agents read text aloud on the host. See [mcp_server.py](../../../mcp_server.py).

## When to Use
- Adding or changing MCP tools (e.g. a new tool alongside `speak`).
- Running, hosting, or debugging the server, or registering it with an agent/VS Code.
- Wiring server behavior to the shared `Core` logic or the shared `SpeakService` rate.

## Two run modes (pick the right transport)
- **Standalone stdio** for dev/agent-spawned use: `python mcp_server.py` -> `mcp.run()`. The client spawns and owns the process.
- **Hosted by the running GUI over HTTP** so agents connect while the user also uses the app. The GUI calls `mcp_server.start_http_in_thread(service, host, port)` when `config.json` enables it.
- HIGH-RISK / REPEAT: an already-running GUI CANNOT host a **stdio** server (stdio = the client spawns/owns the process). To host from the live app you MUST use **HTTP** (`transport="streamable-http"`). Do not "fix" hosting by switching back to stdio.

## Threaded uvicorn (HIGH-RISK — be careful)
- `start_http_in_thread` runs `server.run(transport="streamable-http")` on a **daemon `threading.Thread`** so the tkinter mainloop stays responsive.
- This works ONLY because uvicorn skips installing signal handlers when not on the main thread. REPEAT: keep it on a non-main daemon thread; never run HTTP on the main thread alongside tkinter.
- Default bind is `127.0.0.1:8765` (loopback only). REPEAT: keep it loopback unless the user explicitly asks to expose it.

## Shared rate (use the UI's WPM)
- Both the GUI host and the server speak through a shared `Core.speak_service.SpeakService`. The GUI keeps `service.set_rate(...)` in sync with the speed entry; the `speak` tool reads that rate when `rate` is omitted.
- REPEAT: the `speak` tool's `rate` defaults to `None` = "use the current UI rate". Do not hard-code a default WPM in the tool.
- The int read/write is atomic (GIL), so reading `service.rate` from the server thread is safe. Do NOT read tkinter widgets from the server thread — tkinter is not thread-safe; always go through `SpeakService`.

## Architecture (do NOT re-couple to the GUI)
- The server MUST reuse [Core/](../../../Core/) — never import tkinter or the GUI. Text is normalized with `Core.text_processing.preprocess_text` (done inside `SpeakService.speak`).
- Speech uses **`Core.speech.speak_blocking`** (a fresh engine + `runAndWait()` per call), NOT the GUI's long-lived `startLoop` engine in `Core/speech_engine.py`. REPEAT: do not call `startLoop()` from the server — that is the GUI callback model and will hang a headless request.

## Tool contract
- `speak(text: str, rate: int | None = None) -> str` reads text aloud (UI rate when `rate` is omitted) and returns a short confirmation. Keep tool signatures typed and docstring'd — FastMCP turns the docstring/types into the tool schema agents see.

## Config (opt-in hosting)
- Hosting is OFF by default. `Core.config.load_mcp_config()` reads `config.json` (or `$SPEEDREADER_CONFIG`): `{"mcp": {"enabled": bool, "host": str, "port": int}}`.
- The controller lazy-imports `mcp_server` only when `enabled` is true, so the GUI does not hard-require the `mcp` package unless hosting is on. REPEAT: keep that import lazy.

## Registration
- VS Code connects via [.vscode/mcp.json](../../../.vscode/mcp.json) (`servers.speedreader`, type `http`, url `http://127.0.0.1:8765/mcp`). The SpeedReader UI must be running with hosting enabled for VS Code to reach it. Update that file if the host/port changes.

## Testing (mock the engine, not the library)
- Unit test `SpeakService` by injecting a fake `speak_fn` and asserting the rate used + preprocessed text (see [tests/test_speak_service.py](../../../tests/test_speak_service.py)). REPEAT: do not exercise real pyttsx3 or audio.
- Unit test config loading with a temp file (see [tests/test_config.py](../../../tests/test_config.py)).
- Smoke-check registration without speaking:
  ```pwsh
  .\.venv\Scripts\python.exe -c "import asyncio, mcp_server; print([t.name for t in asyncio.run(mcp_server.mcp.list_tools())])"
  ```
- Smoke-check HTTP hosting binds (daemon thread dies with the process):
  ```pwsh
  .\.venv\Scripts\python.exe -c "import socket,time; from Core.speak_service import SpeakService; import mcp_server; mcp_server.start_http_in_thread(SpeakService(speak_fn=lambda *a: None)); time.sleep(2); s=socket.create_connection(('127.0.0.1',8765),1); s.close(); print('listening')"
  ```
- Run the suite: `python -m pytest -q`.
