import json
import os
from dataclasses import dataclass, field


@dataclass
class McpConfig:
    """User configuration for hosting the MCP server from the running app."""

    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 8765
    voices: list = field(default_factory=list)  # enabled voice IDs; empty = all


def load_mcp_config(path=None):
    """Load MCP hosting config from a JSON file.

    Lookup order: explicit ``path`` arg, then the ``SPEEDREADER_CONFIG``
    environment variable, then ``config.json`` in the working directory. Missing
    file or keys fall back to the (disabled) defaults, so hosting is strictly
    opt-in.

    The JSON may be nested under an ``"mcp"`` key or flat:
        {"mcp": {"enabled": true, "host": "127.0.0.1", "port": 8765}}
    """
    path = path or os.environ.get("SPEEDREADER_CONFIG") or "config.json"
    cfg = McpConfig()
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle) or {}
        mcp = data.get("mcp", data)
        if "enabled" in mcp:
            cfg.enabled = bool(mcp["enabled"])
        if "host" in mcp:
            cfg.host = str(mcp["host"])
        if "port" in mcp:
            cfg.port = int(mcp["port"])
        if "voices" in mcp and isinstance(mcp["voices"], list):
            cfg.voices = [str(v) for v in mcp["voices"]]
    return cfg


def _update_mcp_config(updates, path=None):
    """Merge ``updates`` into the ``mcp`` section of the config file.

    Preserves any existing config and other keys. Returns the resolved path.
    """
    path = path or os.environ.get("SPEEDREADER_CONFIG") or "config.json"
    data = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle) or {}
    data.setdefault("mcp", {})
    data["mcp"].update(updates)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=4)
    return path


def save_enabled_voices(voice_ids, path=None):
    """Persist the set of MCP-enabled voice IDs to the config file.

    Preserves any existing config; writes ``mcp.voices``. Used by the GUI's
    Voice Settings dialog.
    """
    return _update_mcp_config({"voices": list(voice_ids)}, path=path)


def save_mcp_port(port, path=None):
    """Persist the MCP hosting port so it survives across sessions.

    Preserves any existing config; writes ``mcp.port``. Used by the GUI when the
    user changes the server port and restarts the server.
    """
    return _update_mcp_config({"port": int(port)}, path=path)
