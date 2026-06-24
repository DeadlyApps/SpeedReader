---
description: "Build the SpeedReader standalone Windows EXE with PyInstaller and verify the output."
name: "Release Build"
agent: "agent"
---
Build the standalone Windows EXE for SpeedReader.

Steps:
1. Ensure dependencies are installed: `pip install -r requirements.txt` (note `pyttsx3` is pinned to `2.71` on purpose — do not change it).
2. Run the build using the existing spec file:
   ```pwsh
   pyinstaller --clean --onefile --windowed SpeedReader.spec
   ```
3. Confirm `dist/SpeedReader.exe` was produced and report its path and size.
4. If the build fails with a PyInstaller bootloader issue, point the user to the background link noted in [README.md](../../README.md) (https://github.com/pyinstaller/pyinstaller/issues/3268) instead of guessing.

Do not modify [SpeedReader.spec](../../SpeedReader.spec) unless the user explicitly asks. Report the result; do not run the produced EXE.
