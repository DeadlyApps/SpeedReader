import threading


class SpeechEngine:
    """GUI-free wrapper around the pyttsx3 engine lifecycle.

    pyttsx3's SAPI5 engine is a COM object, so it MUST be created, pumped, and
    have its event callbacks delivered on the SAME thread. If the engine is
    created on one thread (e.g. the tkinter main thread) but ``startLoop`` pumps
    it on another, SAPI5's word/utterance callbacks fire with no Python thread
    state and crash the process (``PyEval_RestoreThread ... thread state NULL``).

    Therefore engine creation, voice enumeration, and ``startLoop`` all happen on
    a single dedicated daemon thread, started by ``prime_async``. Other threads
    (the tkinter UI, the MCP server) never create or touch the COM engine
    directly: ``get_voices`` waits for the cached voices and ``speak`` waits for
    the engine to be ready, then only queues an utterance.

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
        self._voices = []
        self._speak_lock = threading.RLock()
        self._done = threading.Event()
        self._engine_ready = threading.Event()
        self._voices_ready = threading.Event()
        self._loop_requested = False
        self._flush_generation = 0

    def _ensure_engine(self):
        """Create + wire the engine. MUST run on the dedicated loop thread.

        The tkinter UI and MCP server must NOT call this directly — they go
        through ``_await_engine``/``get_voices`` so the COM engine is only ever
        created on the thread that also pumps its run loop.
        """
        if self.engine is None:
            engine = self._init()
            engine.connect('started-utterance', self._on_start)
            engine.connect('started-word', self._on_word)
            engine.connect('finished-utterance', self._on_end)
            engine.connect('finished-utterance', self._mark_done)
            self.engine = engine
            self._engine_ready.set()
        return self.engine

    def _load_voices(self):
        """Enumerate installed voices into the cache (on the loop thread)."""
        engine = self._ensure_engine()
        self._voices = [(voice.id, voice.name) for voice in engine.getProperty('voices')]
        self._voices_ready.set()
        return self._voices

    def _mark_done(self, name, completed):
        self._done.set()

    def _apply_properties(self, rate, voice):
        self.engine.setProperty('rate', rate)
        chosen = voice if voice is not None else self._voice
        if chosen is not None:
            self.engine.setProperty('voice', chosen)

    def _await_engine(self):
        """Return the engine, waiting for the loop thread to build it.

        When the run loop has been primed (the normal app path), the engine is
        created on that thread, so foreign callers must wait for it rather than
        create their own COM instance on the wrong thread. Without a primed loop
        (headless/tests), fall back to building it inline.
        """
        if self._loop_requested:
            self._engine_ready.wait(timeout=30)
            return self.engine
        return self._ensure_engine()

    def flush(self):
        """Cancel queued utterances and interrupt the one being spoken now.

        Bumps the flush generation so any callers blocked waiting for the speak
        lock abort instead of speaking, then stops the engine to interrupt the
        current utterance. Used by the GUI 'barge in' (Ctrl+B) path. The MCP
        server never flushes, so agent utterances queue and play in order.
        """
        self._flush_generation += 1
        if self.engine is not None:
            try:
                self.engine.stop()
            except Exception:
                pass

    def speak(self, text, rate, voice=None, block=True, interrupt=False, name=None):
        """Speak one utterance, optionally with a per-call ``voice`` id.

        Serialized via a lock; when ``block`` (default) it waits for the
        utterance to finish so the next speaker's voice cannot bleed in. Run on
        a daemon/worker thread — never the tkinter main thread.

        When ``interrupt`` is set, the current utterance is stopped and any
        already-queued utterances are cancelled before this one speaks (the GUI
        Ctrl+B path). Calls left ``interrupt=False`` (e.g. the MCP server) queue
        normally and play in order.

        ``name`` is passed through to ``engine.say`` so it is echoed back to the
        started/word/finished callbacks; the GUI uses it to tag each utterance
        with a session id and ignore callbacks from an interrupted utterance
        that arrive after a new one has already started.
        """
        if interrupt:
            self.flush()
        my_generation = self._flush_generation
        with self._speak_lock:
            if self._flush_generation != my_generation:
                # A flush happened while this call waited in the queue — drop it.
                return
            engine = self._await_engine()
            self._apply_properties(rate, voice)
            self._done.clear()
            if name is None:
                engine.say(text)
            else:
                engine.say(text, name)
            if block:
                self._done.wait(timeout=600)

    def prime_async(self, rate):
        """Create the engine and start its run loop on a dedicated daemon thread.

        Call this once at startup BEFORE ``get_voices``/``speak``. The COM engine
        is created AND pumped on this one thread so its callbacks never fire on a
        thread without a Python thread state (which crashes the process).
        """
        self._loop_requested = True
        threading.Thread(target=self.ensure_loop, args=(rate,), daemon=True).start()

    def ensure_loop(self, rate):
        """Build the engine, cache voices, and start the run loop once.

        ``startLoop`` blocks, so this runs on the dedicated daemon thread spawned
        by ``prime_async``. No-op restart if the loop is already running.
        """
        self._loop_requested = True
        engine = self._ensure_engine()
        self._load_voices()
        if not self._started:
            self._apply_properties(rate, None)
            self._started = True
            engine.startLoop()

    def get_voices(self):
        """Return ``[(id, name), ...]`` for the voices installed on this system.

        Returns the voices enumerated on the loop thread (waiting for them when
        the loop has been primed), so the COM engine is never created on the
        calling thread.
        """
        if self._loop_requested:
            self._voices_ready.wait(timeout=30)
            return list(self._voices)
        return list(self._load_voices())

    def set_voice(self, voice_id):
        """Select the default voice used when ``speak`` is called without one.

        Store-only: the voice is applied per-utterance in ``_apply_properties``
        so the COM engine is never touched from the tkinter main thread.
        """
        self._voice = voice_id

    def stop(self):
        if self.engine is not None:
            self.engine.stop()
