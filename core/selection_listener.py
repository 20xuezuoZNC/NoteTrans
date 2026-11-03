import math
import time
import os
import ctypes
from ctypes import wintypes
import threading
from typing import Optional, Tuple
from PySide6.QtCore import QObject, Signal
from pynput import mouse
import pyperclip
from config import config

kernel32 = ctypes.windll.kernel32
user32 = ctypes.windll.user32
VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_MENU = 0x12  # Alt
VK_C = 0x43
KEYEVENTF_KEYUP = 0x0002

def is_own_window(hwnd: int) -> bool:
    """Checks whether the given window handle belongs to NoteTrans process."""
    if not hwnd or not user32.IsWindow(hwnd):
        return False
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value == os.getpid()

def is_point_in_own_window(x: int, y: int) -> bool:
    """Checks whether the (x, y) screen point is within any NoteTrans window."""
    pt = wintypes.POINT(int(x), int(y))
    hwnd = user32.WindowFromPoint(pt)
    if is_own_window(hwnd):
        return True
    root = user32.GetAncestor(hwnd, 2)  # GA_ROOT
    if is_own_window(root):
        return True
    return False

def force_activate_window(hwnd: int):
    """Guarantees bringing target window to foreground using AttachThreadInput."""
    if not hwnd or not user32.IsWindow(hwnd) or is_own_window(hwnd):
        return
    cur_thread = kernel32.GetCurrentThreadId()
    fore_thread = user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), None)
    if cur_thread != fore_thread:
        user32.AttachThreadInput(cur_thread, fore_thread, True)
        user32.SetForegroundWindow(hwnd)
        user32.BringWindowToTop(hwnd)
        user32.AttachThreadInput(cur_thread, fore_thread, False)
    else:
        user32.SetForegroundWindow(hwnd)
        user32.BringWindowToTop(hwnd)

def simulate_ctrl_c(target_hwnd: Optional[int] = None):
    """
    Simulates native Ctrl+C safely:
    1. Ensures physical left mouse button is released.
    2. Only reactivates target window if foreground has actually changed.
    3. Releases stuck modifiers.
    4. Sends Ctrl+C keystroke.
    """
    if target_hwnd and is_own_window(target_hwnd):
        return

    # Wait until user physically releases the mouse button (up to 200ms)
    start_wait = time.time()
    while (user32.GetAsyncKeyState(0x01) & 0x8000) and (time.time() - start_wait < 0.2):
        time.sleep(0.01)

    time.sleep(0.02)
    if target_hwnd and user32.IsWindow(target_hwnd) and not is_own_window(target_hwnd):
        fg = user32.GetForegroundWindow()
        if fg != target_hwnd:
            force_activate_window(target_hwnd)
            time.sleep(0.04)

    # Release any stuck modifiers first
    for vk in (VK_CONTROL, VK_SHIFT, VK_MENU, VK_C):
        user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.01)

    # Press Ctrl + C
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    time.sleep(0.02)
    user32.keybd_event(VK_C, 0, 0, 0)
    time.sleep(0.03)
    user32.keybd_event(VK_C, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.02)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

def grab_selected_text(target_hwnd: Optional[int] = None, timeout: float = 0.55) -> str:
    """
    Grabs currently selected text from target application without corrupting clipboard.
    Uses GetClipboardSequenceNumber to detect updates accurately.
    """
    if target_hwnd and is_own_window(target_hwnd):
        return ""
    old_content = ""
    try:
        old_content = pyperclip.paste()
    except Exception:
        pass

    seq_before = user32.GetClipboardSequenceNumber()

    # Send Ctrl+C
    simulate_ctrl_c(target_hwnd)

    # Wait for target app to update clipboard
    start = time.time()
    new_text = ""
    while time.time() - start < timeout:
        time.sleep(0.03)
        curr_seq = user32.GetClipboardSequenceNumber()
        if curr_seq != seq_before:
            try:
                curr = pyperclip.paste()
                if curr:
                    new_text = curr
                    break
            except Exception:
                pass

    # Restore old clipboard after brief delay
    def restore():
        try:
            if old_content and old_content != new_text:
                pyperclip.copy(old_content)
        except Exception:
            pass

    if new_text and old_content and new_text != old_content:
        threading.Timer(0.45, restore).start()

    return new_text.strip()

