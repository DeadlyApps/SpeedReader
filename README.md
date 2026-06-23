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

## MCP server (let AI agents speak through SpeedReader)
SpeedReader ships a [Model Context Protocol](https://modelcontextprotocol.io) server that exposes a single `speak` tool, so an AI agent (e.g. in VS Code) can read text aloud on your machine using the same voice — and the same words-per-minute — you've set in the app.

There are two ways to run it:

### Hosted by the running app (recommended)
This is the main use case: you keep SpeedReader open to read your own text, and agents speak through the very same window. It also means agent speech uses the **rate currently set in the UI**.

1. Enable hosting in `config.json` at the repo root (hosting is **off by default**):

   ```json
   {
     "mcp": { "enabled": true, "host": "127.0.0.1", "port": 8765 }
   }
   ```

2. Start the app (`python SpeedReader.py`). It hosts the server over HTTP on `http://127.0.0.1:8765/mcp`, bound to localhost only.
3. Point your agent at it. In VS Code this is already wired in [.vscode/mcp.json](.vscode/mcp.json):

   ```json
   {
     "servers": {
       "speedreader": { "type": "http", "url": "http://127.0.0.1:8765/mcp" }
     }
   }
   ```

The agent now has a `speak(text, rate?)` tool. Omit `rate` to use the WPM set in the UI.

### Standalone (stdio)
For development or agent-spawned use without the GUI:

```pwsh
python mcp_server.py
```

## Convert to EXE
The build uses PyInstaller (see SpeedReader.spec). For background on the bootloader fix: https://github.com/pyinstaller/pyinstaller/issues/3268

pyinstaller --clean --onefile --windowed SpeedReader.spec
