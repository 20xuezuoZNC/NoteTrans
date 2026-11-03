import sys
import os
import threading
from typing import Optional

from PySide6.QtCore import Qt, QObject, Signal, QThread, QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QGuiApplication, QPixmap, QImage
import numpy as np

# Ensure high DPI attributes are properly configured before QApplication creation
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

from config import config
from core.translator import translate
from core.ocr_engine import ocr_engine
from core.selection_listener import SelectionListener, grab_selected_text
from core.hotkey_manager import HotkeyManager

from ui.float_window import FloatTranslationWindow
from ui.mini_button import MiniTriggerButton
from ui.snipping_widget import SnippingOverlay
from ui.tray_icon import NoteTransTray, create_default_tray_icon
from ui.settings_dialog import SettingsDialog

class OCRTaskWorker(QObject):
    finished = Signal(str, str)

    def __init__(self, img_array: np.ndarray):
        super().__init__()
        self.img_array = img_array

    def run(self):
        try:
            text = ocr_engine.recognize(self.img_array)
            self.finished.emit(text, "")
        except Exception as e:
            self.finished.emit("", str(e))

class TextGrabWorker(QObject):
    finished = Signal(str)

    def __init__(self, target_hwnd=None):
        super().__init__()
        self.target_hwnd = target_hwnd

    def run(self):
        text = grab_selected_text(self.target_hwnd)
        self.finished.emit(text)

