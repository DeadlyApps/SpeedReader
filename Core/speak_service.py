from Core.speech import speak_blocking
from Core.text_processing import preprocess_text


class SpeakService:
    """Shared text-to-speech entry point for both the GUI host and MCP server.

    Holds the current speech rate so agent requests speak at the same words per
    minute the user has set in the UI. The GUI keeps ``rate`` in sync via
    ``set_rate``; the int read/write is atomic, so it is safe to read from the
    MCP server thread. ``speak_fn`` is injectable for testing.
    """

    def __init__(self, rate=500, speak_fn=None):
        self._rate = int(rate)
        self._speak_fn = speak_fn or speak_blocking

    @property
    def rate(self):
        return self._rate

    def set_rate(self, rate):
        self._rate = int(rate)

    def speak(self, text, rate=None):
        """Speak ``text`` aloud, using the UI rate unless ``rate`` overrides it.

        Returns the rate actually used.
        """
        used = self._rate if rate is None else int(rate)
        self._speak_fn(preprocess_text(text), used)
        return used
