import os
import subprocess
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QCheckBox, QPushButton, QGroupBox, QFormLayout,
    QMessageBox
)
from config import config

class SettingsDialog(QDialog):
    """Configuration dialog for NoteTrans."""
    settings_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("NoteTrans 设置")
        self.setFixedSize(510, 530)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #fafaf9;
                color: #1c1917;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            }
            QGroupBox {
                background: #ffffff;
                border: 1px solid #e7e5e4;
                border-radius: 10px;
                margin-top: 12px;
                padding: 16px 14px 12px 14px;
                font-weight: 700;
                color: #44403c;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: #1c1917;
                font-size: 12px;
            }
            QLineEdit, QComboBox {
                background-color: #ffffff;
                border: 1px solid #e7e5e4;
                border-radius: 6px;
                padding: 5px 8px;
                color: #1c1917;
                font-size: 12px;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #b45309;
            }
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #e7e5e4;
                border-radius: 7px;
                padding: 6px 16px;
                color: #44403c;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #f5f5f4;
                color: #1c1917;
            }
            QPushButton:default {
                background-color: #1c1917;
                color: #fafaf9;
                border: 1px solid #1c1917;
                font-weight: 600;
            }
            QPushButton:default:hover {
                background-color: #292524;
            }
        """)

        self._init_ui()
        self._load_values()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 1. Translation Settings
        trans_group = QGroupBox("翻译引擎与接口设置", self)
        trans_layout = QFormLayout(trans_group)
        trans_layout.setSpacing(8)

        self.provider_combo = QComboBox()
        self.provider_combo.addItem("微软 Bing 翻译 (国内免翻墙直连，推荐)", "bing")
        self.provider_combo.addItem("网易有道翻译 (国内免翻墙直连)", "youdao")
        self.provider_combo.addItem("Google 网页翻译 (需科学上网/海外节点)", "google")
        self.provider_combo.addItem("大模型 API (DeepSeek / 硅基流动 / OpenAI 等)", "openai")
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        trans_layout.addRow("翻译源:", self.provider_combo)

        # Preset selector for LLM providers
        self.preset_combo = QComboBox()
        self.preset_combo.addItem("快速填入推荐服务预设...", "")
        self.preset_combo.addItem("★ 硅基流动 SiliconFlow (含永久免费模型 Qwen2.5/GLM-4，推荐)", "siliconflow")
        self.preset_combo.addItem("★ 智谱 AI (GLM-4-Flash 官方永久免费，极速推荐)", "zhipu")
        self.preset_combo.addItem("★ DeepSeek 官方 API (高性价比，国内直连)", "deepseek")
        self.preset_combo.addItem("OpenAI 官方 (需海外环境与 API Key)", "openai_official")
        self.preset_combo.addItem("本地 Ollama (完全离线本地运行)", "ollama")
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        trans_layout.addRow("服务预设:", self.preset_combo)

        self.base_url_input = QLineEdit()
        self.base_url_input.setPlaceholderText("https://api.siliconflow.cn/v1")
        trans_layout.addRow("Base URL:", self.base_url_input)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("sk-...")
        trans_layout.addRow("API Key:", self.api_key_input)

        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("Qwen/Qwen2.5-7B-Instruct 或 deepseek-chat 等")
        trans_layout.addRow("Model 名称:", self.model_input)

        self.tip_lbl = QLabel(
            "<span style='color: #64748b; font-size: 11px;'>"
            "💡 <b>国内使用说明</b>：<br>"
            "• 默认使用<b>微软 Bing</b>或<b>网易有道</b>，国内无需代理、免 Key 开箱即用。<br>"
            "• 若使用大模型，推荐<b>硅基流动</b>（提供 Qwen2.5 永久免费模型）或 <b>DeepSeek</b>。"
            "</span>"
        )
        self.tip_lbl.setWordWrap(True)
        trans_layout.addRow("", self.tip_lbl)

        layout.addWidget(trans_group)

        # 2. General & Hotkeys
        gen_group = QGroupBox("快捷键与交互行为", self)
        gen_layout = QFormLayout(gen_group)
        gen_layout.setSpacing(6)

        self.hotkey_snip_input = QLineEdit()
        gen_layout.addRow("框选识图快捷键:", self.hotkey_snip_input)

        self.hotkey_win_input = QLineEdit()
        gen_layout.addRow("唤醒悬浮窗快捷键:", self.hotkey_win_input)

        self.check_selection = QCheckBox("开启划词与右键快捷触发 ([译] 悬浮小球)")
        gen_layout.addRow("", self.check_selection)

        self.check_blur_hide = QCheckBox("未置顶时失去焦点自动隐藏悬浮窗")
        gen_layout.addRow("", self.check_blur_hide)

        layout.addWidget(gen_group)

        # 3. Action Buttons
        btn_layout = QHBoxLayout()

        self.btn_open_file = QPushButton("打开 config.json")
        self.btn_open_file.clicked.connect(self._open_config_file)
        btn_layout.addWidget(self.btn_open_file)

        btn_layout.addStretch()

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("保存设置")
        self.btn_save.setDefault(True)
        self.btn_save.clicked.connect(self._save_values)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _load_values(self):
        # Provider
        provider = config.get("translation", "provider", default="bing")
        if provider == "free":
            provider = "bing"
        idx = self.provider_combo.findData(provider)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)

        # OpenAI
        openai_cfg = config.get("translation", "openai", default={})
        self.base_url_input.setText(openai_cfg.get("base_url", "https://api.siliconflow.cn/v1"))
        self.api_key_input.setText(openai_cfg.get("api_key", ""))
        self.model_input.setText(openai_cfg.get("model", "Qwen/Qwen2.5-7B-Instruct"))

        # Hotkeys
        self.hotkey_snip_input.setText(config.get("general", "hotkey_screenshot", default="alt+q"))
        self.hotkey_win_input.setText(config.get("general", "hotkey_toggle_window", default="alt+w"))

        # Checks
        self.check_selection.setChecked(config.get("general", "enable_selection_trigger", default=True))
        self.check_blur_hide.setChecked(config.get("general", "auto_hide_on_blur", default=True))

        self._on_provider_changed()

    def _on_provider_changed(self):
        is_openai = (self.provider_combo.currentData() == "openai")
        self.preset_combo.setEnabled(is_openai)
        self.base_url_input.setEnabled(is_openai)
        self.api_key_input.setEnabled(is_openai)
        self.model_input.setEnabled(is_openai)

    def _on_preset_changed(self):
        preset = self.preset_combo.currentData()
        if preset == "siliconflow":
            self.base_url_input.setText("https://api.siliconflow.cn/v1")
            self.model_input.setText("Qwen/Qwen2.5-7B-Instruct")
            if not self.api_key_input.text().strip():
                self.api_key_input.setPlaceholderText("请输入硅基流动 API Key (sk-...)")
        elif preset == "zhipu":
            self.base_url_input.setText("https://open.bigmodel.cn/api/paas/v4")
            self.model_input.setText("glm-4-flash")
            if not self.api_key_input.text().strip():
                self.api_key_input.setPlaceholderText("请输入智谱 API Key")
        elif preset == "deepseek":
            self.base_url_input.setText("https://api.deepseek.com")
            self.model_input.setText("deepseek-chat")
            if not self.api_key_input.text().strip():
                self.api_key_input.setPlaceholderText("请输入 DeepSeek API Key (sk-...)")
        elif preset == "openai_official":
            self.base_url_input.setText("https://api.openai.com/v1")
            self.model_input.setText("gpt-4o-mini")
            if not self.api_key_input.text().strip():
                self.api_key_input.setPlaceholderText("请输入 OpenAI API Key (sk-...)")
        elif preset == "ollama":
            self.base_url_input.setText("http://localhost:11434/v1")
            self.model_input.setText("qwen2.5:7b")
            self.api_key_input.setText("ollama")

    def _save_values(self):
        # Save provider
        config.set("translation", "provider", self.provider_combo.currentData())

        # Save openai
        config.set("translation", "openai", "base_url", self.base_url_input.text().strip())
        config.set("translation", "openai", "api_key", self.api_key_input.text().strip())
        config.set("translation", "openai", "model", self.model_input.text().strip())

        # Save general
        config.set("general", "hotkey_screenshot", self.hotkey_snip_input.text().strip())
        config.set("general", "hotkey_toggle_window", self.hotkey_win_input.text().strip())
        config.set("general", "enable_selection_trigger", self.check_selection.isChecked())
        config.set("general", "auto_hide_on_blur", self.check_blur_hide.isChecked())

        self.settings_changed.emit()
        self.accept()

    def _open_config_file(self):
        cfg_path = config.config_path
        if os.name == 'nt':
            os.startfile(str(cfg_path))
        else:
            subprocess.run(["xdg-open", str(cfg_path)])
