import threading
import webbrowser
import tkinter.ttk as ttk
from tkinter.constants import END, N, S, E, W, NORMAL, DISABLED, RIGHT, CENTER, SEL, INSERT, HORIZONTAL
from tkinter import Text, StringVar, BooleanVar, Toplevel
from Core.speech_engine import SpeechEngine
from Core.speak_service import SpeakService
from Core.voice_registry import VoiceRegistry
from Core.config import load_mcp_config, save_enabled_voices
from Core.text_processing import preprocess_text, word_window, highlight_indices

class MainFrame(ttk.Frame):
    def __init__(self, **kw):
        ttk.Frame.__init__(self, **kw)
        self.speech = SpeechEngine(self.onStart, self.onStartWord, self.onEnd)
        self.speak_service = SpeakService(rate=500, speak_fn=self.speak_external)
        self.voices = self.speech.get_voices()
        self.voice_registry = self._build_voice_registry()
        self.spoken_text = ''
        self.highlight_index1 = None
        self.highlight_index2 = None
        self.build_frame_content(kw)
        # Prime the single pyttsx3 run loop on a daemon thread so every speak
        # (GUI and MCP) only has to queue + wait, never start the loop.
        threading.Thread(target=self.speech.ensure_loop, args=(500,), daemon=True).start()

    def _build_voice_registry(self):
        """Build the agent voice registry from system voices + saved config.

        When the config lists no enabled voices, all system voices are enabled.
        """
        cfg = load_mcp_config()
        if cfg.voices:
            enabled = [(vid, name) for vid, name in self.voices if vid in cfg.voices]
        else:
            enabled = list(self.voices)
        return VoiceRegistry(enabled=enabled)

    def build_frame_content(self, kw):

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=0)
        self.grid_columnconfigure(3, weight=1)

        row_index = 0

        self.progress = ttk.Progressbar(self, orient=HORIZONTAL, mode="determinate")
        self.progress.grid(row=row_index, columnspan=4, sticky=(W, E))

        row_index += 1


        self.grid_rowconfigure(row_index, weight=1)
        self.title = ttk.Label(self, font=("Georgia", "80"), justify=RIGHT, text="Speed Reader", anchor=CENTER)
        self.title.grid(row=row_index, column=0, columnspan=4, sticky=(N, W, E), pady=15)
        row_index += 1


        self.spoken_words_container = ttk.Frame(self, height=40)
        self.spoken_words_container.grid(row=row_index, column=0, columnspan=4, sticky=(N, S, W, E))
        self.spoken_words_container.grid_propagate(False)  # lock height so text length never resizes the window
        self.spoken_words_container.grid_rowconfigure(0, weight=1)
        self.spoken_words_container.grid_columnconfigure(0, weight=1)
        self.spoken_words = ttk.Label(self.spoken_words_container, font=("Georgia", "20"), justify=RIGHT, anchor=E)
        self.spoken_words.grid(row=0, column=0, sticky=(N, S, W, E))
        row_index += 1

        self.current_word_container = ttk.Frame(self, height=180)
        self.current_word_container.grid(row=row_index, column=0, columnspan=4, sticky=(N, S, W, E))
        self.current_word_container.grid_propagate(False)  # lock height so word length never resizes the window
        self.current_word_container.grid_rowconfigure(0, weight=1)
        self.current_word_container.grid_columnconfigure(0, weight=1)
        self.current_word_label = ttk.Label(self.current_word_container, font=("Georgia", "120"), anchor=CENTER)
        self.current_word_label.grid(row=0, column=0, sticky=(N, S, W, E))
        row_index += 1

        self.next_words_container = ttk.Frame(self, height=40)
        self.next_words_container.grid(row=row_index, column=0, columnspan=4, sticky=(N, S, W, E))
        self.next_words_container.grid_propagate(False)  # lock height so text length never resizes the window
        self.next_words_container.grid_rowconfigure(0, weight=1)
        self.next_words_container.grid_columnconfigure(0, weight=1)
        self.next_words = ttk.Label(self.next_words_container, font=("Georgia", "20"), anchor=W)
        self.next_words.grid(row=0, column=0, sticky=(N, S, W, E))

        row_index += 1

        self.settings_frame = ttk.Frame(self)
        self.settings_frame.grid(row=row_index, column=0, columnspan=4, pady=10)

        self.speed_label = ttk.Label(self.settings_frame, text="Speed: ")
        self.speed_label.grid(row=0, column=0, padx=(0, 5))
        self.speed_var = StringVar(value="500")
        self.speed_entry = ttk.Entry(self.settings_frame, width=6, textvariable=self.speed_var)
        self.speed_entry.grid(row=0, column=1, padx=(0, 20))
        self.speed_var.trace_add("write", self.on_rate_changed)

        self.voice_label = ttk.Label(self.settings_frame, text="Voice: ")
        self.voice_label.grid(row=0, column=2, padx=(0, 5))
        self.voice_var = StringVar()
        self.voice_combo = ttk.Combobox(
            self.settings_frame, textvariable=self.voice_var, state="readonly",
            width=30, values=[name for _, name in self.voices])
        self.voice_combo.grid(row=0, column=3)
        self.voice_combo.bind("<<ComboboxSelected>>", self.on_voice_changed)
        if self.voices:
            self.voice_var.set(self.voices[0][1])
            self.speech.set_voice(self.voices[0][0])
            # Reserve the user's voice so agents claim the other voices first.
            self.voice_registry.set_user_voice(self.voices[0][0])

        self.voice_settings_button = ttk.Button(
            self.settings_frame, text="Voice Settings…", command=self.open_voice_settings)
        self.voice_settings_button.grid(row=0, column=4, padx=(20, 0))
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
        row_index += 1

        self.contribute_button = ttk.Button(self, text="Contribute", command=self.open_contribute)
        self.contribute_button.grid(row=row_index, column=0, columnspan=4, pady=10)

        self.text_area.bind("<Control-Key-a>", self.select_all_text)
        self.text_area.bind("<Control-Key-A>", self.select_all_text)

        self.master.bind("<Control-Key-b>", self.paste_and_speak)
        self.master.bind("<Control-Key-B>", self.paste_and_speak)

        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        self.stop(None)
        self.master.destroy()
        self.master.quit()

    def open_contribute(self):
        webbrowser.open_new_tab(GITHUB_URL)

    def open_voice_settings(self):
        """Open a dialog to enable/disable which system voices agents may use."""
        enabled_ids = {vid for vid, _ in self.voice_registry.enabled()}
        dialog = Toplevel(self)
        dialog.title("Voice Settings")
        dialog.transient(self.master)
        ttk.Label(
            dialog, text="Voices agents may use via the MCP server:"
        ).grid(row=0, column=0, sticky=W, padx=12, pady=(12, 6))

        vars_by_id = {}
        for i, (vid, name) in enumerate(self.voices, start=1):
            var = BooleanVar(value=vid in enabled_ids)
            vars_by_id[vid] = var
            ttk.Checkbutton(dialog, text=name, variable=var).grid(
                row=i, column=0, sticky=W, padx=18)

        def save():
            selected = [(vid, name) for vid, name in self.voices if vars_by_id[vid].get()]
            self.voice_registry.set_enabled(selected)
            save_enabled_voices([vid for vid, _ in selected])
            dialog.destroy()

        buttons = ttk.Frame(dialog)
        buttons.grid(row=len(self.voices) + 1, column=0, sticky=E, padx=12, pady=12)
        ttk.Button(buttons, text="Cancel", command=dialog.destroy).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(buttons, text="Save", command=save).grid(row=0, column=1)

    def on_rate_changed(self, *args):
        # Keep the shared service rate in sync so MCP agents speak at the UI rate.
        try:
            self.speak_service.set_rate(int(self.speed_var.get()))
        except ValueError:
            pass

    def on_voice_changed(self, event=None):
        # Apply the picked voice to the shared engine (used by the GUI and MCP).
        selected = self.voice_var.get()
        for voice_id, voice_name in self.voices:
            if voice_name == selected:
                self.speech.set_voice(voice_id)
                # Re-reserve the user's voice so agents keep avoiding it.
                self.voice_registry.set_user_voice(voice_id)
                break

    def paste_and_speak(self, event):
        self.stop(event)
        self.text_area.delete("1.0", END)
        self.text_area.insert(END, self.master.clipboard_get())
        self.speak(event)

    def select_all_text(self, event):
        self.text_area.tag_add(SEL, "1.0", END)

    def stop(self, event):
        if self.stop_button['state'].__str__() == NORMAL:
            self.speech.stop()
            self.speak_button['state'] = NORMAL
            self.stop_button['state'] = DISABLED

    def onStart(self, name):
        self.speak_button['state'] = DISABLED
        self.stop_button['state'] = NORMAL
        print("onStart")

    def onStartWord(self, name, location, length):
        spoken, current, next_ = word_window(self.spoken_text, location, length)
        self.spoken_words['text'] = spoken
        self.current_word_label['text'] = current
        self.next_words['text'] = next_
        if self.highlight_index1 is not None:
            self.text_area.tag_remove(TAG_CURRENT_WORD, self.highlight_index1, self.highlight_index2)
        self.highlight_index1, self.highlight_index2 = highlight_indices(location, length)
        self.text_area.see(self.highlight_index1)
        self.text_area.tag_add(TAG_CURRENT_WORD, self.highlight_index1, self.highlight_index2)

        self.progress["maximum"] = self.spoken_text.__len__()
        self.progress["value"] = location

    def onEnd(self, name, completed):
        self.speak_button['state'] = NORMAL
        self.stop_button['state'] = DISABLED
        self.progress["maximum"] = self.spoken_text.__len__()
        self.progress["value"] = self.spoken_text.__len__()
        print("onEnd")

    def speak(self, event):
        if self.speak_button['state'].__str__() == NORMAL:
            self.spoken_text = preprocess_text(self.text_area.get("1.0", END))
            self.text_area.delete("1.0", END)
            self.text_area.insert(END, self.spoken_text)

            speech_speed = int(self.speed_entry.get())

            self.thread = threading.Thread(target=self.speak_on_thread, args=(speech_speed, self.spoken_text))
            self.thread.daemon = True
            self.thread.start()

    def speak_on_thread(self, speech_speed, spoken_text):
        self.speech.speak(spoken_text, speech_speed)

    def speak_external(self, text, rate, voice=None):
        # Entry point for MCP agent speech (called from the server thread).
        # Update the UI on the tkinter main thread, but run the BLOCKING speak on
        # this server thread (never inside `after`, which would freeze the UI).
        # Blocking serializes per-utterance voices so agents don't bleed voices.
        self.after(0, lambda: self._render_external(text))
        self.speech.speak(text, rate, voice=voice, block=True)

    def _render_external(self, text):
        self.spoken_text = text
        self.text_area.delete("1.0", END)
        self.text_area.insert(END, text)


TAG_CURRENT_WORD = "current word"
GITHUB_URL = "https://github.com/DeadlyApps/SpeedReader"
