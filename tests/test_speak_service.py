from unittest.mock import MagicMock

from Core.speak_service import SpeakService


def test_speak_uses_current_rate_and_preprocesses():
    speak_fn = MagicMock()
    service = SpeakService(rate=500, speak_fn=speak_fn)

    used = service.speak('hello\nworld')

    assert used == 500
    speak_fn.assert_called_once_with('hello world', 500, None)


def test_set_rate_changes_the_rate_used():
    speak_fn = MagicMock()
    service = SpeakService(rate=500, speak_fn=speak_fn)

    service.set_rate(300)
    used = service.speak('hi')

    assert used == 300
    speak_fn.assert_called_once_with('hi', 300, None)


def test_explicit_rate_overrides_ui_rate():
    speak_fn = MagicMock()
    service = SpeakService(rate=500, speak_fn=speak_fn)

    used = service.speak('hi', rate=120)

    assert used == 120
    speak_fn.assert_called_once_with('hi', 120, None)


def test_voice_is_passed_through_to_speak_fn():
    speak_fn = MagicMock()
    service = SpeakService(rate=500, speak_fn=speak_fn)

    service.speak('hi', voice='voice-id-1')

    speak_fn.assert_called_once_with('hi', 500, 'voice-id-1')
