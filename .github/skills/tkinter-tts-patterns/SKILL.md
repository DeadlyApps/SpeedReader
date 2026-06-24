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

## COM same-thread rule (HIGH-RISK — a crash, not just a freeze)
- pyttsx3's SAPI5 engine is a **COM object**. It MUST be created, pumped (`startLoop`), and have its callbacks delivered on the **SAME thread**. Creating it on the tkinter main thread but pumping it on another thread makes SAPI5's word/utterance callbacks fire with NO Python thread state → fatal `PyEval_RestoreThread ... thread state NULL` crash (strict on Python 3.12+/3.14).
- REPEAT: NEVER call `pyttsx3.init()` / create the engine on the tkinter main thread. `SpeechEngine.prime_async()` creates AND pumps it on one dedicated daemon thread.
- The main thread and the MCP server thread NEVER touch the COM engine directly: `get_voices()` returns voices the loop thread enumerated (cached, waited-for), and `speak()` waits for the engine to be ready (`_await_engine`) instead of creating it.
- `set_voice()` is **store-only** (applied per-utterance in `_apply_properties`) so the main thread never calls `setProperty` on the COM engine.
- REPEAT: engine creation + voice enumeration + `startLoop` all happen on the `prime_async` loop thread; foreign threads only queue + wait.

## Engine lifecycle (create ONCE, start loop ONCE — only on the loop thread)
- The engine is created once (`pyttsx3.init()` + `connect()` the callbacks) and reused, on the dedicated loop thread. Voices are enumerated there too and cached, so `get_voices()` never creates the COM engine on the caller.
- The run loop (`startLoop()`) is started AT MOST ONCE, guarded by `_started`. `MainFrame.__init__` primes it via `prime_async(500)` on a **daemon thread** at startup (always — not just when hosting MCP), BEFORE `get_voices()`. REPEAT: `speak()` NEVER starts the loop; it only applies properties + `say(...)`. `startLoop()` runs exactly once for the app's lifetime.
- WHY: `startLoop()` blocks the thread that calls it. If `speak()` started the loop while holding its serialization lock, the lock would never release and every later speak would deadlock. So the loop owner is a dedicated daemon thread, and speakers only queue + wait. REPEAT: never call `startLoop()` under the speak lock.
- NEVER re-init the engine and NEVER call `startLoop()` a second time. `_started` prevents a second call.
- Voice: `set_voice(voice_id)` records the DEFAULT voice (store-only; applied per-utterance). `speak(text, rate, voice=...)` takes an optional PER-UTTERANCE voice that overrides the default for that one utterance (used by the MCP server so different agents speak in different voices). Rate (and the chosen voice) are re-applied on EVERY utterance. REPEAT: apply rate AND the per-utterance/default voice each `say`, not just on first speak.
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
