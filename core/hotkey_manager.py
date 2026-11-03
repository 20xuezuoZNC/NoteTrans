from typing import Optional, Callable
from PySide6.QtCore import QObject, Signal
from pynput import keyboard
from config import config

def format_hotkey(hotkey_str: str) -> str:
    """
    Converts human-readable hotkey like 'Alt+Q' or 'Ctrl+Alt+T'
    to pynput format like '<alt>+q' or '<ctrl>+<alt>+t'.
    """
    parts = hotkey_str.lower().replace(" ", "").split("+")
    formatted = []
    special_keys = {"ctrl", "alt", "shift", "cmd", "super"}
    for p in parts:
        if p in special_keys:
            formatted.append(f"<{p}>")
        else:
            formatted.append(p)
    return "+".join(formatted)

class HotkeyManager(QObject):
    """Manages global system hotkeys using pynput."""
    snip_triggered = Signal()
    toggle_window_triggered = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._listener: Optional[keyboard.GlobalHotKeys] = None

    def start(self):
        """Starts or restarts global hotkey listener with current config."""
        self.stop()

        snip_hk = config.get("general", "hotkey_screenshot", default="alt+q")
        win_hk = config.get("general", "hotkey_toggle_window", default="alt+w")

        mapping = {}
        try:
            mapping[format_hotkey(snip_hk)] = self.snip_triggered.emit
        except Exception as e:
            print(f"[HotkeyManager] Invalid snip hotkey {snip_hk}: {e}")

        try:
            mapping[format_hotkey(win_hk)] = self.toggle_window_triggered.emit
        except Exception as e:
            print(f"[HotkeyManager] Invalid toggle window hotkey {win_hk}: {e}")

        if mapping:
            try:
                self._listener = keyboard.GlobalHotKeys(mapping)
                self._listener.daemon = True
                self._listener.start()
            except Exception as e:
                print(f"[HotkeyManager] Error starting hotkeys: {e}")

    def stop(self):
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

    def reload(self):
        self.start()
