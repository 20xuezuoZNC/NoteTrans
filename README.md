# NoteTrans - 轻量级桌面划词与截图翻译助手

> 专为“边看资料边记笔记”场景设计的轻量级、低内存 Windows 悬浮窗翻译工具。高定典雅 UI 设计、支持毫秒级划词、多屏高分屏 OCR 识图与大模型/免费翻译引擎。

<div align="center">
  <img src="assets/screenshot.png" alt="NoteTrans 悬浮窗界面" width="380" />
</div>

---

## ✨ 核心特性

1. **温润瓷白高定 UI 设计**
   * 采用微质感陶瓷渐变底色与法式温润琥珀强调条，视觉极简雅致。
   * 全无边框设计，全卡片任意空白区域与徽标均支持丝滑平滑拖拽。
   * 自适应收缩：最小仅需 330px 宽度，小巧灵动，绝不遮挡文档主体。

2. **非侵入式划词与右键唤醒**
   * 划词或双击选词后，鼠标右下方即刻浮出微型 `[译]` 按钮（停留 3 秒，不抢占焦点）。
   * 期间**左键点击小球**或**直接单击鼠标右键**，一键抓取文本并翻译。
   * 无损剪贴板技术：自动备份与恢复原剪贴板内容，绝不污染原有复制历史。

3. **多屏高分屏屏幕框选识图 (OCR)**
   * 全局快捷键 `Alt + Q`、悬浮窗顶部相机图标或托盘菜单一键唤起全屏截图。
   * 完美适配 Windows 125%/150%/200% 等高 DPI 缩放，像素级对齐无偏移。
   * 内置本地 `RapidOCR` 轻量推理引擎，开箱即用，无需庞大 CUDA 环境。

4. **专为笔记设计的极简悬浮窗**
   * **置顶锁定 (Pin 📌)**：
     * 未锁定（默认）：光标离开悬浮窗、切换到笔记软件打字时自动隐藏，轻便不挡屏。
     * 锁定状态：悬浮窗常驻最前端，方便对照长篇学术论文或技术文档。
   * **原文折叠编辑**：默认单行折叠预览，展开后可直接修改 OCR 误识文本并一键“重新翻译”。
   * **一键复制笔记格式**：
     * ◈ `[复制译文]`：一键复制纯净译文。
     * 📝 `[原文 + 译文]`：按 Markdown 引用格式（`> 原文 \n\n 译文`）排版，直接粘贴至 Obsidian、Notion 或 Logseq。

5. **多翻译引擎与大模型支持**
   * **国内免费免配置**：内置**微软 Bing** 与 **网易有道** 极速直连源，免挂梯、免 Key、开箱即用。
   * **Google 翻译**：国际通用网页翻译接口。
   * **大模型兼容模式**：支持 SiliconFlow (硅基流动免费 Qwen2.5/DeepSeek)、OpenAI、通义千问、Ollama 等所有兼容 `/v1/chat/completions` 的 API。

6. **系统托盘常驻**
   * 随开随用，不占用 Windows 任务栏位置。
   * 托盘菜单可快速开启/暂停划词监听、打开设置或退出程序。

---

## 🚀 启动与使用

### 方式一：一键启动（推荐）
直接双击运行项目根目录下的 **`run.bat`**。

### 方式二：命令行启动
```bash
# 激活虚拟环境
.venv\Scripts\activate

# 启动 NoteTrans
python main.py
```

---

## ⌨️ 默认快捷键

| 功能 | 默认快捷键 | 说明 |
| :--- | :--- | :--- |
| **框选识图翻译** | `Alt + Q` | 全屏暗色遮罩，按住左键拖拽选区，按 Esc 或右键取消 |
| **显示/隐藏悬浮窗** | `Alt + W` | 快速唤出主翻译卡片 |
| **划词快捷翻译** | 选词后按 `[译]` 或单击鼠标右键 | 自动提取并翻译 |

*注：快捷键可在托盘菜单或悬浮窗底部的“设置”中随时自定义。*

---

## ⚙️ 配置文件说明 (`config.json`)

程序首次启动会自动生成 `config.json`，支持在图形界面设置或直接编辑：

```json
{
  "general": {
    "hotkey_screenshot": "alt+q",
    "hotkey_toggle_window": "alt+w",
    "enable_selection_trigger": true,
    "mini_button_timeout": 3.0,
    "auto_hide_on_blur": true,
    "theme": "light"
  },
  "translation": {
    "provider": "free",
    "target_lang": "auto",
    "openai": {
      "base_url": "https://api.openai.com/v1",
      "api_key": "",
      "model": "gpt-4o-mini",
      "temperature": 0.3,
      "system_prompt": "You are a professional, accurate translator..."
    }
  },
  "ocr": {
    "engine": "rapidocr",
    "auto_copy_ocr": false
  }
}
```

---

## 📁 目录结构

```
.
├── main.py                   # 程序主入口与控制器
├── config.py                 # 配置加载与管理
├── config.json               # 本地配置文件 (自动生成)
├── requirements.txt          # Python 依赖清单
├── run.bat                   # Windows 一键启动脚本
├── README.md                 # 项目文档
│
├── core/                     # 核心引擎模块
│   ├── translator.py         # 翻译引擎 (免费接口 + 大模型接口)
│   ├── ocr_engine.py         # RapidOCR 识别与智能排版
│   ├── selection_listener.py # 鼠标划词监听与剪贴板无损抓取
│   └── hotkey_manager.py     # 全局热键管理器
│
└── ui/                       # 界面组件
    ├── styles.py             # 样式表与调色板
    ├── float_window.py       # 主翻译悬浮窗卡片
    ├── mini_button.py        # [译] 悬浮微型按钮
    ├── snipping_widget.py    # 全屏高 DPI 截图遮罩层
    ├── settings_dialog.py    # 设置窗口
    └── tray_icon.py          # 系统托盘与菜单
```
