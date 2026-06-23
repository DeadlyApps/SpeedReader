class SpeechEngine:
    """GUI-free wrapper around the pyttsx3 engine lifecycle.

    The engine is created once and reused. Creating the engine (and connecting
    callbacks) is separated from starting the run loop so voices can be
    enumerated before any speech. ``startLoop()`` is started at most once,
    guarded by ``_started``, and never called twice. The selected voice (if any)
    is applied on every utterance so both the GUI and the MCP server speak with
    it.

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
        self._started = False
        self._voice = None

    def _ensure_engine(self):
        if self.engine is None:
            self.engine = self._init()
            self.engine.connect('started-utterance', self._on_start)
            self.engine.connect('started-word', self._on_word)
            self.engine.connect('finished-utterance', self._on_end)
        return self.engine

    def _apply_properties(self, rate):
        self.engine.setProperty('rate', rate)
        if self._voice is not None:
            self.engine.setProperty('voice', self._voice)

    def speak(self, text, rate):
        engine = self._ensure_engine()
        self._apply_properties(rate)
        engine.say(text)
        if not self._started:
            self._started = True
            engine.startLoop()

    def ensure_loop(self, rate):
        """Start the engine + run loop once WITHOUT speaking.

        pyttsx3 allows only one run loop per process, so when speech is hosted
        in-process (e.g. the MCP server alongside the GUI) the loop must already
        be running before any ``say``. ``startLoop`` blocks, so call this on a
        daemon thread. No-op if the loop is already running.
        """
        engine = self._ensure_engine()
        if not self._started:
            self._apply_properties(rate)
            self._started = True
            engine.startLoop()

    def get_voices(self):
        """Return ``[(id, name), ...]`` for the voices installed on this system.

        Creates the engine if needed (without starting the run loop), so it is
        safe to call at startup to populate a voice picker.
        """
        engine = self._ensure_engine()
        return [(voice.id, voice.name) for voice in engine.getProperty('voices')]

    def set_voice(self, voice_id):
        """Select the voice used for subsequent speech (GUI and MCP)."""
        self._voice = voice_id
        if self.engine is not None:
            self.engine.setProperty('voice', voice_id)

    def stop(self):
        if self.engine is not None:
            self.engine.stop()
