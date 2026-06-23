from tkinter import Tk
from tkinter.constants import N, S, E, W
from Frames.MainFrame import MainFrame
from Core.config import load_mcp_config


class SpeedReaderController(Tk):
    def __init__(self):
        Tk.__init__(self)
        self.title("Speed Reader")
        main_frame = MainFrame(master=self)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        main_frame.grid(padx=50, pady=50, sticky=(N, S, E, W))
        self.maybe_host_mcp(main_frame)

    def maybe_host_mcp(self, main_frame):
        # Host the MCP server in-process only if the user opted in via config.
        # Imported lazily so the GUI doesn't require the mcp package otherwise.
        # MainFrame already primes the shared engine's single run loop, so agents
        # can speak as soon as the server is up.
        config = load_mcp_config()
        if not config.enabled:
            return
        import mcp_server
        mcp_server.start_http_in_thread(
            main_frame.speak_service, main_frame.voice_registry,
            config.host, config.port)
