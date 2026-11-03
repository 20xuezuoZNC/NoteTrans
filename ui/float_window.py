import time
from typing import Optional
from PySide6.QtCore import Qt, QPoint, QSize, Signal, QThread, QObject, QTimer, QEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QPlainTextEdit, QComboBox, QGraphicsDropShadowEffect,
    QSizeGrip, QFrame
)
from PySide6.QtGui import QColor, QFont, QCursor, QGuiApplication, QIcon, QKeyEvent
import pyperclip

from config import config
from ui.styles import CERAMIC_WHITE_STYLE
from core.translator import translate

class TranslationWorker(QObject):
    finished = Signal(str, str)  # (translated_text, error_msg)

    def __init__(self, text: str, target_lang: str):
        super().__init__()
        self.text = text
        self.target_lang = target_lang

    def run(self):
        try:
            res = translate(self.text, self.target_lang)
            self.finished.emit(res, "")
        except Exception as e:
            self.finished.emit("", str(e))

class FloatTranslationWindow(QWidget):
    """
    Main lightweight floating translation card.
    Adopts High-End Ceramic White Theme (温润瓷白·法式高定典雅).
    Supports frameless drag anywhere on non-interactive surfaces, edge resizing,
    pin mode, auto-hide on blur, collapsible original text, and one-click Markdown note copying.
    """
    snip_requested = Signal()
    settings_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_pinned: bool = False
        self._drag_pos: Optional[QPoint] = None
        self._current_source_text: str = ""
        self._current_translated_text: str = ""
        self._worker_thread: Optional[QThread] = None
        self._show_time: float = 0.0
        self._has_focused: bool = False

        self._init_window_flags()
        self._init_ui()
        self.resize(400, 340)
        self.setMinimumSize(330, 240)
        self.setMaximumSize(750, 850)

    def _init_window_flags(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet(CERAMIC_WHITE_STYLE)

    def _init_ui(self):
        # Outer layout for margin to allow drop shadow
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(12, 12, 12, 12)

        # Card container widget
        self.card = QWidget(self)
        self.card.setObjectName("FloatCard")

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(10)

        # Soft warm ceramic ambient shadow
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(32)
        shadow.setColor(QColor(180, 160, 140, 50))
        shadow.setOffset(0, 8)
        self.card.setGraphicsEffect(shadow)

        # 1. Header Toolbar (Floating Island Pill Architecture)
        self.header_bar = QWidget(self.card)
        self.header_bar.setObjectName("HeaderBar")
        self.header_bar.setFixedHeight(30)

        header_layout = QHBoxLayout(self.header_bar)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)

        # Compact Luxury Brand Badge
        self.logo_badge = QLabel("◈ NoteTrans", self.header_bar)
        self.logo_badge.setObjectName("LogoBadge")
        self.logo_badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        header_layout.addWidget(self.logo_badge)

        # Compact Language Selector ComboBox Pill
        self.lang_combo = QComboBox(self.header_bar)
        self.lang_combo.setObjectName("LangSelector")
        self.lang_combo.setToolTip("选择目标语言 (默认中英自动互译)")
        self.lang_combo.addItem("中 ⇄ 英", "auto")
        self.lang_combo.addItem("中 → 英", "en")
        self.lang_combo.addItem("英 → 中", "zh-CN")
        self.lang_combo.addItem("中 → 日", "ja")
        self.lang_combo.addItem("中 → 韩", "ko")
        self.lang_combo.addItem("中 → 法", "fr")
        self.lang_combo.addItem("中 → 德", "de")
        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        header_layout.addWidget(self.lang_combo)

        header_layout.addStretch(1)

        # Minimalist Vector Header Buttons
        self.btn_snip = QPushButton("📷", self.header_bar)
        self.btn_snip.setProperty("class", "header-pill-btn")
        self.btn_snip.setToolTip("框选识图翻译 (Alt+Q)")
        self.btn_snip.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_snip.clicked.connect(self.snip_requested.emit)

        self.btn_pin = QPushButton("📌", self.header_bar)
        self.btn_pin.setObjectName("BtnPin")
        self.btn_pin.setProperty("class", "header-pill-btn")
        self.btn_pin.setToolTip("置顶窗口 (锁定不自动隐藏)")
        self.btn_pin.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pin.clicked.connect(self.toggle_pin)

        self.btn_close = QPushButton("✕", self.header_bar)
        self.btn_close.setObjectName("BtnClose")
        self.btn_close.setProperty("class", "header-pill-btn")
        self.btn_close.setToolTip("关闭 (隐藏)")
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.hide)

        header_layout.addWidget(self.btn_snip)
        header_layout.addWidget(self.btn_pin)
        header_layout.addWidget(self.btn_close)

        card_layout.addWidget(self.header_bar)

        # 2. Original Text Section (Quote card with amber accent bar)
        self.orig_section = QWidget(self.card)
        self.orig_section.setObjectName("OriginalSection")
        orig_layout = QVBoxLayout(self.orig_section)
        orig_layout.setContentsMargins(12, 8, 12, 8)
        orig_layout.setSpacing(4)

        orig_header_row = QHBoxLayout()
        orig_header_row.setSpacing(6)

        self.orig_tag = QLabel("SOURCE TEXT", self.orig_section)
        self.orig_tag.setObjectName("OriginalTag")

        self.orig_preview_lbl = QLabel("", self.orig_section)
        self.orig_preview_lbl.setObjectName("OriginalPreview")
        self.orig_preview_lbl.setVisible(False)

        self.retranslate_btn = QPushButton("重新翻译", self.orig_section)
        self.retranslate_btn.setObjectName("ReTranslateBtn")
        self.retranslate_btn.setToolTip("修改原文后点击重新翻译")
        self.retranslate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.retranslate_btn.clicked.connect(self._on_retranslate_clicked)

        self.toggle_orig_btn = QPushButton("收起 ▴", self.orig_section)
        self.toggle_orig_btn.setObjectName("ToggleOriginalBtn")
        self.toggle_orig_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_orig_btn.clicked.connect(self._toggle_original_expand)

        orig_header_row.addWidget(self.orig_tag)
        orig_header_row.addWidget(self.orig_preview_lbl, 1)
        orig_header_row.addStretch()
        orig_header_row.addWidget(self.retranslate_btn)
        orig_header_row.addWidget(self.toggle_orig_btn)
        orig_layout.addLayout(orig_header_row)

        self.orig_text_edit = QPlainTextEdit(self.orig_section)
        self.orig_text_edit.setObjectName("OriginalInput")
        self.orig_text_edit.setFixedHeight(48)
        self.orig_text_edit.setPlaceholderText("等待划词或输入待翻译文本...")
        orig_layout.addWidget(self.orig_text_edit)

        card_layout.addWidget(self.orig_section)

        # 3. Translated Hero Text Section
        self.trans_text_edit = QTextEdit(self.card)
        self.trans_text_edit.setObjectName("TranslatedText")
        self.trans_text_edit.setReadOnly(True)
        self.trans_text_edit.setPlaceholderText("等待划词或截图输入...")
        card_layout.addWidget(self.trans_text_edit, 1)

        # Engine Badge Row
        badge_row = QHBoxLayout()
        badge_row.setContentsMargins(4, 0, 4, 0)
        self.engine_badge = QLabel("◈ 微软 Bing • 极速直连", self.card)
        self.engine_badge.setObjectName("EngineBadge")
        badge_row.addStretch()
        badge_row.addWidget(self.engine_badge)
        card_layout.addLayout(badge_row)

        # 4. Bottom Action Dock
        self.bottom_bar = QWidget(self.card)
        self.bottom_bar.setObjectName("BottomBar")
        bottom_layout = QHBoxLayout(self.bottom_bar)
        bottom_layout.setContentsMargins(0, 2, 0, 0)
        bottom_layout.setSpacing(8)

        self.btn_copy_trans = QPushButton("◈  复制译文", self.bottom_bar)
        self.btn_copy_trans.setObjectName("BtnCopyTrans")
        self.btn_copy_trans.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy_trans.clicked.connect(self._copy_translation)

        self.btn_copy_both = QPushButton("📝 原文 + 译文", self.bottom_bar)
        self.btn_copy_both.setObjectName("BtnCopyNote")
        self.btn_copy_both.setToolTip("按 Markdown 引用格式复制原文与译文，方便直接粘贴入笔记")
        self.btn_copy_both.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy_both.clicked.connect(self._copy_both_markdown)

        self.btn_settings = QPushButton("⚙", self.bottom_bar)
        self.btn_settings.setObjectName("BtnSettings")
        self.btn_settings.setToolTip("设置与配置")
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.clicked.connect(self.settings_requested.emit)

        self.size_grip = QSizeGrip(self.bottom_bar)
        self.size_grip.setFixedSize(14, 14)

        bottom_layout.addWidget(self.btn_copy_trans)
        bottom_layout.addWidget(self.btn_copy_both)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btn_settings)
        bottom_layout.addWidget(self.size_grip)

        card_layout.addWidget(self.bottom_bar)
        outer_layout.addWidget(self.card)

        self._update_engine_badge()

        # Non-interactive labels pass through mouse events so drag works seamlessly across them
        self.orig_tag.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.orig_preview_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.engine_badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        # Universal smooth dragging across all container surfaces
        for panel in (self.card, self.header_bar, self.bottom_bar, self.orig_section):
            panel.installEventFilter(self)

    def _update_engine_badge(self):
        """Updates the engine badge based on current configuration."""
        provider = config.get("translation", "provider", default="bing")
        if provider == "bing":
            self.engine_badge.setText("◈ 微软 Bing • 极速直连")
        elif provider == "youdao":
            self.engine_badge.setText("◈ 网易有道 • 极速直连")
        elif provider == "google":
            self.engine_badge.setText("◈ Google 网页翻译")
        elif provider == "openai":
            model = config.get("translation", "openai", "model", default="LLM")
            self.engine_badge.setText(f"◈ {model} • AI 润色")
        else:
            self.engine_badge.setText("◈ 智能引擎 • 极速直连")

    def toggle_pin(self):
        """Toggles pinned / always-on-top state."""
        self.is_pinned = not self.is_pinned
        if self.is_pinned:
            self.btn_pin.setProperty("class", "header-pill-btn pinned")
            self.btn_pin.setToolTip("已置顶锁定 (失去焦点不会自动隐藏)")
            self.btn_pin.setText("📌")
        else:
            self.btn_pin.setProperty("class", "header-pill-btn")
            self.btn_pin.setToolTip("未锁定 (失去焦点将自动隐藏)")
            self.btn_pin.setText("📌")
        
        self.btn_pin.style().unpolish(self.btn_pin)
        self.btn_pin.style().polish(self.btn_pin)

    def changeEvent(self, event):
        """Auto-hide when window loses focus, if not pinned."""
        if event.type() == QEvent.Type.ActivationChange:
            if self.isActiveWindow():
                self._has_focused = True
            elif not self.is_pinned and self._has_focused:
                if time.time() - self._show_time > 0.8:
                    if config.get("general", "auto_hide_on_blur", default=True):
                        QTimer.singleShot(250, self._check_and_hide_on_blur)
        super().changeEvent(event)

    def _check_and_hide_on_blur(self):
        if not self.isActiveWindow() and not self.is_pinned and self._has_focused:
            if time.time() - self._show_time > 0.8:
                self.hide()

    def _toggle_original_expand(self):
        """Expands or collapses original text editor."""
        is_visible = self.orig_text_edit.isVisible()
        if is_visible:
            # Collapse
            self.orig_text_edit.setVisible(False)
            self.retranslate_btn.setVisible(False)
            preview = self._current_source_text.replace("\n", " ").strip()
            if len(preview) > 30:
                preview = preview[:30] + "..."
            self.orig_preview_lbl.setText(preview)
            self.orig_preview_lbl.setVisible(True)
            self.toggle_orig_btn.setText("展开 ▾")
            self.resize(self.width(), max(240, self.height() - 50))
        else:
            # Expand
            self.orig_preview_lbl.setVisible(False)
            self.orig_text_edit.setPlainText(self._current_source_text)
            self.orig_text_edit.setVisible(True)
            self.retranslate_btn.setVisible(True)
            self.toggle_orig_btn.setText("收起 ▴")
            self.resize(self.width(), min(850, self.height() + 50))

    def set_content(self, source_text: str, auto_translate: bool = True):
        """Sets source text and begins translation."""
        self._current_source_text = source_text.strip()
        self.orig_text_edit.setPlainText(self._current_source_text)
        preview = self._current_source_text.replace("\n", " ").strip()
        if len(preview) > 30:
            preview = preview[:30] + "..."
        self.orig_preview_lbl.setText(preview)
        
        if not self._current_source_text:
            self.trans_text_edit.setHtml("<span style='color: #a8a29e; font-size: 14px;'>等待划词或截图输入...</span>")
            return

        if auto_translate:
            self.start_translation()

    def start_translation(self):
        """Executes translation in background QThread."""
        if not self._current_source_text:
            return

        self._update_engine_badge()
        self.trans_text_edit.setHtml("<span style='color: #b45309; font-size: 14px;'><i>◈ 正在翻译中...</i></span>")

        # Cleanup existing thread if running
        if self._worker_thread and self._worker_thread.isRunning():
            self._worker_thread.quit()
            self._worker_thread.wait()

        target_lang = self.lang_combo.currentData()
        self._worker_thread = QThread()
        self._worker = TranslationWorker(self._current_source_text, target_lang)
        self._worker.moveToThread(self._worker_thread)

        self._worker_thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_translation_finished, Qt.ConnectionType.QueuedConnection)
        self._worker.finished.connect(self._worker_thread.quit)

        self._worker_thread.start()

    def _on_translation_finished(self, result: str, error: str):
        if error:
            self._current_translated_text = ""
            error_html = (
                "<div style='color: #dc2626; font-size: 13px; line-height: 1.6;'>"
                "<b>翻译失败</b>: 无法连接翻译服务。<br>"
                "<span style='color: #78716c; font-size: 12px;'>"
                "• 国内环境推荐使用默认的 <b>微软 Bing</b> 或 <b>网易有道</b> 翻译源。<br>"
                "• 如需切换翻译源或配置大模型，请点击右下角设置 ⚙。</span>"
                "</div>"
            )
            self.trans_text_edit.setHtml(error_html)
            return

        if not result:
            result = self._current_source_text

        self._current_translated_text = result
        formatted = result.replace("\n", "<br>")
        self.trans_text_edit.setHtml(f"<div style='line-height: 1.6; font-size: 15.5px; font-weight: 600; color: #1c1917;'>{formatted}</div>")

    def _on_retranslate_clicked(self):
        self._current_source_text = self.orig_text_edit.toPlainText().strip()
        self.start_translation()

    def _on_lang_changed(self):
        if self._current_source_text:
            self.start_translation()

    def _copy_translation(self):
        """Copies translation to clipboard with visual feedback."""
        if not self._current_translated_text:
            return
        pyperclip.copy(self._current_translated_text)
        self._show_button_feedback(self.btn_copy_trans, "已复制 ✓", "◈  复制译文")

    def _copy_both_markdown(self):
        """Copies Markdown quote format (> 原文 \n\n 译文) for note-taking apps."""
        if not self._current_source_text and not self._current_translated_text:
            return
        
        orig_quoted = "\n".join([f"> {line}" for line in self._current_source_text.splitlines()])
        markdown_note = f"{orig_quoted}\n\n{self._current_translated_text}"
        pyperclip.copy(markdown_note)
        self._show_button_feedback(self.btn_copy_both, "已复制 ✓", "📝 原文 + 译文")

    def _show_button_feedback(self, button: QPushButton, feedback_text: str, original_text: str):
        button.setText(feedback_text)
        button.setProperty("class", "success")
        button.style().unpolish(button)
        button.style().polish(button)

        QTimer.singleShot(1500, lambda: self._reset_button_feedback(button, original_text))

    def _reset_button_feedback(self, button: QPushButton, original_text: str):
        button.setText(original_text)
        button.setProperty("class", "")
        button.style().unpolish(button)
        button.style().polish(button)

    def show_at_cursor(self, offset_x: int = 15, offset_y: int = 15):
        """Displays the floating window near current mouse cursor.
        If already visible, keeps current position without jumping/flickering.
        """
        self._show_time = time.time()
        self._has_focused = False

        if self.isVisible():
            self.raise_()
            self.activateWindow()
            return

        cursor_pos = QCursor.pos()
        target_x = cursor_pos.x() + offset_x
        target_y = cursor_pos.y() + offset_y

        screen = QGuiApplication.screenAt(cursor_pos)
        if not screen:
            screen = QGuiApplication.primaryScreen()

        if screen:
            geom = screen.availableGeometry()
            if target_x + self.width() > geom.right():
                target_x = cursor_pos.x() - self.width() - offset_x
            if target_y + self.height() > geom.bottom():
                target_y = cursor_pos.y() - self.height() - offset_y

            target_x = max(geom.left() + 5, min(target_x, geom.right() - self.width() - 5))
            target_y = max(geom.top() + 5, min(target_y, geom.bottom() - self.height() - 5))

        self.setGeometry(target_x, target_y, self.width(), self.height())
        self.show()
        self.raise_()
        self.activateWindow()

    # Universal silky dragging for frameless window
    def eventFilter(self, watched, event):
        """Intercepts mouse events on card and sub-panels to allow dragging from any non-interactive surface."""
        drag_panels = (
            getattr(self, "card", None),
            getattr(self, "header_bar", None),
            getattr(self, "bottom_bar", None),
            getattr(self, "orig_section", None)
        )
        if watched and watched in drag_panels:
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    global_pos = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
                    local_pos = self.mapFromGlobal(global_pos)
                    child = self.childAt(local_pos)
                    if not isinstance(child, (QPushButton, QTextEdit, QPlainTextEdit, QComboBox, QSizeGrip)):
                        self._drag_pos = global_pos - self.frameGeometry().topLeft()
                        return True

            elif event.type() == QEvent.Type.MouseMove:
                if self._drag_pos and (event.buttons() & Qt.MouseButton.LeftButton):
                    global_pos = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
                    self.move(global_pos - self._drag_pos)
                    return True

            elif event.type() == QEvent.Type.MouseButtonRelease:
                if self._drag_pos:
                    self._drag_pos = None
                    return True

        return super().eventFilter(watched, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.pos())
            if not isinstance(child, (QPushButton, QTextEdit, QPlainTextEdit, QComboBox, QSizeGrip)):
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos and (event.buttons() & Qt.MouseButton.LeftButton):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)
