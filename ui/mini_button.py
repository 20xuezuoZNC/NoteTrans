from PySide6.QtCore import Qt, QTimer, Signal, QPoint
from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QGraphicsDropShadowEffect
from PySide6.QtGui import QColor, QCursor, QGuiApplication
from ui.styles import LIGHT_STYLE
from config import config

class MiniTriggerButton(QWidget):
    """
    Micro floating button [译] that pops up right next to the mouse cursor after text selection.
    Uses QCursor.pos() for DPI-independent logical coordinates.
    Triggers safely on mouse click release without disturbing underlying document focus.
    """
    trigger_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self.setFixedSize(38, 38)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.btn = QPushButton("译", self)
        self.btn.setObjectName("MiniButton")
        self.btn.setFixedSize(30, 30)
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.setToolTip("点击翻译选中文本 (或直接单击鼠标右键)")
        self.btn.clicked.connect(self._on_button_clicked)

        # Shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 2)
        self.btn.setGraphicsEffect(shadow)

        layout.addWidget(self.btn)
        self.setStyleSheet(LIGHT_STYLE)

        # Auto-hide timer
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide_button)

    def show_near_cursor(self, offset_x: int = 15, offset_y: int = 15):
        """Displays the mini button right next to the current mouse cursor in logical coordinates."""
        pos = QCursor.pos()
        target_x = pos.x() + offset_x
        target_y = pos.y() + offset_y

        screen = QGuiApplication.screenAt(pos)
        if not screen:
            screen = QGuiApplication.primaryScreen()

        if screen:
            geom = screen.availableGeometry()
            # If button would fall off right or bottom edges, flip to opposite side of cursor
            if target_x + self.width() > geom.right():
                target_x = pos.x() - self.width() - offset_x
            if target_y + self.height() > geom.bottom():
                target_y = pos.y() - self.height() - offset_y

            target_x = max(geom.left() + 2, min(target_x, geom.right() - self.width() - 2))
            target_y = max(geom.top() + 2, min(target_y, geom.bottom() - self.height() - 2))

        self.move(target_x, target_y)
        self.show()
        self.raise_()

        timeout_sec = config.get("general", "mini_button_timeout", default=3.0)
        self.hide_timer.start(int(timeout_sec * 1000))

    def show_at(self, x: int, y: int):
        self.show_near_cursor()

    def hide_button(self):
        """Hides the button and stops the auto-hide timer."""
        self.hide_timer.stop()
        self.hide()

    def _on_button_clicked(self):
        self.hide_button()
        self.trigger_requested.emit()
