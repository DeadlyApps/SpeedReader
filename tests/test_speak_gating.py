import asyncio
from unittest.mock import MagicMock

import mcp_server


class _FakeRegistry:
    def resolve_for_speak(self, agent=None, voice=None):
        return None


def _build(pause, active):
    service = MagicMock()
    service.speak.return_value = 500
    server, _, _ = mcp_server.build_mcp(
        service=service, registry=_FakeRegistry(),
        pause_when_mic_in_use=pause, call_active=lambda: active)
    return server, service


def _call_speak(server, text="hi"):
    return asyncio.run(server.call_tool("speak", {"text": text}))


def test_speak_skipped_when_call_active_and_pause_enabled():
    server, service = _build(pause=True, active=True)
    _call_speak(server)
    service.speak.assert_not_called()


def test_speak_runs_when_call_active_but_pause_disabled():
    server, service = _build(pause=False, active=True)
    _call_speak(server)
    service.speak.assert_called_once()


def test_speak_runs_when_pause_enabled_but_no_call():
    server, service = _build(pause=True, active=False)
    _call_speak(server)
    service.speak.assert_called_once()
