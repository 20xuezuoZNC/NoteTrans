"""
High-End Ceramic White Theme (温润瓷白·法式高定典雅) for NoteTrans.
Inspired by B&O, high-end editorial magazines, and Apple Pro product design.
Warm pearlescent ceramic gradients, amber accents, fine typography, and pill architecture.
"""

CERAMIC_WHITE_STYLE = """
/* Global Card Base */
QWidget#FloatCard {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #fcfbfa);
    border: 1px solid #e7e5e4;
    border-radius: 18px;
}

QLabel {
    font-family: 'Segoe UI', 'SF Pro Display', 'Microsoft YaHei', sans-serif;
}

/* Header Brand Pill */
QLabel#LogoBadge {
    background: #f5f5f4;
    border: 1px solid #e7e5e4;
    border-radius: 12px;
    color: #44403c;
    font-size: 11px;
    font-weight: 700;
    padding: 2px 8px;
}

/* Language selector pill */
QComboBox#LangSelector {
    background: #fafaf9;
    border: 1px solid #e7e5e4;
    border-radius: 12px;
    padding: 2px 6px;
    font-size: 11px;
    font-weight: 600;
    color: #57534e;
    min-width: 68px;
    max-width: 82px;
}

QComboBox#LangSelector:hover {
    background: #f5f5f4;
    border-color: #d6d3d1;
    color: #1c1917;
}

QComboBox#LangSelector::drop-down {
    border: none;
    width: 14px;
}

QComboBox#LangSelector QAbstractItemView {
    background: #ffffff;
    border: 1px solid #e7e5e4;
    border-radius: 8px;
    selection-background-color: #f5f5f4;
    selection-color: #1c1917;
    outline: none;
    padding: 4px;
}

/* Top control buttons */
QPushButton.header-pill-btn {
    background: #fbfbfa;
    border: 1px solid #f0efed;
    border-radius: 12px;
    color: #78716c;
    font-size: 11px;
    min-width: 24px;
    min-height: 24px;
    max-width: 24px;
    max-height: 24px;
}

QPushButton.header-pill-btn:hover {
    background: #f5f5f4;
    border-color: #d6d3d1;
    color: #1c1917;
}

QPushButton#BtnPin.pinned {
    background: #fef3c7;
    border-color: #fde68a;
    color: #b45309;
}

QPushButton#BtnClose:hover {
    background: #fee2e2;
    border-color: #fca5a5;
    color: #dc2626;
}

/* Original text quote container */
QWidget#OriginalSection {
    background: #fdfbf7;
    border: 1px solid #f5ede4;
    border-left: 3px solid #d97706;
    border-radius: 10px;
}

QLabel#OriginalTag {
    color: #a8a29e;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1.2px;
    background: transparent;
    border: none;
}

QLabel#OriginalPreview {
    color: #78716c;
    font-size: 12px;
    font-style: italic;
    background: transparent;
    border: none;
}

QPlainTextEdit#OriginalInput {
    background: transparent;
    border: none;
    color: #78716c;
    font-size: 13px;
    line-height: 1.45;
    font-style: italic;
    padding: 2px;
}

QPushButton#ToggleOriginalBtn {
    background: transparent;
    border: none;
    color: #a8a29e;
    font-size: 10px;
    padding: 2px 5px;
    border-radius: 4px;
}

QPushButton#ToggleOriginalBtn:hover {
    color: #1c1917;
    background: #f5f5f4;
}

QPushButton#ReTranslateBtn {
    background: #ffffff;
    border: 1px solid #e7e5e4;
    border-radius: 5px;
    color: #78716c;
    font-size: 10px;
    padding: 2px 7px;
}

QPushButton#ReTranslateBtn:hover {
    background: #f5f5f4;
    border-color: #d6d3d1;
    color: #1c1917;
}

/* Translated hero text area */
QTextEdit#TranslatedText {
    background: transparent;
    border: none;
    font-size: 15.5px;
    font-weight: 600;
    color: #1c1917;
    padding: 4px 6px;
    line-height: 1.6;
    selection-background-color: #fef3c7;
    selection-color: #78350f;
}

QLabel#EngineBadge {
    color: #a8a29e;
    font-size: 10px;
    font-weight: 500;
    background: transparent;
    border: none;
}

/* Bottom Action Dock */
QWidget#BottomBar {
    background: transparent;
    border: none;
    padding: 0px;
}

QPushButton#BtnCopyTrans {
    background: #1c1917;
    border: 1px solid #1c1917;
    border-radius: 9px;
    color: #fafaf9;
    font-size: 12px;
    font-weight: 600;
    padding: 7px 18px;
}

QPushButton#BtnCopyTrans:hover {
    background: #292524;
    border-color: #292524;
}

QPushButton#BtnCopyTrans:pressed {
    background: #44403c;
}

QPushButton#BtnCopyTrans.success {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    color: #15803d;
}

QPushButton#BtnCopyNote {
    background: #ffffff;
    border: 1px solid #e7e5e4;
    border-radius: 9px;
    color: #57534e;
    font-size: 12px;
    font-weight: 500;
    padding: 7px 14px;
}

QPushButton#BtnCopyNote:hover {
    background: #f5f5f4;
    border-color: #d6d3d1;
    color: #1c1917;
}

QPushButton#BtnCopyNote:pressed {
    background: #e7e5e4;
}

QPushButton#BtnCopyNote.success {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    color: #15803d;
}

QPushButton#BtnSettings {
    background: #fafaf9;
    border: 1px solid #e7e5e4;
    border-radius: 15px;
    color: #a8a29e;
    font-size: 13px;
    min-width: 30px;
    min-height: 30px;
    max-width: 30px;
    max-height: 30px;
}

QPushButton#BtnSettings:hover {
    background: #f5f5f4;
    border-color: #d6d3d1;
    color: #44403c;
}

/* Mini trigger button (悬浮小「译」球) */
QPushButton#MiniButton {
    background: #1c1917;
    border: 1.5px solid #ffffff;
    border-radius: 15px;
    color: #fafaf9;
    font-size: 12px;
    font-weight: 700;
    text-align: center;
}

QPushButton#MiniButton:hover {
    background: #292524;
    color: #f59e0b;
}

/* Minimal ScrollBar */
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 4px;
    margin: 2px;
}

QScrollBar::handle:vertical {
    background: #e7e5e4;
    min-height: 20px;
    border-radius: 2px;
}

QScrollBar::handle:vertical:hover {
    background: #d6d3d1;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

# Alias for backwards compatibility
LIGHT_STYLE = CERAMIC_WHITE_STYLE