class NoteTransApp(QObject):
    """Main Application Controller for NoteTrans."""

    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self._ocr_thread: Optional[QThread] = None
        self._grab_thread: Optional[QThread] = None

        # 1. Instantiate UI components
        self.float_window = FloatTranslationWindow()
        self.mini_btn = MiniTriggerButton()
        self.snipping = SnippingOverlay()
        self.tray = NoteTransTray()
        self.settings_dlg = SettingsDialog()

        # 2. Instantiate Core Controllers
        self.selection_listener = SelectionListener()
        self.hotkey_manager = HotkeyManager()

        # 3. Connect signals
        self._wire_signals()

    def start(self):
        """Starts listeners, tray, and background services."""
        self.tray.show()
        self.selection_listener.start()
        self.hotkey_manager.start()

        # Display floating window on startup with friendly quick-guide
        self.float_window.show_at_cursor()
        self.float_window.set_content("Hello NoteTrans", auto_translate=False)
        self.float_window.trans_text_edit.setHtml(
            "<div style='color: #b45309; font-weight: 700; font-size: 14px; letter-spacing: 0.5px;'>◈ NoteTrans 已就绪</div>"
            "<div style='color: #57534e; font-size: 12.5px; margin-top: 8px; line-height: 1.7;'>"
            "• <b>划词翻译</b>：在任意软件中选中文本后，点击小「译」按钮或单击鼠标右键。<br>"
            "• <b>截图翻译</b>：随时按 <code>Alt + Q</code> 框选屏幕区域进行 OCR 识图翻译。<br>"
            "• <b>呼出窗口</b>：随时按 <code>Alt + W</code> 或点击右下角托盘图标唤醒。<br>"
            "• <b>固定置顶</b>：点击右上角 ⊸ 按钮即可锁定窗口，失去焦点不隐藏。"
            "</div>"
        )

    def _wire_signals(self):
        # Mini Button & Selection Listener
        self.selection_listener.selection_detected.connect(self._on_selection_detected)
        self.selection_listener.trigger_requested.connect(self._on_trigger_translation)
        self.selection_listener.dismiss_requested.connect(self._on_dismiss_selection)

        self.mini_btn.trigger_requested.connect(self._on_mini_btn_clicked)

        # Snipping
        self.snipping.region_captured.connect(self._on_region_captured)
        self.snipping.cancelled.connect(self._on_snip_cancelled)

        self.tray.snip_requested.connect(self._request_snipping)
        self.float_window.snip_requested.connect(self._request_snipping)
        self.hotkey_manager.snip_triggered.connect(self._request_snipping)

        # Toggle / Show Window
        self.tray.toggle_window_requested.connect(self._toggle_float_window)
        self.hotkey_manager.toggle_window_triggered.connect(self._toggle_float_window)

        # Settings
        self.tray.settings_requested.connect(self._open_settings)
        self.float_window.settings_requested.connect(self._open_settings)
        self.settings_dlg.settings_changed.connect(self._on_settings_saved)

        # Tray Listener Toggle
        self.tray.toggle_selection_listener.connect(self.selection_listener.set_enabled)

        # Exit
        self.tray.exit_requested.connect(self._shutdown)

    def _on_selection_detected(self):
        """Shows the mini [译] button right next to cursor in logical coordinates."""
        if not config.get("general", "enable_selection_trigger", default=True):
            return
        
        # Don't show mini button if floating window currently has focus
        if self.float_window.isVisible() and self.float_window.isActiveWindow():
            return

        self.mini_btn.show_near_cursor(15, 15)
        self.selection_listener.set_selection_active(True)

    def _on_dismiss_selection(self):
        self.mini_btn.hide_button()
        self.selection_listener.set_selection_active(False)

    def _on_mini_btn_clicked(self):
        target_hwnd = self.selection_listener.get_target_hwnd()
        self._on_trigger_translation(target_hwnd)

    def _on_trigger_translation(self, target_hwnd=None):
        """Pulls selected text from active window and begins translation."""
        self.mini_btn.hide_button()
        self.selection_listener.set_selection_active(False)

        if self._grab_thread and self._grab_thread.isRunning():
            self._grab_thread.quit()
            self._grab_thread.wait()

        self._grab_thread = QThread()
        self._grab_worker = TextGrabWorker(target_hwnd)
        self._grab_worker.moveToThread(self._grab_thread)

        self._grab_thread.started.connect(self._grab_worker.run)
        self._grab_worker.finished.connect(self._handle_grabbed_text, Qt.ConnectionType.QueuedConnection)
        self._grab_worker.finished.connect(self._grab_thread.quit)

        self._grab_thread.start()

    def _handle_grabbed_text(self, text: str):
        self.float_window.show_at_cursor()
        text = text.strip()
        if text:
            self.float_window.set_content(text, auto_translate=True)
        else:
            self.float_window.set_content("", auto_translate=False)
            self.float_window.trans_text_edit.setHtml(
                "<div style='color: #475569; font-size: 13px; line-height: 1.6;'>"
                "<span style='color: #64748b;'>可在上方「原文」中直接粘贴或输入文字，或按 <b>Alt + Q</b> 框选截图翻译。</span>"
                "</div>"
            )

    def _request_snipping(self):
        """Hides existing floating window and starts snipping capture."""
        self.mini_btn.hide_button()
        self.selection_listener.set_selection_active(False)
        self.float_window.hide()

        # Brief delay to allow window to completely disappear before screen grab
        QTimer.singleShot(120, self.snipping.start_capture)

    def _on_snip_cancelled(self):
        pass

    def _on_region_captured(self, pixmap: QPixmap):
        """Handles cropped screenshot region and starts RapidOCR in worker thread."""
        self.float_window.show_at_cursor()
        self.float_window.trans_text_edit.setHtml("<span style='color: #3b82f6;'><i>正在识别文字 (OCR)...</i></span>")

        # Convert QPixmap to numpy array on GUI thread before sending to QThread (thread-safe!)
        qimage = pixmap.toImage().convertToFormat(QImage.Format.Format_RGB888)
        width = qimage.width()
        height = qimage.height()
        stride = qimage.bytesPerLine()
        buf = qimage.bits()
        arr = np.frombuffer(buf, dtype=np.uint8).reshape((height, stride))[:, :width * 3].reshape((height, width, 3)).copy()

        if self._ocr_thread and self._ocr_thread.isRunning():
            self._ocr_thread.quit()
            self._ocr_thread.wait()

        self._ocr_thread = QThread()
        self._ocr_worker = OCRTaskWorker(arr)
        self._ocr_worker.moveToThread(self._ocr_thread)

        self._ocr_thread.started.connect(self._ocr_worker.run)
        self._ocr_worker.finished.connect(self._on_ocr_finished, Qt.ConnectionType.QueuedConnection)
        self._ocr_worker.finished.connect(self._ocr_thread.quit)

        self._ocr_thread.start()

    def _on_ocr_finished(self, text: str, error: str):
        if error:
            self.float_window.trans_text_edit.setHtml(f"<span style='color: #ef4444;'>OCR 识别失败: {error}</span>")
            return
        
        text = text.strip()
        if not text:
            self.float_window.trans_text_edit.setHtml("<span style='color: #94a3b8;'>未在选区中识别到有效文字</span>")
            return

        self.float_window.set_content(text, auto_translate=True)

    def _toggle_float_window(self):
        if self.float_window.isVisible():
            self.float_window.hide()
        else:
            self.float_window.show_at_cursor()

    def _open_settings(self):
        self.settings_dlg.show()
        self.settings_dlg.raise_()
        self.settings_dlg.activateWindow()

    def _on_settings_saved(self):
        self.hotkey_manager.reload()
        self.tray.update_hotkey_labels()
        self.selection_listener.set_enabled(config.get("general", "enable_selection_trigger", default=True))

    def _shutdown(self):
        self.selection_listener.stop()
        self.hotkey_manager.stop()
        self.app.quit()

def main():
    try:
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setWindowIcon(create_default_tray_icon())
    # Ensure app stays alive when windows are hidden
    app.setQuitOnLastWindowClosed(False)

    note_trans = NoteTransApp(app)
    note_trans.start()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
