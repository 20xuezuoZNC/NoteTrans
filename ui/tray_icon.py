import os
import subprocess
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from config import config

def create_default_tray_icon() -> QIcon:
    """Generates or loads a high-DPI friendly tray icon with a stylish '译' glyph."""
    ico_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.ico")
    if os.path.exists(ico_path):
        return QIcon(ico_path)
    if os.path.exists("app.ico"):
        return QIcon("app.ico")

    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    
    # Rounded background
    painter.setBrush(QColor(37, 99, 235))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(4, 4, 56, 56, 14, 14)

    # Text "译"
    painter.setPen(QColor(255, 255, 255))
    painter.setFont(QFont("Microsoft YaHei", 32, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "译")
    painter.end()

    return QIcon(pixmap)

from PySide6.QtCore import Qt

class NoteTransTray(QSystemTrayIcon):
    """System tray icon and context menu."""
    snip_requested = Signal()
    toggle_window_requested = Signal()
    toggle_selection_listener = Signal(bool)
    settings_requested = Signal()
    exit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(create_default_tray_icon())
        self.setToolTip("NoteTrans - 桌面划词与截图翻译助手")

        self._init_menu()
        self.activated.connect(self._on_tray_activated)

    def _init_menu(self):
        menu = QMenu()

        # 1. Selection listener toggle (checkable)
        self.action_selection = menu.addAction("开启划词监听")
        self.action_selection.setCheckable(True)
        enabled = config.get("general", "enable_selection_trigger", default=True)
        self.action_selection.setChecked(enabled)
        self.action_selection.toggled.connect(self._on_selection_toggled)

        # 2. Hotkey actions
        snip_hk = config.get("general", "hotkey_screenshot", default="Alt+Q").upper()
        self.action_snip = menu.addAction(f"框选识图翻译 ({snip_hk})")
        self.action_snip.triggered.connect(self.snip_requested.emit)

        win_hk = config.get("general", "hotkey_toggle_window", default="Alt+W").upper()
        self.action_win = menu.addAction(f"打开悬浮窗 ({win_hk})")
        self.action_win.triggered.connect(self.toggle_window_requested.emit)

        menu.addSeparator()

        # 3. Settings & config file
        self.action_settings = menu.addAction("设置与配置...")
        self.action_settings.triggered.connect(self.settings_requested.emit)

        self.action_config = menu.addAction("打开配置文件 (config.json)")
        self.action_config.triggered.connect(self._open_config_file)

        menu.addSeparator()

        # 4. Exit
        self.action_exit = menu.addAction("退出 NoteTrans")
        self.action_exit.triggered.connect(self.exit_requested.emit)

        self.setContextMenu(menu)

    def _on_selection_toggled(self, checked: bool):
        config.set("general", "enable_selection_trigger", checked)
        self.toggle_selection_listener.emit(checked)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Single click toggles floating window
            self.toggle_window_requested.emit()

    def _open_config_file(self):
        cfg_path = config.config_path
        if os.name == 'nt':
            os.startfile(str(cfg_path))
        else:
            subprocess.run(["xdg-open", str(cfg_path)])

    def update_hotkey_labels(self):
        snip_hk = config.get("general", "hotkey_screenshot", default="Alt+Q").upper()
        self.action_snip.setText(f"框选识图翻译 ({snip_hk})")
        win_hk = config.get("general", "hotkey_toggle_window", default="Alt+W").upper()
        self.action_win.setText(f"打开悬浮窗 ({win_hk})")
