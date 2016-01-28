from Tkconstants import N, S, E, W
from Tkinter import Tk

from Frames.MainFrame import MainFrame


class SpeedReaderController(Tk):
    def __init__(self):
        Tk.__init__(self)
        main_frame = MainFrame()
        main_frame.grid(padx=50, pady=50, sticky=(N, S, E, W))