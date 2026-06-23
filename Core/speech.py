def speak_blocking(text, rate, init=None):
    """Speak text aloud and block until finished (headless, no GUI).

    A fresh pyttsx3 engine is created per call and driven with ``runAndWait()``,
    which suits one-shot requests such as an MCP tool invocation (unlike the
    GUI's long-lived ``startLoop`` engine in ``speech_engine.py``). ``init`` is
    injectable so the lifecycle can be unit tested without pyttsx3.
    """
    if init is None:
        import pyttsx3
        init = pyttsx3.init
    engine = init()
    engine.setProperty('rate', rate)
    engine.say(text)
    engine.runAndWait()
