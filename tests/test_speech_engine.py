from unittest.mock import MagicMock, call

from Core.speech_engine import SpeechEngine


def make_engine():
    fake_engine = MagicMock()
    init = MagicMock(return_value=fake_engine)
    speech = SpeechEngine(on_start='S', on_word='W', on_end='E', init=init)
    return speech, init, fake_engine


def test_first_speak_initializes_connects_and_says_without_starting_loop():
    speech, init, fake_engine = make_engine()

    speech.speak('hello', 500, block=False)

    init.assert_called_once_with()
    fake_engine.setProperty.assert_called_once_with('rate', 500)
    fake_engine.connect.assert_any_call('started-utterance', 'S')
    fake_engine.connect.assert_any_call('started-word', 'W')
    fake_engine.connect.assert_any_call('finished-utterance', 'E')
    fake_engine.say.assert_called_once_with('hello')
    fake_engine.startLoop.assert_not_called()  # only ensure_loop starts the loop


def test_second_speak_reuses_engine_without_reinit():
    speech, init, fake_engine = make_engine()

    speech.speak('first', 500, block=False)
    speech.speak('second', 300, block=False)

    init.assert_called_once()  # engine is not re-initialized
    fake_engine.startLoop.assert_not_called()  # speak never starts the loop
    assert fake_engine.setProperty.call_args_list == [call('rate', 500), call('rate', 300)]
    assert fake_engine.say.call_args_list == [call('first'), call('second')]


def test_stop_before_any_speak_is_a_noop():
    speech, init, fake_engine = make_engine()

    speech.stop()

    init.assert_not_called()
    fake_engine.stop.assert_not_called()


def test_stop_after_speak_stops_the_engine():
    speech, init, fake_engine = make_engine()

    speech.speak('hi', 500, block=False)
    speech.stop()

    fake_engine.stop.assert_called_once_with()


def test_ensure_loop_starts_loop_once_without_speaking():
    speech, init, fake_engine = make_engine()
    fake_engine.getProperty.return_value = []

    speech.ensure_loop(500)

    init.assert_called_once_with()
    fake_engine.startLoop.assert_called_once_with()
    fake_engine.say.assert_not_called()


def test_speak_after_ensure_loop_reuses_engine_without_second_startloop():
    speech, init, fake_engine = make_engine()
    fake_engine.getProperty.return_value = []

    speech.ensure_loop(500)
    speech.speak('hello', 300, block=False)

    init.assert_called_once()  # engine is not re-initialized
    fake_engine.startLoop.assert_called_once()  # loop is not started again
    fake_engine.say.assert_called_once_with('hello')


def test_get_voices_returns_id_name_pairs_without_starting_loop():
    speech, init, fake_engine = make_engine()
    v1 = MagicMock(id='id-1')
    v1.name = 'Alice'
    v2 = MagicMock(id='id-2')
    v2.name = 'Bob'
    fake_engine.getProperty.return_value = [v1, v2]

    voices = speech.get_voices()

    assert voices == [('id-1', 'Alice'), ('id-2', 'Bob')]
    fake_engine.getProperty.assert_called_once_with('voices')
    fake_engine.startLoop.assert_not_called()


def test_set_voice_is_applied_on_each_utterance():
    speech, init, fake_engine = make_engine()

    speech.set_voice('id-2')
    speech.speak('hi', 400, block=False)

    fake_engine.setProperty.assert_any_call('voice', 'id-2')
    fake_engine.setProperty.assert_any_call('rate', 400)


def test_set_voice_before_engine_exists_applies_after_first_speak():
    speech, init, fake_engine = make_engine()

    speech.set_voice('id-9')  # engine not created yet
    speech.speak('hi', 500, block=False)

    fake_engine.setProperty.assert_any_call('voice', 'id-9')


def test_per_utterance_voice_overrides_default_voice():
    speech, init, fake_engine = make_engine()

    speech.set_voice('default-voice')
    speech.speak('hi', 500, voice='agent-voice', block=False)

    fake_engine.setProperty.assert_any_call('voice', 'agent-voice')


def test_primed_loop_owns_engine_creation_and_caches_voices():
    # Regression: the COM engine must be created on the loop thread only. Once
    # the loop is primed, get_voices/speak reuse that engine and never init a
    # second one on the calling thread (which would crash SAPI5 callbacks).
    speech, init, fake_engine = make_engine()
    v1 = MagicMock(id='id-1')
    v1.name = 'Alice'
    fake_engine.getProperty.return_value = [v1]

    speech.ensure_loop(500)  # stands in for the dedicated loop thread

    assert speech.get_voices() == [('id-1', 'Alice')]
    speech.speak('hi', 400, block=False)

    init.assert_called_once()  # no second engine created by get_voices/speak
    fake_engine.startLoop.assert_called_once()


