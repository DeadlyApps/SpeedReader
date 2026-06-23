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
- **Hosted by the running GUI over HTTP** so agents connect while the user also uses the app. The GUI calls `mcp_server.start_http_in_thread(service, registry, host, port)` (which returns a restartable `McpHost`) when `config.json` enables it.
- HIGH-RISK / REPEAT: an already-running GUI CANNOT host a **stdio** server (stdio = the client spawns/owns the process). To host from the live app you MUST use **HTTP** (`transport="streamable-http"`). Do not "fix" hosting by switching back to stdio.

## Threaded uvicorn (HIGH-RISK — be careful)
- `start_http_in_thread` returns an `McpHost` that serves the FastMCP ASGI app (`server.streamable_http_app()`) via a `uvicorn.Server` we own, on a **daemon `threading.Thread`** so the tkinter mainloop stays responsive.
- REPEAT: drive uvicorn ourselves (own the `uvicorn.Server`) instead of `FastMCP.run(...)` so we hold a `should_exit` handle and can **restart on a new port**. `FastMCP.run` gives no shutdown handle.
- This works ONLY because uvicorn skips installing signal handlers when not on the main thread. REPEAT: keep it on a non-main daemon thread; never run HTTP on the main thread alongside tkinter.
- Default bind is `127.0.0.1:8765` (loopback only). REPEAT: keep it loopback unless the user explicitly asks to expose it.

## Restartable host / runtime port change (McpHost)
- `McpHost(service, registry, host, port)` has `start()`, `stop()` (sets `server.should_exit=True` then joins the thread), `restart(port=, host=)` (stop then start), and `is_running()`.
- The GUI's **Server port** entry + **Restart Server** button call `main_frame.mcp_host.restart(port=...)`, then `Core.config.save_mcp_port(port)` persists it to `config.json` (`mcp.port`) for next launch.
- REPEAT: `stop()` must run off the tkinter main thread's event handler only briefly — it joins the daemon thread (graceful uvicorn shutdown releases the old port before the new bind). The controller stores the host as `main_frame.mcp_host`; if hosting is disabled it stays `None` and the Restart button is disabled.
- Tests mock `uvicorn.Config`/`uvicorn.Server` and `build_mcp` (see `tests/test_mcp_host.py`) so no real socket/network is needed to verify start/stop/restart orchestration.

## Shared rate (use the UI's WPM)
- Both the GUI host and the server speak through a shared `Core.speak_service.SpeakService`. The GUI keeps `service.set_rate(...)` in sync with the speed entry; the `speak` tool reads that rate when `rate` is omitted.
- REPEAT: the `speak` tool's `rate` defaults to `None` = "use the current UI rate". Do not hard-code a default WPM in the tool.
- The int read/write is atomic (GIL), so reading `service.rate` from the server thread is safe. Do NOT read tkinter widgets from the server thread — tkinter is not thread-safe; always go through `SpeakService`.

## Architecture (do NOT re-couple to the GUI)
- The server MUST reuse [Core/](../../../Core/) — never import tkinter or the GUI. Text is normalized with `Core.text_processing.preprocess_text` (done inside `SpeakService.speak`).
- `build_mcp(service, registry, host, port)` and `start_http_in_thread(service, registry, host, port)` take a `Core.voice_registry.VoiceRegistry` so the GUI and server share one claim state.
- Speech goes through whatever `speak_fn` the `SpeakService` was built with:
  - **Hosted by the GUI**: `speak_fn = MainFrame.speak_external`, which routes through the GUI's single long-lived `startLoop` engine (so the user and agents share one window/loop). REPEAT: when hosted, agent speech does NOT use `speak_blocking`.
  - **Standalone**: the default `speak_fn = Core.speech.speak_blocking` (a fresh engine + `runAndWait()` per call).
- REPEAT: never call `startLoop()` from the server module — that is the GUI callback model and would conflict with the single-loop-per-process rule.

## Tool contract
- `speak(text, agent=None, voice=None, rate=None) -> str`: reads text aloud (UI rate when `rate` omitted). Voice is resolved by `registry.resolve_for_speak(agent, voice)`: explicit `voice` (name/id) > the `agent`'s reserved voice. REPEAT: with >1 enabled voice and NO reserved `agent` and NO explicit `voice`, it RAISES a `ValueError` telling the agent to `claim_voice` first (the handshake is enforced, not silently defaulted). Sole enabled voice = used without a reservation; empty registry = engine default.
- `list_voices() -> list`: `[{id, name, claimed_by}]` for enabled voices (the user's reserved voice shows `"user"`).
- `claim_voice(agent=None, voice=None) -> dict`: reserves a voice; raises `ValueError` (surfaced to the agent) when voices are exhausted and no `agent` is given. See *Per-agent voices*.
- `release_voice(agent) -> str`: frees the agent's voice.
- Keep tool signatures typed and docstring'd — FastMCP turns the docstring/types into the tool schema agents see.

## Agentic handshake (the intended flow — be repetitive)
1. (optional) `list_voices()` to discover enabled voices + holders.
2. `claim_voice(agent="<repo folder or current task>")` to RESERVE a voice (idempotent; returns `{id, name, shared, reused}`).
3. `speak(text, agent="<same id>")` to read in that reserved voice.
4. (optional) `release_voice(agent)` when done to free the pool.
- REPEAT: `speak` enforces step 2 — without a reservation (or explicit `voice`) it errors with guidance. Escape hatches: explicit `voice="..."` for one-offs, and a single enabled voice needs no reservation.

## Per-agent voices (claim/exhaustion model — HIGH-RISK, be repetitive)
- `Core.voice_registry.VoiceRegistry` (GUI-free, thread-safe) tracks enabled voices + claims. The user enables voices in the GUI Voice Settings; agents claim them via MCP.
- The GUI reserves the user's dropdown voice via `registry.set_user_voice(...)` (at startup and on dropdown change). Agents AVOID the user's reserved voice and claim other voices first. REPEAT: the user's voice is handed to an agent ONLY when it is the sole enabled voice (`only_voice`).
- Claims are EXCLUSIVE while unused (non-user) voices remain. `claim_voice()` hands out a free one.
- When ALL assignable voices are taken, `claim_voice()` WITHOUT an `agent` label raises `ValueError` instructing the agent to retry with an `agent` (repo folder name or current task). REPEAT: the agent label is REQUIRED only on reuse/exhaustion, optional before that.
- Reuse shares another *agent's* voice (least-shared), NEVER the user's voice — unless the user's voice is the only enabled voice. REPEAT: never auto-assign the user's reserved voice while other voices exist.
- A named agent's claim is idempotent (same agent → same voice). `set_enabled(...)` drops claims for voices no longer enabled and clears the user reservation if its voice was disabled.
- Per-utterance voice relies on the engine SERIALIZING speech (see the `tkinter-tts-patterns` skill): each utterance applies its voice and waits for `finished-utterance` so voices don't bleed. REPEAT: do not remove the serialization or per-utterance voices break.

## Config (opt-in hosting)
- Hosting is OFF by default. `Core.config.load_mcp_config()` reads `config.json` (or `$SPEEDREADER_CONFIG`): `{"mcp": {"enabled": bool, "host": str, "port": int, "voices": [ids]}}`.
- `mcp.voices` is the list of voice IDs enabled for agents (empty/absent = all voices enabled). The GUI's Voice Settings dialog writes it via `Core.config.save_enabled_voices(ids)`. REPEAT: empty list means "all enabled", so the registry is built from all system voices when no voices are configured.
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
