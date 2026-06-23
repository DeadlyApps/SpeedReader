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

from Core.call_detection import microphone_in_use
from Core.config import load_mcp_config
from Core.speak_service import SpeakService
from Core.voice_registry import VoiceRegistry


def build_mcp(service=None, registry=None, host="127.0.0.1", port=8765,
              pause_when_mic_in_use=False, call_active=None):
    """Build a FastMCP server whose tools delegate to ``service``/``registry``.

    When ``pause_when_mic_in_use`` is true, the ``speak`` tool skips speaking
    while a call is detected (``call_active()`` — microphone in use by default)
    and returns a message instead, so agent speech never talks over the user.
    """
    service = service or SpeakService()
    registry = registry if registry is not None else VoiceRegistry()
    call_active = call_active or microphone_in_use
    server = FastMCP("SpeedReader", host=host, port=port)

    @server.tool()
    def list_voices() -> list:
        """List the voices the user has enabled for agents, with claim status.

        Returns a list of ``{id, name, claimed_by}`` so you can pick an unused
        voice to claim. ``claimed_by`` lists the agents currently using it.
        """
        return registry.status()

    @server.tool()
    def claim_voice(agent: str | None = None, voice: str | None = None) -> dict:
        """Claim a voice to speak with.

        While unused voices remain you may claim one (optionally requesting a
        specific ``voice`` by name or id); each is exclusive. Once every enabled
        voice is taken, you must pass an ``agent`` label to share one — use a
        stable identifier such as the repo folder name or your current task.

        Args:
            agent: Your identity (repo folder name or current task). Required to
                share a voice after all voices are claimed.
            voice: Optional specific voice (name or id) to request.

        Returns:
            ``{id, name, agent, shared, reused}`` for the claimed voice. Pass the
            same ``agent`` (or the returned voice) to ``speak``.
        """
        return registry.claim(agent=agent, voice=voice)

    @server.tool()
    def release_voice(agent: str) -> str:
        """Release the voice claimed by ``agent`` so others can use it."""
        released = registry.release(agent)
        return "Released voice for %s." % agent if released else "No voice was claimed by %s." % agent

    @server.tool()
    def speak(text: str, agent: str | None = None, voice: str | None = None,
              rate: int | None = None) -> str:
        """Read text aloud on the host machine using the local TTS voice.

        Reserve a voice first: call ``claim_voice(agent="<your repo folder or
        current task>")`` once, then pass that same ``agent`` here. Speaking
        without a reserved ``agent`` (or an explicit ``voice``) is an error when
        more than one voice is enabled.

        Args:
            text: The text to speak. Newlines are collapsed to spaces and URLs
                are replaced with a ``[URL]`` placeholder before speaking.
            agent: Your identity; resolves to the voice you reserved with
                ``claim_voice``.
            voice: Optional specific voice (name or id) to speak with, overriding
                the reservation.
            rate: Words per minute. Omit to use the rate set in the UI.

        Returns:
            A short confirmation of what was spoken.
        """
        if pause_when_mic_in_use and call_active():
            return "Skipped: a call is in progress (microphone in use); speech was not played."
        chosen = registry.resolve_for_speak(agent=agent, voice=voice)
        used = service.speak(text, rate, voice=chosen)
        return "Spoke {} characters at {} WPM.".format(len(text), used)

    return server, service, registry


def start_http_in_thread(service, registry=None, host="127.0.0.1", port=8765,
                         pause_when_mic_in_use=False):
    """Host the MCP server over HTTP in a daemon thread (for the running GUI).

    uvicorn skips signal-handler installation off the main thread, so this is
    safe to run alongside the tkinter mainloop. Returns a started :class:`McpHost`
    so the GUI can restart it on a new port.
    """
    host_obj = McpHost(service, registry=registry, host=host, port=port,
                       pause_when_mic_in_use=pause_when_mic_in_use)
    host_obj.start()
    return host_obj


class McpHost:
    """A restartable in-process HTTP MCP server running on a daemon thread.

    The GUI uses this to change the listening port at runtime: ``restart(port)``
    gracefully stops the current uvicorn server and binds the new port. We drive
    uvicorn ourselves (via the FastMCP ASGI app) instead of ``FastMCP.run`` so we
    hold a ``uvicorn.Server`` handle whose ``should_exit`` flag stops it cleanly.
    uvicorn only installs signal handlers on the main thread, so running on a
    daemon thread alongside the tkinter mainloop is safe.
    """

    def __init__(self, service, registry=None, host="127.0.0.1", port=8765,
                 pause_when_mic_in_use=False):
        self._service = service
        self._registry = registry
        self.host = host
        self.port = int(port)
        self.pause_when_mic_in_use = bool(pause_when_mic_in_use)
        self._server = None
        self._thread = None

    def is_running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        """Build the FastMCP app and serve it on a daemon thread."""
        import uvicorn

        server, _, _ = build_mcp(
            self._service, registry=self._registry, host=self.host, port=self.port,
            pause_when_mic_in_use=self.pause_when_mic_in_use)
        app = server.streamable_http_app()
        config = uvicorn.Config(app, host=self.host, port=self.port, log_level="warning")
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(
            target=self._server.run, name="speedreader-mcp", daemon=True)
        self._thread.start()
        return self._thread

    def stop(self, timeout=5):
        """Signal the running server to exit and wait for the thread to finish."""
        if self._server is not None:
            self._server.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=timeout)
        self._server = None
        self._thread = None

    def restart(self, port=None, host=None):
        """Stop the server and start it again, optionally on a new host/port."""
        if port is not None:
            self.port = int(port)
        if host is not None:
            self.host = host
        self.stop()
        return self.start()



# Module-level server for the standalone stdio path (and import smoke tests).
mcp, _service, _registry = build_mcp(pause_when_mic_in_use=load_mcp_config().pause_when_mic_in_use)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
