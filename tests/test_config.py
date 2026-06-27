import json
import os

from Core.config import load_mcp_config, save_enabled_voices, McpConfig, save_media_pause_setting


def test_defaults_are_disabled_when_no_file(tmp_path):
    cfg = load_mcp_config(path=str(tmp_path / "does_not_exist.json"))
    assert cfg == McpConfig(enabled=False, host="127.0.0.1", port=8765)


def test_loads_nested_mcp_config(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"mcp": {"enabled": True, "host": "0.0.0.0", "port": 9000}}))
    cfg = load_mcp_config(path=str(path))
    assert cfg.enabled is True
    assert cfg.host == "0.0.0.0"
    assert cfg.port == 9000


def test_loads_flat_config_and_coerces_types(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"enabled": 1, "port": "8000"}))
    cfg = load_mcp_config(path=str(path))
    assert cfg.enabled is True
    assert cfg.port == 8000
    assert cfg.host == "127.0.0.1"  # untouched default


def test_env_var_is_used_when_path_not_given(tmp_path, monkeypatch):
    path = tmp_path / "env.json"
    path.write_text(json.dumps({"mcp": {"enabled": True}}))
    monkeypatch.setenv("SPEEDREADER_CONFIG", str(path))
    cfg = load_mcp_config()
    assert cfg.enabled is True


def test_loads_enabled_voices(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"mcp": {"voices": ["id-1", "id-2"]}}))
    cfg = load_mcp_config(path=str(path))
    assert cfg.voices == ["id-1", "id-2"]


def test_pause_when_mic_in_use_defaults_false_and_loads(tmp_path):
    assert load_mcp_config(path=str(tmp_path / "nope.json")).pause_when_mic_in_use is False
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"mcp": {"pause_when_mic_in_use": True}}))
    assert load_mcp_config(path=str(path)).pause_when_mic_in_use is True


def test_save_enabled_voices_preserves_existing_config(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"mcp": {"enabled": True, "port": 9000}}))

    save_enabled_voices(["id-1", "id-3"], path=str(path))

    data = json.loads(path.read_text())
    assert data["mcp"]["voices"] == ["id-1", "id-3"]
    assert data["mcp"]["enabled"] is True  # preserved
    assert data["mcp"]["port"] == 9000


def test_save_enabled_voices_creates_file_when_missing(tmp_path):
    path = tmp_path / "new.json"

    save_enabled_voices(["id-1"], path=str(path))

    data = json.loads(path.read_text())
    assert data["mcp"]["voices"] == ["id-1"]


def test_save_mcp_port_persists_and_preserves_config(tmp_path):
    path = tmp_path / "config.json"
    # Write initial state, ensuring 'port' is present for the assertion to pass
    initial_data = {"mcp": {"enabled": True, "voices": ["id-1"], "port": 9100}}
    path.write_text(json.dumps(initial_data))

    save_media_pause_setting(True, path=str(path))

    # Reload data to check for preservation of 'port' and addition of 'pause_media_when_speaking'
    data = json.loads(path.read_text())
    assert data["mcp"]["port"] == 9100  # Asserting preserved key
    assert data["mcp"]["enabled"] is True  # preserved
    assert data["mcp"]["voices"] == ["id-1"]  # preserved
    assert data["mcp"]["pause_media_when_speaking"] is True  # Asserting new key was added

    # round-trips through the loader
    assert load_mcp_config(path=str(path)).port == 9100
