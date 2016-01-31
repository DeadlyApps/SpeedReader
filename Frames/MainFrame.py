import thread
import ttk
from Tkconstants import END, N, S, E, W, NORMAL, DISABLED, RIGHT, CENTER
from Tkinter import Text

import pyttsx


class MainFrame(ttk.Frame):
    def __init__(self, **kw):
        ttk.Frame.__init__(self, **kw)
        self.engine = None
        self.spoken_text = ''
        self.highlight_index1 = None
        self.highlight_index2 = None
        self.build_frame_content(kw)

    def build_frame_content(self, kw):

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=0)
        self.grid_columnconfigure(3, weight=1)

        row_index = 0
        self.grid_rowconfigure(row_index, weight=1)
        self.title = ttk.Label(self, font=("Georgia", "80"), justify=RIGHT, text="Speed Reader", anchor=CENTER)
        self.title.grid(row=row_index, column=0, columnspan=4, sticky=(N, W, E), pady=15)
        row_index += 1

        self.spoken_words = ttk.Label(self, font=("Georgia", "20"), justify=RIGHT, anchor=E)
        self.spoken_words.grid(row=row_index, column=0, columnspan=4, sticky=(W, E))
        row_index += 1

        self.current_word_label = ttk.Label(self, font=("Georgia", "120"), anchor=CENTER)
        self.current_word_label.grid(row=row_index, column=0, columnspan=4, sticky=(W, E))
        row_index += 1

        self.next_words = ttk.Label(self, font=("Georgia", "20"), anchor=W)
        self.next_words.grid(row=row_index, column=0, columnspan=4, sticky=(W, E))

        row_index += 1

        self.speed_label = ttk.Label(self, text="Speed: ")
        self.speed_label.grid(row=row_index, column=1, pady=10)
        self.speed_entry = ttk.Entry(self)
        self.speed_entry.insert(0, "500")
        self.speed_entry.grid(row=row_index, column=2, pady=10)
        row_index += 1

        self.grid_rowconfigure(row_index, weight=1)
        self.text_area = Text(self, height=5, width=1, font=("Georgia", "40"))
        self.text_area.insert(END, '')
        self.text_area.tag_config(TAG_CURRENT_WORD, foreground="red")
        self.text_area.grid(row=row_index, column=0, columnspan=4, sticky=(N, S, E, W))
        row_index += 1

        self.speak_button = ttk.Button(self, text="Speak")
        self.speak_button.grid(row=row_index, column=1, pady=10)
        self.speak_button['state'] = NORMAL
        self.speak_button.bind("<Button-1>", self.speak)

        self.stop_button = ttk.Button(self, text="Stop")
        self.stop_button.grid(row=row_index, column=2, pady=10)
        self.stop_button['state'] = DISABLED
        self.stop_button.bind("<Button-1>", self.stop)

    def stop(self, event):
        if self.stop_button['state'].__str__() == NORMAL:
            self.engine.stop()
            self.speak_button['state'] = NORMAL
            self.stop_button['state'] = DISABLED

    def onStart(self, name):
        self.speak_button['state'] = DISABLED
        self.stop_button['state'] = NORMAL
        print("onStart")

    def onWord(self, name, location, length):
        read_trail = 100
        left_index = location - read_trail
        if left_index < 0:
            left_index = 0

        self.spoken_words['text'] = self.spoken_text[left_index:location]
        self.current_word_label['text'] = self.spoken_text[location:location + length]
        self.next_words['text'] = self.spoken_text[location + length:location + length + read_trail]
        if self.highlight_index1 is not None:
            self.text_area.tag_remove(TAG_CURRENT_WORD, self.highlight_index1, self.highlight_index2)
        self.highlight_index1 = "1.{}".format(location)
        self.highlight_index2 = "1.{}".format(location + length)
        self.text_area.see(self.highlight_index1)
        self.text_area.tag_add(TAG_CURRENT_WORD, self.highlight_index1, self.highlight_index2)

    def onEnd(self, name, completed):
        self.speak_button['state'] = NORMAL
        self.stop_button['state'] = DISABLED
        print("onEnd")

    def speak(self, event):
        if self.speak_button['state'].__str__() == NORMAL:
            self.spoken_text = self.text_area.get("1.0", END).replace('\n', ' ')
            self.text_area.delete("1.0", END)
            self.text_area.insert(END, self.spoken_text)

            speech_speed = int(self.speed_entry.get())
            print("starting thread")
            thread.start_new_thread(self.speak_on_thread, (speech_speed, self.spoken_text))

    def speak_on_thread(self, speech_speed, spoken_text):

        if self.engine is None:
            self.engine = pyttsx.init()
            self.engine.setProperty('rate', speech_speed)
            self.engine.connect('started-utterance', self.onStart)
            self.engine.connect('started-word', self.onWord)
            self.engine.connect('finished-utterance', self.onEnd)
            self.engine.say(spoken_text)
            self.engine.startLoop()
        else:
            self.engine.setProperty('rate', speech_speed)
            self.engine.say(spoken_text)

        print("thread finished")


TAG_CURRENT_WORD = "current word"
