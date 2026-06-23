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
from Core.voice_registry import VoiceRegistry


def build_mcp(service=None, registry=None, host="127.0.0.1", port=8765):
    """Build a FastMCP server whose tools delegate to ``service``/``registry``."""
    service = service or SpeakService()
    registry = registry if registry is not None else VoiceRegistry()
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
        chosen = registry.resolve_for_speak(agent=agent, voice=voice)
        used = service.speak(text, rate, voice=chosen)
        return "Spoke {} characters at {} WPM.".format(len(text), used)

    return server, service, registry


def start_http_in_thread(service, registry=None, host="127.0.0.1", port=8765):
    """Host the MCP server over HTTP in a daemon thread (for the running GUI).

    uvicorn skips signal-handler installation off the main thread, so this is
    safe to run alongside the tkinter mainloop. Returns the started thread.
    """
    server, _, _ = build_mcp(service, registry=registry, host=host, port=port)
    thread = threading.Thread(
        target=lambda: server.run(transport="streamable-http"),
        name="speedreader-mcp",
        daemon=True,
    )
    thread.start()
    return thread


# Module-level server for the standalone stdio path (and import smoke tests).
mcp, _service, _registry = build_mcp()


def main():
    mcp.run()


if __name__ == "__main__":
    main()
