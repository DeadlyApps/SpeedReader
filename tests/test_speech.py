from unittest.mock import MagicMock

from Core.speech import speak_blocking


def test_speak_blocking_initializes_sets_rate_says_and_waits():
    fake_engine = MagicMock()
    init = MagicMock(return_value=fake_engine)

    speak_blocking('hello world', 400, init=init)

    init.assert_called_once_with()
    fake_engine.setProperty.assert_called_once_with('rate', 400)
    fake_engine.say.assert_called_once_with('hello world')
    fake_engine.runAndWait.assert_called_once_with()


def test_speak_blocking_uses_a_fresh_engine_per_call():
    engines = [MagicMock(), MagicMock()]
    init = MagicMock(side_effect=engines)

    speak_blocking('first', 300, init=init)
    speak_blocking('second', 500, init=init)

    assert init.call_count == 2
    engines[0].say.assert_called_once_with('first')
    engines[1].say.assert_called_once_with('second')


def test_speak_blocking_sets_voice_when_given():
    fake_engine = MagicMock()
    init = MagicMock(return_value=fake_engine)

    speak_blocking('hi', 400, voice='voice-id-1', init=init)

    fake_engine.setProperty.assert_any_call('rate', 400)
    fake_engine.setProperty.assert_any_call('voice', 'voice-id-1')
    fake_engine.say.assert_called_once_with('hi')
    fake_engine.runAndWait.assert_called_once_with()
