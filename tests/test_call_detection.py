from Core.call_detection import microphone_in_use, _key_active


class _FakeWinreg:
    """Minimal winreg stand-in driven by a nested dict of fake registry keys.

    Each node is ``{"values": {name: value}, "subkeys": {name: node}}``.
    """

    FileNotFoundError = FileNotFoundError

    def __init__(self, root):
        self._root = root

    def QueryValueEx(self, key, name):
        if name in key["values"]:
            return key["values"][name], 0
        raise FileNotFoundError(name)

    def EnumKey(self, key, index):
        names = list(key["subkeys"].keys())
        if index >= len(names):
            raise OSError("no more subkeys")
        return names[index]

    def OpenKey(self, key, name):
        return _Ctx(key["subkeys"][name])


class _Ctx:
    def __init__(self, node):
        self._node = node

    def __enter__(self):
        return self._node

    def __exit__(self, *exc):
        return False


def _node(values=None, subkeys=None):
    return {"values": values or {}, "subkeys": subkeys or {}}


def test_scan_returns_false_when_no_app_holds_mic():
    tree = _node(subkeys={
        "App.A": _node(values={"LastUsedTimeStop": 132000000000000}),
        "NonPackaged": _node(subkeys={
            "C__app.exe": _node(values={"LastUsedTimeStop": 132000000000001}),
        }),
    })
    winreg = _FakeWinreg(tree)
    assert _key_active(winreg, tree) is False


def test_scan_detects_packaged_app_using_mic():
    tree = _node(subkeys={
        "Teams": _node(values={"LastUsedTimeStop": 0}),
    })
    winreg = _FakeWinreg(tree)
    assert _key_active(winreg, tree) is True


def test_scan_detects_nonpackaged_app_using_mic():
    tree = _node(subkeys={
        "NonPackaged": _node(subkeys={
            "C__zoom.exe": _node(values={"LastUsedTimeStop": 0}),
        }),
    })
    winreg = _FakeWinreg(tree)
    assert _key_active(winreg, tree) is True


def test_microphone_in_use_uses_injected_scan():
    assert microphone_in_use(scan=lambda: True) is True
    assert microphone_in_use(scan=lambda: False) is False


def test_microphone_in_use_swallows_errors():
    def boom():
        raise OSError("access denied")

    assert microphone_in_use(scan=boom) is False
