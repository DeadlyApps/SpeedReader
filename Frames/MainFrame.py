import threading
import webbrowser
import tkinter.ttk as ttk
from tkinter.constants import END, N, S, E, W, NORMAL, DISABLED, RIGHT, CENTER, SEL, INSERT, HORIZONTAL
from tkinter import Text
import pyttsx3
from pyttsx3 import engine
import re
import platform
import asyncio

# Windows media key support
if platform.system() == 'Windows':
    import ctypes
    VK_MEDIA_PLAY_PAUSE = 0xB3
    KEYEVENTF_EXTENDEDKEY = 0x0001
    KEYEVENTF_KEYUP = 0x0002
    
    # Try to import Windows Media Session API for detecting playback state
    try:
        from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager
        from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionPlaybackStatus
        MEDIA_SESSION_AVAILABLE = True
    except ImportError:
        MEDIA_SESSION_AVAILABLE = False
        print("Windows Media Session API not available - media detection disabled")

class MainFrame(ttk.Frame):
    def __init__(self, **kw):
        ttk.Frame.__init__(self, **kw)
        self.speech = SpeechEngine(self.onStart, self.onStartWord, self.onEnd)
        self.speak_service = SpeakService(rate=500, speak_fn=self.speak_external)
        # Create + pump the pyttsx3 COM engine on ONE dedicated daemon thread.
        # It MUST NOT be created on this (tkinter main) thread, or SAPI5's word
        # callbacks fire on the pump thread with no Python thread state and crash
        # the process. prime_async builds it on the loop thread; get_voices then
        # waits for the voices that thread enumerated.
        self.speech.prime_async(500)
        self.voices = self.speech.get_voices()
        self.voice_registry = self._build_voice_registry()
        self.mcp_host = None  # set by the controller when MCP hosting is enabled
        self.spoken_text = ''
        self.highlight_index1 = None
        self.highlight_index2 = None
        self.media_was_paused = False  # Track if we paused media playback
        self.build_frame_content(kw)

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

        # Second row: MCP server port + restart. The restart button is enabled
        # only once the controller hosts a server (set_server_port enables it).
        self.server_label = ttk.Label(self.settings_frame, text="Server port: ")
        self.server_label.grid(row=1, column=0, padx=(0, 5), pady=(10, 0))
        self.port_var = StringVar(value="8765")
        self.port_entry = ttk.Entry(self.settings_frame, width=6, textvariable=self.port_var)
        self.port_entry.grid(row=1, column=1, padx=(0, 20), pady=(10, 0))
        self.restart_server_button = ttk.Button(
            self.settings_frame, text="Restart Server", command=self.restart_server,
            state=DISABLED)
        self.restart_server_button.grid(row=1, column=2, columnspan=3, sticky=W, pady=(10, 0))
        self.server_status_var = StringVar(value="")
        self.server_status = ttk.Label(self.settings_frame, textvariable=self.server_status_var)
        self.server_status.grid(row=1, column=3, columnspan=2, sticky=W, pady=(10, 0))
        self.server_status_button = ttk.Button(
            self.settings_frame, text="Server Status…", command=self.open_server_status)
        self.server_status_button.grid(row=2, column=0, columnspan=2, sticky=W, pady=(10, 0))
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
        self.cleanup_engine()
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

    def open_server_status(self):
        """Show MCP server status: hosting state plus per-voice agent claims.

        Refreshes on a timer so claims/releases and live mic state stay current,
        and cancels that timer when the dialog closes.
        """
        dialog = Toplevel(self)
        dialog.title("MCP Server Status")
        dialog.transient(self.master)

        body = ttk.Label(dialog, justify=LEFT, anchor=W, font=("Consolas", 11))
        body.grid(row=0, column=0, sticky=(N, S, W, E), padx=12, pady=12)

        def refresh():
            body['text'] = self._server_status_text()
            dialog._status_job = dialog.after(1000, refresh)

        def on_close():
            job = getattr(dialog, "_status_job", None)
            if job is not None:
                dialog.after_cancel(job)
            dialog.destroy()

        ttk.Button(dialog, text="Close", command=on_close).grid(
            row=1, column=0, sticky=E, padx=12, pady=(0, 12))
        dialog.protocol("WM_DELETE_WINDOW", on_close)
        refresh()

    def _server_status_text(self):
        """Build the multi-line status text for the Server Status dialog."""
        lines = []
        host = self.mcp_host
        if host is not None and host.is_running():
            lines.append("Server: running on {}:{}".format(host.host, host.port))
            paused = getattr(host, "pause_when_mic_in_use", False)
            lines.append("Pause while mic in use: {}".format("on" if paused else "off"))
            if paused:
                from Core.call_detection import microphone_in_use
                lines.append("Microphone in use now: {}".format(
                    "yes" if microphone_in_use() else "no"))
        else:
            lines.append("Server: not hosting (enable mcp in config.json)")

        lines.append("")
        lines.append("Voices and the agents that claimed them:")
        status = self.voice_registry.status()
        if not status:
            lines.append("  (no voices enabled)")
        for entry in status:
            holders = entry["claimed_by"]
            who = ", ".join(holders) if holders else "(unclaimed)"
            lines.append("  {} — {}".format(entry["name"], who))
        return "\n".join(lines)

    def set_server_port(self, port):
        """Reflect the active MCP port in the UI and enable Restart (host is up)."""
        self.port_var.set(str(port))
        self.restart_server_button['state'] = NORMAL
        self.server_status_var.set("running on {}".format(port))

    def restart_server(self):
        """Restart the MCP server on the port from the entry and persist it."""
        if self.mcp_host is None:
            self.server_status_var.set("hosting disabled")
            return
        try:
            port = int(self.port_var.get())
        except ValueError:
            self.server_status_var.set("invalid port")
            return
        if not (1 <= port <= 65535):
            self.server_status_var.set("port out of range")
            return
        self.server_status_var.set("restarting…")
        self.restart_server_button['state'] = DISABLED
        self.update_idletasks()
        try:
            self.mcp_host.restart(port=port)
        except OSError as exc:
            self.server_status_var.set("failed: {}".format(exc))
            self.restart_server_button['state'] = NORMAL
            return
        save_mcp_port(port)
        self.server_status_var.set("running on {}".format(port))
        self.restart_server_button['state'] = NORMAL

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
        """Stop current speech, paste clipboard content, and start speaking."""
        # Force stop any current speech and reset state
        self.force_stop_and_reset()
        
        # Clear UI and insert new text
        self.clear_display_labels()
        self.text_area.delete("1.0", END)
        try:
            clipboard_text = self.master.clipboard_get()
            self.text_area.insert(END, clipboard_text)
        except Exception as e:
            print(f"Error getting clipboard: {e}")
            return
        
        # Start speaking the new text
        self.speak(event)

    def force_stop_and_reset(self):
        """Force stop current speech and reset engine for fresh start."""
        self.stop_requested = True
        
        # Increment session ID to invalidate any pending callbacks from old session
        self.speech_session_id += 1
        
        # Stop the current engine if running
        if self.engine is not None:
            try:
                self.engine.stop()
            except Exception as e:
                print(f"Error stopping engine: {e}")
            # Dispose of the engine - we'll create a fresh one
            self.engine = None
        
        # Wait briefly for the speech thread to finish
        if self.speech_thread is not None and self.speech_thread.is_alive():
            self.speech_thread.join(timeout=0.5)
        
        # Reset state
        self.is_speaking = False
        self.stop_requested = False
        self.speak_button['state'] = NORMAL
        self.stop_button['state'] = DISABLED

    def clear_display_labels(self):
        """Clear all the display labels and progress."""
        self.spoken_words['text'] = ''
        self.current_word_label['text'] = ''
        self.next_words['text'] = ''
        self.progress["value"] = 0
        
        # Clear highlighting
        if self.highlight_index1 is not None:
            try:
                self.text_area.tag_remove(TAG_CURRENT_WORD, self.highlight_index1, self.highlight_index2)
            except Exception:
                pass
            self.highlight_index1 = None
            self.highlight_index2 = None

    def pause_system_media(self):
        """Pause any currently playing system media (Windows only).
        
        Uses Windows Media Session API to check if media is actually playing
        before sending the pause command. This prevents toggling music that
        was already paused.
        """
        if platform.system() != 'Windows':
            return
            
        # Check if media is actually playing before pausing
        if not self._is_media_playing():
            print("No media playing - skipping pause")
            self.media_was_paused = False
            return
            
        try:
            # Send media play/pause key press to pause
            ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, KEYEVENTF_EXTENDEDKEY, 0)
            ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
            self.media_was_paused = True
            print("Paused system media playback")
        except Exception as e:
            print(f"Error pausing media: {e}")
            self.media_was_paused = False
    
    def _is_media_playing(self):
        """Check if system media is currently playing (Windows only).
        
        Uses Windows Media Session API to query the current playback state.
        Returns True if media is playing, False otherwise.
        """
        if platform.system() != 'Windows':
            return False
            
        if not MEDIA_SESSION_AVAILABLE:
            # If API not available, assume nothing is playing to be safe
            return False
            
        try:
            # Run async check synchronously
            return asyncio.run(self._check_media_playing_async())
        except Exception as e:
            print(f"Error checking media state: {e}")
            return False
    
    async def _check_media_playing_async(self):
        """Async helper to check media playback state."""
        try:
            # Get the media session manager
            manager = await GlobalSystemMediaTransportControlsSessionManager.request_async()
            session = manager.get_current_session()
            
            if session is None:
                return False
                
            # Get playback info
            playback_info = session.get_playback_info()
            status = playback_info.playback_status
            
            # Check if currently playing
            return status == GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING
        except Exception as e:
            print(f"Error in async media check: {e}")
            return False
    
    def resume_system_media(self):
        """Resume system media playback if we previously paused it (Windows only).
        
        Only resumes if media_was_paused flag is set.
        """
        if platform.system() == 'Windows' and self.media_was_paused:
            try:
                # Send media play/pause key press to resume
                ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, KEYEVENTF_EXTENDEDKEY, 0)
                ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
                self.media_was_paused = False
                print("Resumed system media playback")
            except Exception as e:
                print(f"Error resuming media: {e}")

    def select_all_text(self, event):
        self.text_area.tag_add(SEL, "1.0", END)

    def stop(self, event):
        """Stop current speech when stop button is clicked."""
        if self.stop_button['state'].__str__() == NORMAL:
            self.speech.stop()
            self.speak_button['state'] = NORMAL
            self.stop_button['state'] = DISABLED

    def onStart(self, name):
        """Called when an utterance starts."""
        # Ignore callbacks from old speech sessions
        if self.current_session_id != self.speech_session_id:
            return
        self.is_speaking = True
        self.stop_requested = False
        self.speak_button['state'] = DISABLED
        self.stop_button['state'] = NORMAL
        
        # Pause any system media playing
        self.pause_system_media()
        print(f"onStart: {name}")

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
        """Called when an utterance finishes.
        
        Args:
            name: The name of the utterance that finished
            completed: True if speech completed normally, False if interrupted
        """
        # Ignore callbacks from old speech sessions
        if self.current_session_id != self.speech_session_id:
            print(f"onEnd: {name} - ignored (old session)")
            return
            
        self.is_speaking = False
        self.speak_button['state'] = NORMAL
        self.stop_button['state'] = DISABLED
        
        if completed:
            # Speech completed normally - update progress to 100%
            self.progress["maximum"] = self.spoken_text.__len__()
            self.progress["value"] = self.spoken_text.__len__()
            print(f"onEnd: {name} - completed successfully")
        else:
            # Speech was interrupted/stopped
            print(f"onEnd: {name} - interrupted")
        
        # Clear the current word highlight
        if self.highlight_index1 is not None:
            try:
                self.text_area.tag_remove(TAG_CURRENT_WORD, self.highlight_index1, self.highlight_index2)
            except Exception:
                pass
            self.highlight_index1 = None
            self.highlight_index2 = None
        
        # Resume any system media we paused
        self.resume_system_media()

    def onError(self, name, exception):
        """Called when an error occurs during speech.
        
        Args:
            name: The name of the utterance that had an error
            exception: The exception that occurred
        """
        # Ignore callbacks from old speech sessions
        if self.current_session_id != self.speech_session_id:
            return
            
        self.is_speaking = False
        self.speak_button['state'] = NORMAL
        self.stop_button['state'] = DISABLED
        print(f"onError: {name} - {exception}")
        
        # Clear highlighting on error
        if self.highlight_index1 is not None:
            try:
                self.text_area.tag_remove(TAG_CURRENT_WORD, self.highlight_index1, self.highlight_index2)
            except Exception:
                pass
            self.highlight_index1 = None
            self.highlight_index2 = None
        
        # Resume any system media we paused
        self.resume_system_media()

    def speak(self, event):
        if self.speak_button['state'].__str__() == NORMAL:
            self.spoken_text = preprocess_text(self.text_area.get("1.0", END))
            self.text_area.delete("1.0", END)
            self.text_area.insert(END, self.spoken_text)

            speech_speed = int(self.speed_entry.get())
            
            # Increment session ID for this new speech
            self.speech_session_id += 1
            session_id = self.speech_session_id

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
