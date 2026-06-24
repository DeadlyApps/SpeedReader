# SpeedReader - Copilot Instructions

## Project Overview
A Python desktop application that uses text-to-speech (TTS) to read text at high speeds (up to 500+ WPM). Built with tkinter for the GUI and pyttsx3 for speech synthesis.

## Architecture

### MVC-like Structure
```
SpeedReader.py          # Entry point - instantiates controller and starts mainloop
Controllers/            # Application controllers (extend Tk)
  SpeedReaderController.py  # Main window controller, sets up grid layout
Frames/                 # UI components (extend ttk.Frame)
  MainFrame.py          # All UI logic, TTS engine management, event handlers
```

### Key Patterns
- **Controller as Tk root**: `SpeedReaderController` extends `Tk` directly, not a separate class
- **Frame-based UI**: UI components are `ttk.Frame` subclasses passed `master=self` from controller
- **Threaded TTS**: Speech runs in daemon threads via `threading.Thread` to keep UI responsive
- **Fresh engine per session**: pyttsx3 engine is created fresh for each speech session to avoid state issues after interruption
- **Session ID tracking**: `speech_session_id` increments on new speech; callbacks check `current_session_id` to ignore stale events
- **Windows media control**: Pauses system music when TTS starts, resumes when finished (via `VK_MEDIA_PLAY_PAUSE` key simulation)

### Important Code Patterns

**Widget state checking** - uses string comparison:
```python
if self.speak_button['state'].__str__() == NORMAL:
```

**Text widget tagging** for highlighting current word:
```python
self.text_area.tag_config(TAG_CURRENT_WORD, foreground="red")
self.text_area.tag_add(TAG_CURRENT_WORD, index1, index2)
```

**pyttsx3 callbacks** - connect to engine events:
```python
self.engine.connect('started-utterance', self.onStart)
self.engine.connect('started-word', self.onStartWord)
self.engine.connect('finished-utterance', self.onEnd)
```

## Build & Run

### Development
```powershell
# Activate venv (may need execution policy)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\.venv\Scripts\Activate.ps1

# Run the app
python SpeedReader.py
```

### Build Executable
```powershell
pyinstaller SpeedReader.spec
# Output: dist/SpeedReader.exe (single file, no console)
```

## Dependencies
- `pyttsx3` - Cross-platform TTS (uses SAPI5 on Windows)
- `pyinstaller` - Build standalone executables
- `tkinter` - GUI (included with Python)

## UI Keyboard Shortcuts
- `Ctrl+A` - Select all text in text area
- `Ctrl+B` - Paste clipboard and immediately start speaking

## Testing Practices

### Test-Driven Development (TDD)
Follow the TDD cycle: **Red → Green → Refactor**
1. Write a failing test first
2. Write minimal code to make it pass
3. Refactor while keeping tests green

### Unit Test Structure
Use **Arrange-Act-Assert** pattern for all tests:
```python
def test_speed_entry_default_value():
    # Arrange
    controller = SpeedReaderController()
    frame = controller.winfo_children()[0]
    
    # Act
    speed_value = frame.speed_entry.get()
    
    # Assert
    assert speed_value == "500"
    controller.destroy()
```

### Testing tkinter Components
- Always call `controller.destroy()` in teardown to clean up Tk instances
- Use `controller.update()` to process pending UI events in tests
- Mock `pyttsx3.init()` to avoid actual speech synthesis during tests

## Agent Self-Improvement
**When you discover something new about this project**, update this instructions file:
- New patterns or conventions you observe in the code
- Build/run commands that aren't documented
- Gotchas or workarounds you encounter
- Integration points with external systems

Keep this file current so future AI agents benefit from your learnings.
