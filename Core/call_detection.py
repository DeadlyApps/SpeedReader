"""GUI-free detection of whether the user is likely in a call.

On Windows, apps that are *currently* using the microphone leave a record under
``HKCU\\...\\CapabilityAccessManager\\ConsentStore\\microphone``: each app key has
a ``LastUsedTimeStop`` QWORD that is ``0`` while the mic is in use and set to a
FILETIME once it stops. We treat "any app holding the microphone" as a proxy for
"in a call", which is good enough to pause agent speech.

Everything here is injectable so the logic is unit-tested without touching the
real registry, and it degrades to ``False`` on non-Windows or on any error (so a
detection failure never blocks speech).
"""
import sys

# Root of the per-app microphone consent records (under HKEY_CURRENT_USER).
_MIC_KEY = (
    r"SOFTWARE\Microsoft\Windows\CurrentVersion"
    r"\CapabilityAccessManager\ConsentStore\microphone"
)


def microphone_in_use(scan=None):
    """Return ``True`` if any app is currently using the microphone.

    ``scan`` is injectable for testing; by default it walks the Windows registry.
    Any error (missing key, non-Windows, access denied) is swallowed and reported
    as ``False`` so detection never prevents speech on failure.
    """
    scan = scan or _scan_windows_microphone
    try:
        return bool(scan())
    except Exception:
        return False


def _scan_windows_microphone():
    """Walk the Windows mic consent store; ``True`` if an app holds the mic."""
    if not sys.platform.startswith("win"):
        return False
    import winreg

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _MIC_KEY)
    except FileNotFoundError:
        return False
    with key:
        return _key_active(winreg, key)


def _key_active(winreg, key):
    """Recursively report whether ``key`` (or a descendant) holds the mic.

    Packaged apps store ``LastUsedTimeStop`` directly on their key; desktop apps
    live one level down under the ``NonPackaged`` container, so we recurse into
    every subkey. ``LastUsedTimeStop == 0`` means the mic is still in use.
    """
    try:
        stop, _ = winreg.QueryValueEx(key, "LastUsedTimeStop")
        if stop == 0:
            return True
    except FileNotFoundError:
        pass

    index = 0
    while True:
        try:
            name = winreg.EnumKey(key, index)
        except OSError:
            break
        index += 1
        with winreg.OpenKey(key, name) as sub:
            if _key_active(winreg, sub):
                return True
    return False
