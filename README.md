# SpeedReader
Python based tool to use text to speech to read books or study material quickly.

# History
In college my now father in law was using a text to speech program and talking about how he can listen to books at 500 WPM and recommended it to me. It was a pivotal point in my education because I realized I could listen & read a document at 500 words per minute and internalize the information. I began to receive better grades and was able to get ‘A’ letter grades on tests composed of 3 months of materials by listening for 2 hours. I later wrote a speed reader for myself that I used for 10 years and now I felt like it was time to write an updated version in python. I suggest trying it at low speeds first, then increasing the speed as you feel comfortable. Start at 200, and increment by 25 each time you use it until you find that your level of understanding is decreasing then take it slower till you reach 500 WPM. 

I believe if you are an auditory learning this tool can be massively helpful to you.

# Setup
## Run Locally Setup
Tested with Python 3.14 (originally developed on 3.7)

install requirements.txt
pyttsx3==2.71 due to a bug detailed here: https://github.com/nateshmbhat/pyttsx3/issues/78

## Controls
- **Speed** — words per minute (start low, e.g. 200, and work up to 500).
- **Voice** — pick from the text-to-speech voices installed on your system; the choice applies to both your reading and any AI agent speaking through the MCP server.
- **Voice Settings…** — choose which system voices agents are allowed to use (see below). All voices are enabled by default.
- **Server port** + **Restart Server** — change the port the MCP server listens on and restart it on the new port without closing the app. The new port is saved to `config.json` (`mcp.port`) so it sticks across sessions. Only active when MCP hosting is enabled (see below).
- Shortcuts: `Ctrl+B` paste & speak, `Ctrl+A` select all.

## MCP server (let AI agents speak through SpeedReader)
SpeedReader ships a [Model Context Protocol](https://modelcontextprotocol.io) server so an AI agent (e.g. in VS Code) can read text aloud on your machine. It exposes these tools:

- `speak(text, agent?, voice?, rate?)` — read text aloud. Omit `rate` to use the WPM set in the UI; pass the `agent` you claimed with (or an explicit `voice`) to speak in a specific voice, otherwise the UI's selected voice is used.
- `list_voices()` — list the voices the user enabled for agents, with claim status.
- `claim_voice(agent?, voice?)` — claim a voice to speak with (see *Per-agent voices* below).
- `release_voice(agent)` — release a claimed voice.

There are two ways to run it:

### Hosted by the running app (recommended)
This is the main use case: you keep SpeedReader open to read your own text, and agents speak through the very same window. It also means agent speech uses the **rate and voice currently set in the UI**.

1. Enable hosting in `config.json` at the repo root (hosting is **off by default**):

   ```json
   {
     "mcp": { "enabled": true, "host": "127.0.0.1", "port": 8765 }
   }
   ```

2. Start the app (`python SpeedReader.py`). It hosts the server over HTTP on `http://127.0.0.1:8765/mcp`, bound to localhost only. You can change the port at runtime with the **Server port** field + **Restart Server** button in the app — the new port is persisted to `config.json` for next launch (update your agent's URL to match).
3. Point your agent at it. In VS Code this is already wired in [.vscode/mcp.json](.vscode/mcp.json):

   ```json
   {
     "servers": {
       "speedreader": { "type": "http", "url": "http://127.0.0.1:8765/mcp" }
     }
   }
   ```

The agent now has the tools above. Omit `rate` to use the WPM set in the UI.

### Per-agent voices (multiple agents, multiple voices)
Use **Voice Settings…** in the app to enable/disable which installed voices agents may use; the choice is saved to `config.json` under `mcp.voices`. The voice you pick in the **Voice** dropdown is reserved for you — agents avoid it and claim the other voices first (unless it's the only enabled voice). The agent handshake is:

1. **(optional) discover** — `list_voices()` shows enabled voices and who holds each.
2. **reserve** — `claim_voice(agent="my-repo")` reserves a voice and returns it. Use a stable identifier (repo folder name or current task). Re-claiming returns the same voice.
3. **speak** — `speak("hello", agent="my-repo")` reads in your reserved voice.
4. **(optional) release** — `release_voice("my-repo")` frees it for others.

Rules:
- `speak` **requires a reservation**: calling it without a reserved `agent` (or an explicit `voice="..."`) is an error that tells the agent to `claim_voice` first — unless only one voice is enabled (then it's used automatically).
- Claims are exclusive while unused voices remain. When every assignable voice is taken, `claim_voice` **requires an `agent` label** and shares another *agent's* voice (never yours, unless yours is the only voice).

Speech is serialized so each utterance reads in its own voice without bleeding into the next.

### Pause agent speech while you're on a call
Set `mcp.pause_when_mic_in_use` to `true` in `config.json` to stop agents talking over you during calls:

```json
{
  "mcp": { "enabled": true, "pause_when_mic_in_use": true }
}
```

When enabled, the `speak` tool checks whether any app is currently using your microphone (a proxy for "in a call") and, if so, **skips** speaking and returns a message instead of playing audio. It's **off by default**, only affects agent/MCP speech (your own reading is never paused), and currently uses Windows microphone state — on other platforms it never pauses.

### Standalone (stdio)
For development or agent-spawned use without the GUI:

```pwsh
python mcp_server.py
```

## Convert to EXE
The build uses PyInstaller (see SpeedReader.spec). For background on the bootloader fix: https://github.com/pyinstaller/pyinstaller/issues/3268

pyinstaller --clean --onefile --windowed SpeedReader.spec
