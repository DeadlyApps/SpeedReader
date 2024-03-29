from tkinter import Tk
from tkinter.constants import N, S, E, W
from Frames.MainFrame import MainFrame


class SpeedReaderController(Tk):
    def __init__(self):
        Tk.__init__(self)
        self.title("Speed Reader")
        main_frame = MainFrame(master=self)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        main_frame.grid(padx=50, pady=50, sticky=(N, S, E, W))
