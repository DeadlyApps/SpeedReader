import json
import os
from dataclasses import dataclass


@dataclass
class McpConfig:
    """User configuration for hosting the MCP server from the running app."""

    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 8765


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
    return cfg
