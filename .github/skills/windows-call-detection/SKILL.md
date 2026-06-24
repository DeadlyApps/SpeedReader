---
name: windows-call-detection
description: 'Use when detecting whether the user is in a call / on the microphone on Windows, or gating SpeedReader MCP agent speech on call state (Core/call_detection.py, mcp.pause_when_mic_in_use). Covers the CapabilityAccessManager registry mic-in-use signal, the recursive packaged/NonPackaged walk, fail-open-to-False behavior, and how the speak tool suppresses (not queues) speech during a call. Use to avoid blocking speech on detection errors or coupling detection to tkinter.'
---

# Windows call / microphone detection

GUI-free "is the user in a call?" detection, used to optionally pause MCP agent speech. See [Core/call_detection.py](../../../Core/call_detection.py).

## When to Use
- Detecting microphone-in-use / "in a call" state on Windows.
- Changing how the MCP `speak` tool gates on call state (`mcp.pause_when_mic_in_use`).
- Adding another detection signal or platform.

## The signal (mic-in-use via the registry)
- Windows records per-app microphone consent under `HKEY_CURRENT_USER\SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone`.
- Each app key has a `LastUsedTimeStop` QWORD (FILETIME). **`== 0` means the mic is currently in use**; a non-zero value is the time it stopped. We treat "any app holding the mic" as a proxy for "in a call".
- Packaged (Store) apps store the value directly on their key; **desktop apps live one level down under the `NonPackaged` container**. REPEAT: you MUST recurse into subkeys — checking only the top level misses desktop apps like Zoom/Teams classic.

## Implementation rules (HIGH-RISK — be repetitive)
- `microphone_in_use(scan=None)` is the public entry. `scan` is injectable for tests; default walks the registry.
- REPEAT: **fail open to `False`** — any error (non-Windows, missing key, access denied) returns `False` so a detection failure NEVER blocks/suppresses speech. Wrap the scan in a broad `except Exception`.
- REPEAT: non-Windows returns `False` early (`sys.platform`). Import `winreg` lazily inside the scan, never at module top (keeps `Core` importable/testable cross-platform).
- `_key_active(winreg, key)` is the recursive unit: check `LastUsedTimeStop == 0` on the key, then recurse into every subkey. Both `winreg` and the key are passed in so tests drive it with a fake winreg + nested-dict tree — NO real registry needed (see [tests/test_call_detection.py](../../../tests/test_call_detection.py)).

## Gating MCP speech (suppress, not queue)
- `mcp.pause_when_mic_in_use` (bool, default false) in `config.json` turns this on. It is threaded `config.pause_when_mic_in_use` → `start_http_in_thread` → `McpHost` → `build_mcp(pause_when_mic_in_use, call_active)`; `call_active` defaults to `microphone_in_use` and is injectable.
- In the `speak` tool: `if pause_when_mic_in_use and call_active(): return "Skipped..."` — REPEAT: it **suppresses and returns a message**, it does NOT queue/defer/wait for the call to end (waiting would block the agent's tool call). 
- REPEAT: gating lives ONLY in the MCP `speak` tool — it must NOT touch `SpeakService` or the GUI, so the user's own reading is never paused.
- Off by default; only affects agent/MCP speech.

## Testing
- Unit-test `_key_active` with a fake winreg backed by a nested dict (`values`/`subkeys`); cover packaged active, NonPackaged active, and all-stopped. Unit-test `microphone_in_use` with injected `scan` returning True/False and one that raises (asserts fail-open). See [tests/test_call_detection.py](../../../tests/test_call_detection.py).
- Test the gate via the MCP tool with a fake service + `call_active=lambda: True/False` (see [tests/test_speak_gating.py](../../../tests/test_speak_gating.py)); assert the service is/ isn't called. REPEAT: never touch the real registry or pyttsx3 in tests.
