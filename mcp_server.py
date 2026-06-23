"""Locally hosted MCP server exposing SpeedReader's text-to-speech.

Two ways to run:

* **Standalone (stdio)** for development/agent-spawned use: ``python mcp_server.py``.
* **Hosted by the running GUI (HTTP)** so external agents can connect while the
  user also uses the app: the GUI calls :func:`start_http_in_thread` when the
  user has enabled it in ``config.json``. HTTP is required here because the app
  is already running — a stdio server would have to be spawned and owned by the
  client.

Either way the server reuses the GUI-free logic in ``Core`` and speaks at the
rate held by a shared :class:`~Core.speak_service.SpeakService` (kept in sync
with the UI), so agent speech matches the WPM the user has set.
"""
import threading

from mcp.server.fastmcp import FastMCP

from Core.speak_service import SpeakService


def build_mcp(service=None, host="127.0.0.1", port=8765):
    """Build a FastMCP server whose ``speak`` tool delegates to ``service``."""
    service = service or SpeakService()
    server = FastMCP("SpeedReader", host=host, port=port)

    @server.tool()
    def speak(text: str, rate: int | None = None) -> str:
        """Read text aloud on the host machine using the local TTS voice.

        Args:
            text: The text to speak. Newlines are collapsed to spaces and URLs
                are replaced with a ``[URL]`` placeholder before speaking.
            rate: Speech rate in words per minute. Omit to use the rate
                currently set in the SpeedReader UI.

        Returns:
            A short confirmation of what was spoken.
        """
        used = service.speak(text, rate)
        return "Spoke {} characters at {} WPM.".format(len(text), used)

    return server, service


def start_http_in_thread(service, host="127.0.0.1", port=8765):
    """Host the MCP server over HTTP in a daemon thread (for the running GUI).

    uvicorn skips signal-handler installation off the main thread, so this is
    safe to run alongside the tkinter mainloop. Returns the started thread.
    """
    server, _ = build_mcp(service, host=host, port=port)
    thread = threading.Thread(
        target=lambda: server.run(transport="streamable-http"),
        name="speedreader-mcp",
        daemon=True,
    )
    thread.start()
    return thread


# Module-level server for the standalone stdio path (and import smoke tests).
mcp, _service = build_mcp()


def main():
    mcp.run()


if __name__ == "__main__":
    main()
