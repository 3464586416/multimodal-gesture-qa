"""深色主题样式表与调色板。"""

# 统一调色板（供 QSS 与动态控件共用）
PALETTE = {
    "bg":        "#0f1420",   # 窗口底色
    "surface":   "#161d2b",   # 卡片/面板
    "surface2":  "#1d2635",   # 悬浮/输入框
    "border":    "#2a3648",
    "border_hi": "#3b82f6",
    "text":      "#e6edf3",
    "text_dim":  "#8b98a9",
    "accent":    "#3b82f6",   # 主蓝
    "accent2":   "#06b6d4",   # 青
    "good":      "#22c55e",
    "warn":      "#f59e0b",
    "bad":       "#ef4444",
    "purple":    "#8b5cf6",
}

DARK_QSS = f"""
* {{
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13px;
    color: {PALETTE['text']};
}}

QMainWindow, QWidget#Central {{
    background: {PALETTE['bg']};
}}

/* ===== 卡片面板 ===== */
QFrame#Card {{
    background: {PALETTE['surface']};
    border: 1px solid {PALETTE['border']};
    border-radius: 12px;
}}
QFrame#Card QGroupBox {{
    border: none; margin: 0; padding: 0;
}}
QLabel#CardTitle {{
    color: {PALETTE['text']};
    font-size: 14px;
    font-weight: 700;
    background: transparent;
}}
QLabel#AccentBar {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {PALETTE['accent']}, stop:1 {PALETTE['accent2']});
    border-radius: 2px;
    max-width: 4px;
}}

/* ===== 顶部标题栏 ===== */
QLabel#AppTitle {{
    font-size: 18px; font-weight: 800;
    color: {PALETTE['text']};
    background: transparent;
}}
QLabel#AppSubtitle {{
    font-size: 12px; color: {PALETTE['text_dim']};
    background: transparent;
}}

/* ===== 状态徽章 ===== */
QLabel#StatusBadge {{
    padding: 5px 14px;
    border-radius: 14px;
    font-weight: 700;
    font-size: 12px;
    background: {PALETTE['surface2']};
    color: {PALETTE['text']};
    border: 1px solid {PALETTE['border']};
}}

/* ===== 按钮 ===== */
QPushButton {{
    background: {PALETTE['surface2']};
    border: 1px solid {PALETTE['border']};
    border-radius: 9px;
    padding: 9px 16px;
    font-weight: 600;
    color: {PALETTE['text']};
}}
QPushButton:hover {{
    background: #24324a;
    border-color: {PALETTE['border_hi']};
}}
QPushButton:pressed {{ background: #1a2436; }}
QPushButton:disabled {{
    color: {PALETTE['text_dim']};
    background: {PALETTE['surface']};
    border-color: {PALETTE['border']};
}}

QPushButton[role="primary"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {PALETTE['accent']}, stop:1 {PALETTE['accent2']});
    border: none; color: #ffffff; font-weight: 700;
}}
QPushButton[role="primary"]:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #2f6fe0, stop:1 #0891b2);
}}
QPushButton[role="primary"]:disabled {{
    background: {PALETTE['surface2']}; color: {PALETTE['text_dim']};
}}

QPushButton[role="danger"] {{
    background: {PALETTE['bad']};
    border: none; color: #ffffff; font-weight: 700;
}}
QPushButton[role="danger"]:hover {{ background: #dc2626; }}

QPushButton[role="start"] {{
    background: {PALETTE['good']};
    border: none; color: #ffffff; font-weight: 800; font-size: 15px;
    padding: 12px 40px; border-radius: 12px;
}}
QPushButton[role="start"]:hover {{ background: #16a34a; }}
QPushButton[role="start"]:disabled {{
    background: {PALETTE['surface2']}; color: {PALETTE['text_dim']};
}}

QPushButton[role="toggle_off"] {{
    background: {PALETTE['surface2']};
    border: 1px solid {PALETTE['border']};
}}
QPushButton[role="toggle_on"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {PALETTE['accent']}, stop:1 {PALETTE['accent2']});
    border: none; color: #ffffff; font-weight: 700;
}}

/* ===== 下拉框 ===== */
QComboBox {{
    background: {PALETTE['surface2']};
    border: 1px solid {PALETTE['border']};
    border-radius: 8px;
    padding: 7px 10px;
    color: {PALETTE['text']};
}}
QComboBox:hover {{ border-color: {PALETTE['border_hi']}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {PALETTE['surface2']};
    border: 1px solid {PALETTE['border']};
    selection-background-color: {PALETTE['accent']};
    color: {PALETTE['text']};
    outline: none;
}}

/* ===== 输入框 ===== */
QLineEdit {{
    background: {PALETTE['surface2']};
    border: 1px solid {PALETTE['border']};
    border-radius: 9px;
    padding: 10px 12px;
    color: {PALETTE['text']};
    selection-background-color: {PALETTE['accent']};
}}
QLineEdit:focus {{ border-color: {PALETTE['border_hi']}; }}

/* ===== 文本区 ===== */
QTextEdit, QPlainTextEdit {{
    background: {PALETTE['surface2']};
    border: 1px solid {PALETTE['border']};
    border-radius: 10px;
    padding: 8px;
    color: {PALETTE['text']};
}}

/* ===== 进度条（确认进度）===== */
QProgressBar {{
    background: {PALETTE['surface2']};
    border: 1px solid {PALETTE['border']};
    border-radius: 8px;
    height: 10px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    border-radius: 7px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {PALETTE['accent']}, stop:1 {PALETTE['accent2']});
}}

/* ===== 视频/图片显示区 ===== */
QLabel#VideoCanvas, QLabel#ObjectPreview {{
    background: #060a12;
    border: 1px solid {PALETTE['border']};
    border-radius: 12px;
    color: {PALETTE['text_dim']};
    font-size: 15px;
}}

/* ===== 历史记录列表 ===== */
QListWidget {{
    background: {PALETTE['surface2']};
    border: 1px solid {PALETTE['border']};
    border-radius: 10px;
    padding: 4px;
    outline: none;
}}
QListWidget::item {{
    padding: 8px 10px;
    border-radius: 7px;
    color: {PALETTE['text']};
}}
QListWidget::item:hover {{ background: #24324a; }}
QListWidget::item:selected {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {PALETTE['accent']}, stop:1 {PALETTE['accent2']});
    color: #ffffff;
}}

QScrollBar:vertical {{
    background: transparent; width: 10px; margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {PALETTE['border']}; border-radius: 5px; min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{ background: {PALETTE['text_dim']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{
    background: {PALETTE['border']}; border-radius: 5px; min-width: 24px;
}}

/* ===== 提示气泡 ===== */
QMessageBox {{ background: {PALETTE['surface']}; }}
QToolTip {{
    background: {PALETTE['surface2']};
    color: {PALETTE['text']};
    border: 1px solid {PALETTE['border_hi']};
    border-radius: 6px;
    padding: 6px;
}}
"""


def badge_style(kind: str) -> str:
    """按语义状态返回徽章内联样式。"""
    colors = {
        "idle":    (PALETTE['surface2'], PALETTE['text']),
        "perceive": (PALETTE['accent2'], "#ffffff"),
        "pointing": (PALETTE['warn'], "#111111"),
        "ready":   (PALETTE['good'], "#ffffff"),
        "asking":  (PALETTE['purple'], "#ffffff"),
        "error":   (PALETTE['bad'], "#ffffff"),
    }
    bg, fg = colors.get(kind, colors["idle"])
    return (f"background:{bg}; color:{fg}; border:none; "
            f"padding:5px 14px; border-radius:14px; font-weight:700; font-size:12px;")
