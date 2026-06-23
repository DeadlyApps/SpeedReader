from tkinter import Tk
from tkinter.constants import N, S, E, W
import threading
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
        config = load_mcp_config()
        if not config.enabled:
            return
        # Start the shared engine's single run loop up front (on a daemon thread,
        # since startLoop blocks) so agents can speak even before the user does.
        threading.Thread(
            target=main_frame.speech.ensure_loop,
            args=(main_frame.speak_service.rate,),
            daemon=True,
        ).start()
        import mcp_server
        mcp_server.start_http_in_thread(main_frame.speak_service, config.host, config.port)
