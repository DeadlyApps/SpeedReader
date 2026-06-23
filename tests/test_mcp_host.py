import time

import pytest

import mcp_server


class _FakeFastMCP:
    def streamable_http_app(self):
        return object()


class _FakeConfig:
    def __init__(self, app, host=None, port=None, log_level=None):
        self.app = app
        self.host = host
        self.port = port


class _FakeServer:
    instances = []

    def __init__(self, config):
        self.config = config
        self.should_exit = False
        self.started = False
        _FakeServer.instances.append(self)

    def run(self):
        self.started = True
        while not self.should_exit:
            time.sleep(0.005)


@pytest.fixture
def fake_uvicorn(monkeypatch):
    import uvicorn

    _FakeServer.instances = []
    monkeypatch.setattr(uvicorn, "Config", _FakeConfig)
    monkeypatch.setattr(uvicorn, "Server", _FakeServer)
    monkeypatch.setattr(
        mcp_server, "build_mcp",
        lambda *a, **k: (_FakeFastMCP(), None, None))
    return _FakeServer


def test_start_runs_server_on_daemon_thread(fake_uvicorn):
    host = mcp_server.McpHost(service=None, port=9001)
    host.start()
    try:
        assert host.is_running()
        assert fake_uvicorn.instances[-1].config.port == 9001
    finally:
        host.stop()
    assert not host.is_running()


def test_restart_changes_port_and_stops_old_server(fake_uvicorn):
    host = mcp_server.McpHost(service=None, port=9001)
    host.start()
    first = fake_uvicorn.instances[-1]

    host.restart(port=9002)
    try:
        assert first.should_exit is True  # old server told to exit
        assert host.port == 9002
        assert fake_uvicorn.instances[-1].config.port == 9002
        assert host.is_running()
    finally:
        host.stop()


def test_stop_signals_exit_and_clears_state(fake_uvicorn):
    host = mcp_server.McpHost(service=None, port=9001)
    host.start()
    server = fake_uvicorn.instances[-1]

    host.stop()

    assert server.should_exit is True
    assert not host.is_running()
