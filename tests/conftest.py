"""Pytest configuration and shared fixtures."""
import pytest
import gc
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


# Configure pytest to handle tkinter properly
def pytest_configure(config):
    """Configure pytest for tkinter testing."""
    # Ensure tkinter doesn't cause issues in headless environments
    import os
    if 'DISPLAY' not in os.environ:
        os.environ['DISPLAY'] = ':0'


@pytest.fixture(scope="session", autouse=True)
def mock_pyttsx3():
    """Replace ``pyttsx3.init`` with a fast in-memory fake engine, session-wide.

    The real SAPI5 engine is a COM object: creating it, enumerating voices, and
    running ``startLoop`` per test is slow and emits 'run loop already started'
    warnings. Patching session-wide (not per test) also avoids a race where the
    ``prime_async`` daemon thread calls the real ``pyttsx3.init`` after a
    per-test patch exits (which raised ``SystemExit`` from a background thread).
    Tests assert tkinter widget and SpeechEngine *wiring* behavior, not actual
    speech, so a MagicMock engine suffices while real tkinter widgets stay intact.
    """
    import pyttsx3

    voices = [
        SimpleNamespace(id="voice-1", name="Voice One"),
        SimpleNamespace(id="voice-2", name="Voice Two"),
    ]

    def make_engine():
        engine = MagicMock()
        engine.getProperty.side_effect = (
            lambda prop: voices if prop == "voices" else MagicMock()
        )
        return engine

    with patch.object(pyttsx3, "init", side_effect=lambda *a, **k: make_engine()):
        yield


@pytest.fixture
def app():
    """Create a SpeedReaderController instance for testing.

    This fixture handles proper cleanup to avoid Tcl/Tk initialization issues.
    Includes retry logic for intermittent Tcl initialization failures on Windows.
    MCP hosting is stubbed out so the uvicorn server isn't started (and port
    8765 isn't bound) for every UI test — that startup dominated test runtime.
    """
    from Controllers.SpeedReaderController import SpeedReaderController

    with patch.object(SpeedReaderController, "maybe_host_mcp", lambda self, frame: None):
        yield from _make_controller(SpeedReaderController)


def _make_controller(SpeedReaderController):
    
    # Retry logic for intermittent Tcl initialization failures
    max_retries = 3
    last_error = None
    
    for attempt in range(max_retries):
        try:
            controller = SpeedReaderController()
            controller.update()  # Process any pending events
            yield controller
            try:
                controller.destroy()
            except Exception:
                pass
            gc.collect()  # Force garbage collection to clean up Tcl resources
            return
        except Exception as e:
            last_error = e
            gc.collect()
            time.sleep(0.1 * (attempt + 1))  # Increasing delay between retries
    
    # If all retries failed, raise the last error
    raise last_error


@pytest.fixture
def frame(app):
    """Get the MainFrame from the controller."""
    return app.winfo_children()[0]
