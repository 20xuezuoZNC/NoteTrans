from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QCursor, QGuiApplication, QPixmap

class SnippingOverlay(QWidget):
    """
    Full-screen translucent snipping overlay for region selection and OCR.
    Handles High-DPI screens, multi-monitor positions, and Esc/Right-click cancellation.
    """
    region_captured = Signal(QPixmap)
    cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self.start_pos: QPoint = QPoint()
        self.current_pos: QPoint = QPoint()
        self.is_selecting: bool = False
        self.full_pixmap: QPixmap = QPixmap()
        self.dpr: float = 1.0

    def start_capture(self):
        """Prepares and opens the snipping overlay over the current screen."""
        screen = QGuiApplication.screenAt(QCursor.pos())
        if not screen:
            screen = QGuiApplication.primaryScreen()

        geom = screen.geometry()
        self.dpr = screen.devicePixelRatio()

        # Grab high-res screen pixmap
        self.full_pixmap = screen.grabWindow(0)

        # Cover the target screen
        self.setGeometry(geom)
        self.is_selecting = False
        self.start_pos = QPoint()
        self.current_pos = QPoint()

        self.show()
        self.raise_()
        self.activateWindow()

    def get_selection_rect(self) -> QRect:
        """Returns normalized logical selection rectangle."""
        if not self.is_selecting and self.start_pos.isNull():
            return QRect()
        return QRect(self.start_pos, self.current_pos).normalized()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.pos()
            self.current_pos = event.pos()
            self.is_selecting = True
            self.update()
        elif event.button() == Qt.MouseButton.RightButton:
            # Right click cancels
            self.close()
            self.cancelled.emit()

    def mouseMoveEvent(self, event):
        if self.is_selecting:
            self.current_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_selecting:
            self.is_selecting = False
            rect = self.get_selection_rect()
            
            # Minimum selection threshold (8x8)
            if rect.width() >= 8 and rect.height() >= 8:
                # Convert logical rect to physical device pixel rect
                crop_x = int(rect.x() * self.dpr)
                crop_y = int(rect.y() * self.dpr)
                crop_w = int(rect.width() * self.dpr)
                crop_h = int(rect.height() * self.dpr)

                cropped_pixmap = self.full_pixmap.copy(crop_x, crop_y, crop_w, crop_h)
                self.close()
                self.region_captured.emit(cropped_pixmap)
            else:
                self.close()
                self.cancelled.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            self.cancelled.emit()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # 1. Draw the frozen full screen background
        if not self.full_pixmap.isNull():
            painter.drawPixmap(0, 0, self.width(), self.height(), self.full_pixmap)

        # 2. Draw dark semi-transparent veil
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        # 3. If dragging a selection, reveal the selected region clearly
        rect = self.get_selection_rect()
        if not rect.isEmpty() and (self.is_selecting or rect.width() > 0):
            # Draw original sharp screen inside selection
            source_crop_x = int(rect.x() * self.dpr)
            source_crop_y = int(rect.y() * self.dpr)
            source_crop_w = int(rect.width() * self.dpr)
            source_crop_h = int(rect.height() * self.dpr)
            sub_pix = self.full_pixmap.copy(source_crop_x, source_crop_y, source_crop_w, source_crop_h)
            painter.drawPixmap(rect, sub_pix)

            # Draw accent border
            pen = QPen(QColor(59, 130, 246), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawRect(rect)

            # Draw size badge
            badge_text = f"{rect.width()} × {rect.height()}"
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            badge_rect = QRect(rect.right() - 80, rect.bottom() + 6, 80, 22)
            if badge_rect.bottom() > self.height() - 5:
                badge_rect.moveBottom(rect.top() - 6)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(15, 23, 42, 200))
            painter.drawRoundedRect(badge_rect, 4, 4)

            painter.setPen(QColor(255, 255, 255))
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, badge_text)

        # 4. Top tip banner
        tip_text = "📷 拖拽鼠标左键框选文字区域 | 按 Esc 或鼠标右键取消"
        painter.setFont(QFont("Segoe UI", 10))
        tip_width = 340
        tip_rect = QRect((self.width() - tip_width) // 2, 20, tip_width, 30)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(15, 23, 42, 220))
        painter.drawRoundedRect(tip_rect, 6, 6)

        painter.setPen(QColor(241, 245, 249))
        painter.drawText(tip_rect, Qt.AlignmentFlag.AlignCenter, tip_text)
