class SpeechEngine:
    """GUI-free wrapper around the pyttsx3 engine lifecycle.

    The engine is initialized once and reused: the first ``speak`` connects the
    callbacks and starts the event loop, while later calls only update the rate
    and queue more speech. The engine is never re-initialized and
    ``startLoop()`` is never called twice.

    ``init`` is injectable so the lifecycle can be unit tested without pyttsx3.
    """

    def __init__(self, on_start=None, on_word=None, on_end=None, init=None):
        if init is None:
            import pyttsx3
            init = pyttsx3.init
        self._init = init
        self._on_start = on_start
        self._on_word = on_word
        self._on_end = on_end
        self.engine = None

    def speak(self, text, rate):
        if self.engine is None:
            self.engine = self._init()
            self.engine.setProperty('rate', rate)
            self.engine.connect('started-utterance', self._on_start)
            self.engine.connect('started-word', self._on_word)
            self.engine.connect('finished-utterance', self._on_end)
            self.engine.say(text)
            self.engine.startLoop()
        else:
            self.engine.setProperty('rate', rate)
            self.engine.say(text)

    def stop(self):
        if self.engine is not None:
            self.engine.stop()
