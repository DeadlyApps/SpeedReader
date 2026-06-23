import threading


class SpeechEngine:
    """GUI-free wrapper around the pyttsx3 engine lifecycle.

    The engine is created once and reused. Creating the engine (and connecting
    callbacks) is separate from starting the run loop: ``get_voices`` can create
    it early to populate a voice picker, and the loop is started exactly once by
    ``ensure_loop`` (never by ``speak``). pyttsx3 allows only one run loop per
    process, so ``ensure_loop`` must be running before any ``speak`` and is
    primed on a daemon thread at startup.

    ``speak`` is serialized: each utterance applies the rate and (optional)
    per-utterance voice, then waits for ``finished-utterance`` before the next
    one runs. This is required because pyttsx3 applies properties at processing
    time, so different agents' voices would otherwise bleed across queued
    utterances. Callers run ``speak`` on a worker/daemon thread, never the
    tkinter main thread.

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
        self._speak_lock = threading.RLock()
        self._done = threading.Event()

    def _ensure_engine(self):
        if self.engine is None:
            self.engine = self._init()
            self.engine.connect('started-utterance', self._on_start)
            self.engine.connect('started-word', self._on_word)
            self.engine.connect('finished-utterance', self._on_end)
            self.engine.connect('finished-utterance', self._mark_done)
        return self.engine

    def _mark_done(self, name, completed):
        self._done.set()

    def _apply_properties(self, rate, voice):
        self.engine.setProperty('rate', rate)
        chosen = voice if voice is not None else self._voice
        if chosen is not None:
            self.engine.setProperty('voice', chosen)

    def speak(self, text, rate, voice=None, block=True):
        """Speak one utterance, optionally with a per-call ``voice`` id.

        Serialized via a lock; when ``block`` (default) it waits for the
        utterance to finish so the next speaker's voice cannot bleed in. Run on
        a daemon/worker thread — never the tkinter main thread.
        """
        with self._speak_lock:
            engine = self._ensure_engine()
            self._apply_properties(rate, voice)
            self._done.clear()
            engine.say(text)
            if block:
                self._done.wait(timeout=600)

    def ensure_loop(self, rate):
        """Start the engine + run loop once WITHOUT speaking.

        ``startLoop`` blocks, so call this on a daemon thread. No-op if the loop
        is already running.
        """
        engine = self._ensure_engine()
        if not self._started:
            self._apply_properties(rate, None)
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
        """Select the default voice used when ``speak`` is called without one."""
        self._voice = voice_id
        if self.engine is not None:
            self.engine.setProperty('voice', voice_id)

    def stop(self):
        if self.engine is not None:
            self.engine.stop()
