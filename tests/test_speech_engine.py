from unittest.mock import MagicMock, call

from Core.speech_engine import SpeechEngine


def make_engine():
    fake_engine = MagicMock()
    init = MagicMock(return_value=fake_engine)
    speech = SpeechEngine(on_start='S', on_word='W', on_end='E', init=init)
    return speech, init, fake_engine


def test_first_speak_initializes_connects_and_starts_loop_once():
    speech, init, fake_engine = make_engine()

    speech.speak('hello', 500)

    init.assert_called_once_with()
    fake_engine.setProperty.assert_called_once_with('rate', 500)
    fake_engine.connect.assert_any_call('started-utterance', 'S')
    fake_engine.connect.assert_any_call('started-word', 'W')
    fake_engine.connect.assert_any_call('finished-utterance', 'E')
    fake_engine.say.assert_called_once_with('hello')
    fake_engine.startLoop.assert_called_once_with()


def test_second_speak_reuses_engine_without_reinit_or_second_startloop():
    speech, init, fake_engine = make_engine()

    speech.speak('first', 500)
    speech.speak('second', 300)

    init.assert_called_once()  # engine is not re-initialized
    fake_engine.startLoop.assert_called_once()  # loop is not started again
    assert fake_engine.setProperty.call_args_list == [call('rate', 500), call('rate', 300)]
    assert fake_engine.say.call_args_list == [call('first'), call('second')]


def test_stop_before_any_speak_is_a_noop():
    speech, init, fake_engine = make_engine()

    speech.stop()

    init.assert_not_called()
    fake_engine.stop.assert_not_called()


def test_stop_after_speak_stops_the_engine():
    speech, init, fake_engine = make_engine()

    speech.speak('hi', 500)
    speech.stop()

    fake_engine.stop.assert_called_once_with()
