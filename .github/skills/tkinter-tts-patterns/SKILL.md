---
name: tkinter-tts-patterns
description: 'Use when adding or changing tkinter/ttk UI or pyttsx3 text-to-speech behavior in SpeedReader (Frames/, Controllers/). Covers the daemon-thread + single-init engine callback model, grid/row_index layout, button-state idiom, and single-line Text-index word highlighting. Use to avoid freezing the UI, double-initializing the engine, or breaking highlight offsets.'
---

# tkinter + pyttsx3 patterns (SpeedReader)

## When to Use
- Adding/changing widgets or layout in [MainFrame.py](../../../Frames/MainFrame.py) or window setup in [SpeedReaderController.py](../../../Controllers/SpeedReaderController.py).
- Touching speech: rate, voices, start/stop, or per-word UI updates.
- Debugging a frozen UI, words not highlighting, or the engine misbehaving on a second Speak.

## Threading model (do NOT break)
- Speech MUST run on a **daemon `threading.Thread`** (`speak_on_thread`). Never call `engine.say()`/`startLoop()` on the tkinter main thread — it freezes the UI.
- All UI updates come from `pyttsx3` callbacks, not polling.
- REPEAT: keep the thread `daemon = True` so it dies with the app.

## Engine lifecycle (create ONCE, start loop ONCE)
- The engine is created once (`pyttsx3.init()` + `connect()` the three callbacks) and reused. Creating the engine is SEPARATE from starting the run loop, so voices can be listed before any speech (`get_voices()` creates the engine but does NOT start the loop).
- The run loop (`startLoop()`) is started AT MOST ONCE, guarded by the `_started` flag — by the first `speak()` or by `ensure_loop()` (MCP in-process priming), whichever comes first. Every later `speak` only applies properties + `say(...)`.
- NEVER re-init the engine and NEVER call `startLoop()` a second time. REPEAT: `startLoop()` runs exactly once for the app's lifetime; `_started` is what prevents a second call.
- Voice: `set_voice(voice_id)` records the choice and applies `setProperty('voice', ...)`; the voice (and rate) are re-applied on EVERY utterance so the GUI and the MCP server speak with the selected voice. REPEAT: apply rate AND voice each `say`, not just on first speak.
- Callback → handler map: `started-utterance`→`onStart`, `started-word`→`onStartWord`, `finished-utterance`→`onEnd`.

## Word highlighting
- Text is treated as a **single line**: indices are `"1.{char_offset}"`.
- Input newlines are replaced with spaces in `speak()` BEFORE speaking, so offsets stay valid. REPEAT: if you change how text is preprocessed, keep length/offsets aligned or highlighting drifts.
- Keep `TAG_CURRENT_WORD` defined at module level so it resolves at call time.

## Layout & widget state
- Build widgets with manual `grid` using the running `row_index` counter; increment after each row. Don't hardcode rows.
- Set state: `widget['state'] = NORMAL | DISABLED`. Read state: `widget['state'].__str__() == NORMAL`. Guard new handlers like `speak()`/`stop()` do.

## Verify
1. `pip install -r requirements.txt` (`pyttsx3` pinned to `2.71` — do not bump).
2. Unit tests cover GUI-free logic in `Core/` (mock `pyttsx3`, do not test the library): `pip install -r requirements-dev.txt` then `python -m pytest -q`.
3. `python SpeedReader.py` and exercise Speak/Stop, `Ctrl+B` (paste & speak), `Ctrl+A` (select all); confirm the red word tracks audio and the UI stays responsive. The GUI itself has no automated coverage.