class SelectionListener(QObject):
    """
    Global mouse listener for word selection and right-click trigger.
    Detects drag selection and double-clicks, popping up [译] button.
    """
    selection_detected = Signal()  # Triggers UI to query QCursor.pos()
    trigger_requested = Signal(int) # Passes target_hwnd
    dismiss_requested = Signal()   # When clicked elsewhere

    def __init__(self, parent=None):
        super().__init__(parent)
        self._listener: Optional[mouse.Listener] = None
        self._enabled: bool = True
        self._is_active_selection: bool = False
        self._suppress_next_rbutton_up: bool = False
        self._target_hwnd: int = 0
        
        # State tracking
        self._press_pos: Tuple[int, int] = (0, 0)
        self._press_time: float = 0.0
        self._r_press_pos: Tuple[int, int] = (0, 0)
        self._r_press_time: float = 0.0
        self._last_up_pos: Tuple[int, int] = (0, 0)
        self._last_up_time: float = 0.0

    def start(self):
        """Starts the mouse listener thread."""
        self._enabled = config.get("general", "enable_selection_trigger", default=True)
        if self._listener is None:
            self._listener = mouse.Listener(
                on_click=self._on_click,
                win32_event_filter=self._win32_filter
            )
            self._listener.daemon = True
            self._listener.start()

    def stop(self):
        """Stops the mouse listener."""
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        if not enabled:
            self.set_selection_active(False)

    def set_selection_active(self, active: bool):
        """Sets whether the mini [译] button is currently active on screen."""
        self._is_active_selection = active
        if not active:
            self._suppress_next_rbutton_up = False

    def get_target_hwnd(self) -> int:
        return self._target_hwnd

    def _win32_filter(self, msg, data):
        """
        Windows hook event filter.
        WM_RBUTTONDOWN = 0x0204, WM_RBUTTONUP = 0x0205.
        If [译] button is showing, intercepts right click to trigger translation.
        """
        if not self._enabled:
            return True

        if self._is_active_selection and msg == 0x0204:
            if is_own_window(self._target_hwnd):
                self._is_active_selection = False
                return True
            # User clicked right mouse button while [译] is active!
            self._suppress_next_rbutton_up = True
            self._is_active_selection = False
            self.trigger_requested.emit(self._target_hwnd)
            return False

        if self._suppress_next_rbutton_up and msg == 0x0205:
            self._suppress_next_rbutton_up = False
            return False

        return True

    def _on_click(self, x, y, button, pressed):
        if not self._enabled:
            return

        # If click event happens inside NoteTrans window itself, ignore completely
        if is_point_in_own_window(x, y):
            return

        if button == mouse.Button.left:
            if pressed:
                self._press_pos = (x, y)
                self._press_time = time.time()
            else:
                now = time.time()
                duration = now - self._press_time
                dist = math.hypot(x - self._press_pos[0], y - self._press_pos[1])

                is_drag = (dist >= 8 and duration <= 6.0)
                
                # Check double click / triple click
                double_click_dist = math.hypot(x - self._last_up_pos[0], y - self._last_up_pos[1])
                is_double_click = (dist < 8 and (now - self._last_up_time) < 0.45 and double_click_dist < 12)

                self._last_up_pos = (x, y)
                self._last_up_time = now

                if is_drag or is_double_click:
                    # Save currently active window handle before focus moves
                    target = user32.GetForegroundWindow()
                    if is_own_window(target):
                        return
                    self._target_hwnd = target
                    def delayed_emit():
                        time.sleep(0.08)
                        self.selection_detected.emit()
                    threading.Thread(target=delayed_emit, daemon=True).start()

        elif button == mouse.Button.right:
            if pressed:
                self._r_press_pos = (x, y)
                self._r_press_time = time.time()
            else:
                now = time.time()
                duration = now - self._r_press_time
                dist = math.hypot(x - self._r_press_pos[0], y - self._r_press_pos[1])
                # Support right-click drag selection (> 15px)
                if dist >= 15 and 0.08 <= duration <= 5.0:
                    target = user32.GetForegroundWindow()
                    if is_own_window(target):
                        return
                    self._target_hwnd = target
                    def delayed_emit():
                        time.sleep(0.08)
                        self.selection_detected.emit()
                    threading.Thread(target=delayed_emit, daemon=True).start()
