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

## Engine lifecycle (create ONCE, start loop ONCE — only via `ensure_loop`)
- The engine is created once (`pyttsx3.init()` + `connect()` the callbacks) and reused. Creating the engine is SEPARATE from starting the run loop, so voices can be listed before any speech (`get_voices()` creates the engine but does NOT start the loop).
- The run loop (`startLoop()`) is started AT MOST ONCE, ONLY by `ensure_loop()`, guarded by `_started`. `MainFrame.__init__` primes it on a **daemon thread** at startup (always — not just when hosting MCP). REPEAT: `speak()` NEVER starts the loop; it only applies properties + `say(...)`. `startLoop()` runs exactly once for the app's lifetime.
- WHY: `startLoop()` blocks the thread that calls it. If `speak()` started the loop while holding its serialization lock, the lock would never release and every later speak would deadlock. So the loop owner is a dedicated daemon thread, and speakers only queue + wait. REPEAT: never call `startLoop()` under the speak lock.
- NEVER re-init the engine and NEVER call `startLoop()` a second time. `_started` prevents a second call.
- Voice: `set_voice(voice_id)` records the DEFAULT voice and applies `setProperty('voice', ...)`. `speak(text, rate, voice=...)` takes an optional PER-UTTERANCE voice that overrides the default for that one utterance (used by the MCP server so different agents speak in different voices). Rate (and the chosen voice) are re-applied on EVERY utterance. REPEAT: apply rate AND the per-utterance/default voice each `say`, not just on first speak.
- Callback → handler map: `started-utterance`→`onStart`, `started-word`→`onStartWord`, `finished-utterance`→`onEnd`. A SECOND `finished-utterance` subscriber (`_mark_done`) sets a `threading.Event` — pyttsx3 allows multiple callbacks per topic.

## Serialized speak (per-utterance voice — do NOT break)
- `speak()` holds a lock, applies rate + voice, `say()`s, then (when `block=True`, the default) WAITS on the `finished-utterance` event before returning. This serializes utterances so one agent's voice cannot bleed into the next queued utterance (pyttsx3 applies properties at processing time).
- Run `speak()` on a daemon/worker thread, NEVER the tkinter main thread (blocking the main thread freezes the UI). The GUI path uses `speak_on_thread`; the MCP path (`speak_external`) updates widgets via `after(...)` but runs the BLOCKING `speak` on the server thread.
- Tests pass `block=False` so the wait doesn't hang on a mock engine that never fires `finished-utterance`. REPEAT: in unit tests, `speak(..., block=False)`.


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
