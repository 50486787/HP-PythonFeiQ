"""资源模块 — 颜色常量、QSS 样式表、工具函数"""

# ========== 配色方案 ==========
HEADER_START = '#ffb74d'
HEADER_END = '#f5a623'
HEADER_TEXT = '#fff'
SIDEBAR_BG = '#faf9f6'
CONTACT_SELECTED = '#fff8f0'
CHAT_BG = '#fff'
BUBBLE_SELF_BG = '#f0f4fb'
BUBBLE_SELF_BORDER = '#dce8f6'
BUBBLE_OTHER_BG = '#f5f5f5'
BUBBLE_OTHER_BORDER = '#e0e0e0'
BTN_SEND = '#f5a623'
ONLINE_DOT = '#4caf50'
TIMESTAMP = '#999'

# 头像渐变色池（用于默认文字头像，按 user_id 哈希取稳定色）
AVATAR_COLORS = [
    ('#ffb74d', '#ff9800'), ('#ef9a9a', '#f44336'),
    ('#90caf9', '#2196f3'), ('#a5d6a7', '#4caf50'),
    ('#ce93d8', '#9c27b0'), ('#80cbc4', '#009688'),
    ('#ffcc80', '#ff6d00'), ('#bcaaa4', '#795548'),
]


def get_avatar_color(user_id: str) -> tuple:
    """根据 user_id 哈希取一个稳定的头像渐变色"""
    h = hash(user_id) % len(AVATAR_COLORS)
    return AVATAR_COLORS[h]


def format_size(size: int) -> str:
    """文件大小格式化"""
    if size >= 1024 * 1024 * 1024:
        return '%.1f GB' % (size / (1024 * 1024 * 1024))
    if size >= 1024 * 1024:
        return '%.1f MB' % (size / (1024 * 1024))
    if size >= 1024:
        return '%.1f KB' % (size / 1024)
    return '%d B' % size


# ========== 全局 QSS ==========
MAIN_QSS = """
QMainWindow {
    background: #fff;
}
QTreeWidget {
    background: #faf9f6;
    border: none;
    outline: none;
    font-size: 13px;
}
QTreeWidget::item {
    padding: 7px 14px;
    border: none;
}
QTreeWidget::item:selected {
    background: #fff8f0;
    color: #333;
}
QTreeWidget::branch {
    background: #faf9f6;
}
QSplitter::handle {
    background: #e8e4dc;
    width: 1px;
}
QScrollBar:vertical {
    width: 8px;
    background: transparent;
}
QScrollBar::handle:vertical {
    background: #d0d0d0;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    height: 8px;
    background: transparent;
}
QScrollBar::handle:horizontal {
    background: #d0d0d0;
    border-radius: 4px;
    min-width: 30px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}
QTextEdit {
    border: 1px solid #d8d4cc;
    border-radius: 4px;
    padding: 7px 12px;
    font-size: 13px;
    background: #fff;
}
QPushButton#btnSend {
    background: #f5a623;
    color: #fff;
    border: none;
    border-radius: 3px;
    padding: 7px 24px;
    font-size: 13px;
    font-weight: bold;
}
QPushButton#btnSend:hover {
    background: #e8961a;
}
QLineEdit {
    border: 1px solid #d8d4cc;
    border-radius: 3px;
    padding: 5px 10px;
    font-size: 13px;
}
"""
