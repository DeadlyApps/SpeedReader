from Tkconstants import N, S, E, W
from Tkinter import Tk

from Frames.MainFrame import MainFrame


class SpeedReaderController(Tk):
    def __init__(self):
        Tk.__init__(self)
        self.title("Speed Reader")
        main_frame = MainFrame()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        main_frame.grid(padx=50, pady=50, sticky=(N, S, E, W))