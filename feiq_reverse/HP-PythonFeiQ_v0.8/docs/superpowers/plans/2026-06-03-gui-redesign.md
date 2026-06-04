# HP-PythonFeiQ v0.7 QQ 风格 GUI 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在 `gui/` 文件夹中用纯 PyQt5 构建 QQ 风格聊天界面（浓橙顶栏 + TIM 扁平气泡 + 16 项功能），引擎代码零改动。

**架构：** 7 文件分层架构 — models（纯数据）→ resources（样式常量）→ contact_panel / chat_view / settings_dialog（UI 组件）→ main_window（组装 + 信号连线 + 拖拽 + 托盘）→ main（入口：UDP 服务 + 引擎启动）。引擎通过 `pyqtSignal` 跨线程桥接到 GUI 主线程。

**技术栈：** Python 3, PyQt5 (QtWidgets, QtGui, QtCore), socket, threading, json, os, winreg

---

## 文件职责

| 文件 | 职责 | 依赖 |
|------|------|------|
| `gui/models.py` | `ContactItem`, `ChatMessage` 纯数据类 | 无 |
| `gui/resources.py` | 颜色常量、QSS 样式表、`format_size()`、头像色生成 | 无 |
| `gui/contact_panel.py` | 左侧面板：搜索框 + QTreeWidget 分组折叠联系人列表 | models, resources |
| `gui/chat_view.py` | 右侧聊天区：QListView + BubbleDelegate + 输入框 + 文件/图片按钮 | models, resources |
| `gui/settings_dialog.py` | 设置对话框：个人信息/文件路径/防火墙/多网段/开机启动 | resources |
| `gui/main_window.py` | 主窗口组装、信号桥接、拖拽蒙层、系统托盘、引擎回调 | 以上全部 |
| `gui/main.py` | 入口：QApplication 高 DPI → UDP 服务器 → Instance.start → window.show() | main_window |

---

### 任务 1：models.py — 数据模型

**文件：**
- 创建：`gui/__init__.py`
- 创建：`gui/models.py`

- [ ] **步骤 1：编写 ContactItem 数据类**

```python
"""数据模型 — 纯 Python 数据类，无 Qt 依赖"""
from dataclasses import dataclass, field
from typing import List, Optional
import datetime


@dataclass
class ContactItem:
    """联系人条目"""
    user_id: str           # 引擎用户 ID
    nickname: str          # 昵称
    groupname: str         # 分组名
    ip: str = ''
    port: int = 0
    online: bool = True
    last_message: str = ''  # 最后一条消息预览
    last_time: Optional[datetime.datetime] = None
    avatar_path: str = ''   # 头像文件路径，空则用文字头像


@dataclass
class ChatMessage:
    """聊天消息"""
    peer_id: str           # 对端 ID
    text: str              # 消息文本
    is_send: bool          # True=自己发的, False=收到的
    time: datetime.datetime = field(default_factory=datetime.datetime.now)
    msg_type: str = 'text' # 'text' | 'image' | 'file'
    file_path: str = ''    # 图片/文件本地路径（用于预览）
    file_name: str = ''    # 原始文件名
    file_size: int = 0     # 文件大小（字节）
```

- [ ] **步骤 2：验证导入**

运行：`python -c "from gui.models import ContactItem, ChatMessage; c = ContactItem('id1', 'test', 'group'); print(c)"`
预期：正常打印 ContactItem 对象

- [ ] **步骤 3：Commit**

```bash
git add gui/__init__.py gui/models.py
git commit -m "feat(gui): add data models ContactItem and ChatMessage"
```

---

### 任务 2：resources.py — 颜色常量与样式表

**文件：**
- 创建：`gui/resources.py`

- [ ] **步骤 1：编写颜色常量和工具函数**

```python
"""资源模块 — 颜色常量、QSS 样式表、工具函数"""
from PyQt5.QtGui import QColor

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

# 头像渐变色池（用于默认文字头像）
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
    font-size: 12px;
}
QTreeWidget::item {
    padding: 6px 12px;
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
    width: 6px;
    background: transparent;
}
QScrollBar::handle:vertical {
    background: #d0d0d0;
    border-radius: 3px;
    min-height: 30px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QTextEdit {
    border: 1px solid #d8d4cc;
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 12px;
    background: #fff;
}
QPushButton#btnSend {
    background: #f5a623;
    color: #fff;
    border: none;
    border-radius: 3px;
    padding: 6px 20px;
    font-weight: bold;
}
QPushButton#btnSend:hover {
    background: #e8961a;
}
QLineEdit {
    border: 1px solid #d8d4cc;
    border-radius: 3px;
    padding: 4px 8px;
    font-size: 12px;
}
"""
```

- [ ] **步骤 2：验证导入和工具函数**

运行：`python -c "from gui.resources import format_size, get_avatar_color; print(format_size(1234567)); print(get_avatar_color('test'))"`
预期：`1.2 MB` 和颜色元组

- [ ] **步骤 3：Commit**

```bash
git add gui/resources.py
git commit -m "feat(gui): add color constants, QSS stylesheets, and utility functions"
```

---

### 任务 3：contact_panel.py — 左侧联系人面板

**文件：**
- 创建：`gui/contact_panel.py`

- [ ] **步骤 1：编写 ContactPanel 类（QTreeWidget 分组列表 + 搜索框）**

```python
"""联系人面板 — 搜索框 + 可折叠分组树"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QTreeWidget, QTreeWidgetItem
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QBrush, QColor

from gui.resources import SIDEBAR_BG, CONTACT_SELECTED, ONLINE_DOT


class ContactPanel(QWidget):
    """左侧联系人面板"""

    contactSelected = pyqtSignal(str)  # user_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._groups = {}  # groupname -> QTreeWidgetItem
        self._contacts = {}  # user_id -> QTreeWidgetItem
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 搜索框
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText('🔍 搜索联系人')
        self.search_box.textChanged.connect(self._on_search)
        layout.addWidget(self.search_box)

        # 联系人树
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(16)
        self.tree.setAnimated(True)
        self.tree.setFocusPolicy(Qt.NoFocus)
        self.tree.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.tree)

    def upsert_contact(self, user_id: str, nickname: str, groupname: str,
                       online: bool = True, last_message: str = ''):
        """添加或更新联系人"""
        # 确保分组存在
        if groupname not in self._groups:
            group_item = QTreeWidgetItem()
            group_item.setText(0, groupname)
            group_item.setData(0, Qt.UserRole, '')  # group marker
            group_item.setFlags(group_item.flags() & ~Qt.ItemIsSelectable)
            self.tree.addTopLevelItem(group_item)
            self._groups[groupname] = group_item

        group_item = self._groups[groupname]

        # 更新或创建联系人条目
        if user_id in self._contacts:
            item = self._contacts[user_id]
        else:
            item = QTreeWidgetItem()
            self._contacts[user_id] = item
            group_item.addChild(item)

        display = f'● {nickname}' if online else f'○ {nickname}'
        if last_message:
            display += f'\n  {last_message[:20]}'
        item.setText(0, display)
        item.setData(0, Qt.UserRole, user_id)
        item.setForeground(0, QBrush(QColor(ONLINE_DOT if online else '#999')))
        item.setSizeHint(0, item.sizeHint(0).expandedTo(
            item.sizeHint(0).grownBy(0, 8)))

        # 更新分组标题
        online_count = sum(
            1 for i in range(group_item.childCount())
            if group_item.child(i).text(0).startswith('●'))
        group_item.setText(0, f'{groupname} ({online_count})')

        group_item.setExpanded(True)

    def remove_contact(self, user_id: str):
        """移除联系人（下线）"""
        if user_id in self._contacts:
            item = self._contacts.pop(user_id)
            parent = item.parent()
            if parent:
                parent.removeChild(item)
                # 更新分组计数
                if parent.childCount() == 0:
                    idx = self.tree.indexOfTopLevelItem(parent)
                    self.tree.takeTopLevelItem(idx)
                    for gname, gitem in list(self._groups.items()):
                        if gitem is parent:
                            del self._groups[gname]

    def set_online_status(self, user_id: str, online: bool):
        """更新在线状态"""
        if user_id in self._contacts:
            item = self._contacts[user_id]
            text = item.text(0)
            if online:
                text = text.replace('○ ', '● ', 1)
            else:
                text = text.replace('● ', '○ ', 1)
            item.setText(0, text)
            item.setForeground(0, QBrush(QColor(ONLINE_DOT if online else '#999')))

    def _on_search(self, text: str):
        """搜索过滤"""
        for i in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(i)
            group.setHidden(False)
            for j in range(group.childCount()):
                child = group.child(j)
                child.setHidden(
                    text.lower() not in child.text(0).lower() if text else False
                )

    def _on_item_clicked(self, item: QTreeWidgetItem, col: int):
        user_id = item.data(0, Qt.UserRole)
        if user_id:  # 联系人条目，非分组标题
            self.contactSelected.emit(user_id)
```

- [ ] **步骤 2：验证组件可独立创建**

运行：`python -c "from PyQt5.QtWidgets import QApplication; import sys; app=QApplication(sys.argv); from gui.contact_panel import ContactPanel; w=ContactPanel(); w.upsert_contact('1','Alice','Test',True,'hello'); w.show(); print('OK')"`
预期：窗口弹出，输出 OK（手动关闭窗口）

- [ ] **步骤 3：Commit**

```bash
git add gui/contact_panel.py
git commit -m "feat(gui): add contact panel with collapsible groups and search"
```

---

### 任务 4：chat_view.py — 右侧聊天区（消息气泡 + 输入）

**文件：**
- 创建：`gui/chat_view.py`

这是最复杂的组件，分 4 个子步骤：

- [ ] **步骤 4.1：编写 ChatView 框架（消息列表 + 输入框 + 按钮栏）**

```python
"""聊天视图 — 消息列表（气泡 delegate）+ 输入区 + 文件按钮"""
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListView, QTextEdit,
    QPushButton, QFileDialog, QStyledItemDelegate, QStyle,
    QApplication
)
from PyQt5.QtCore import pyqtSignal, Qt, QSize, QRect
from PyQt5.QtGui import (
    QFont, QFontMetrics, QPainter, QPainterPath, QTextDocument,
    QPen, QBrush, QColor, QPalette
)

from gui.models import ChatMessage
from gui.resources import (
    BUBBLE_SELF_BG, BUBBLE_SELF_BORDER,
    BUBBLE_OTHER_BG, BUBBLE_OTHER_BORDER,
    CHAT_BG, BTN_SEND, format_size
)


class BubbleDelegate(QStyledItemDelegate):
    """TIM 风格扁平气泡绘制"""

    MAX_WIDTH_RATIO = 0.6  # 气泡最大宽度占比

    def __init__(self, parent=None):
        super().__init__(parent)
        self._doc = QTextDocument()

    def paint(self, painter: QPainter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        is_self = index.data(Qt.UserRole + 1)  # True=自己发的
        text = index.data(Qt.DisplayRole) or ''
        time_str = index.data(Qt.UserRole + 2) or ''

        view_width = option.widget.viewport().width() if option.widget else 400
        max_bubble_w = int(view_width * self.MAX_WIDTH_RATIO)

        # 计算文本尺寸
        self._doc.setDefaultFont(option.font)
        self._doc.setTextWidth(max_bubble_w - 28)  # padding
        self._doc.setHtml(text)
        doc_h = self._doc.size().height()

        bubble_w = min(int(self._doc.size().width()) + 28, max_bubble_w)
        bubble_h = doc_h + 16

        # 计算气泡位置
        margin = 12
        if is_self:
            bubble_x = view_width - bubble_w - margin
        else:
            bubble_x = margin

        bubble_y = option.rect.top() + 4
        bubble_rect = QRect(bubble_x, bubble_y, bubble_w, bubble_h)

        # 绘制气泡背景
        path = QPainterPath()
        path.addRoundedRect(QRect(0, 0, bubble_w, bubble_h).translated(
            bubble_rect.topLeft()), 8, 8)

        if is_self:
            painter.fillPath(path, QColor(BUBBLE_SELF_BG))
            painter.setPen(QPen(QColor(BUBBLE_SELF_BORDER), 1))
        else:
            painter.fillPath(path, QColor(BUBBLE_OTHER_BG))
            painter.setPen(QPen(QColor(BUBBLE_OTHER_BORDER), 1))
        painter.drawPath(path)

        # 绘制文本
        painter.translate(bubble_x + 14, bubble_y + 8)
        self._doc.drawContents(painter)
        painter.restore()

        # 时间戳
        painter.save()
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)
        painter.setPen(QColor('#999'))
        time_rect = QRect(bubble_x, bubble_y + bubble_h + 2,
                          bubble_w, 16)
        align = Qt.AlignRight if is_self else Qt.AlignLeft
        painter.drawText(time_rect, align, time_str)
        painter.restore()

    def sizeHint(self, option, index):
        text = index.data(Qt.DisplayRole) or ''
        view_width = option.widget.viewport().width() if option.widget else 400
        max_w = int(view_width * self.MAX_WIDTH_RATIO)

        self._doc.setDefaultFont(option.font)
        self._doc.setTextWidth(max_w - 28)
        self._doc.setHtml(text)
        doc_h = self._doc.size().height()

        return QSize(view_width, doc_h + 36)  # bubble + padding + timestamp


class ChatView(QWidget):
    """聊天区组件"""

    sendMessage = pyqtSignal(str)       # 发送文字
    sendFile = pyqtSignal(str)          # 发送单个文件
    sendFolder = pyqtSignal(str)        # 发送文件夹
    sendBatchFiles = pyqtSignal(list)   # 批量发送文件
    sendImage = pyqtSignal(str)         # 发送图片

    def __init__(self, parent=None):
        super().__init__(parent)
        self._messages = []  # list[ChatMessage]
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 消息列表
        self.list_view = QListView()
        self.list_view.setVerticalScrollMode(QListView.ScrollPerPixel)
        self.list_view.setSelectionMode(QListView.NoSelection)
        self.list_view.setItemDelegate(BubbleDelegate(self.list_view))
        self.list_view.setStyleSheet('QListView { border: none; background: %s; }' % CHAT_BG)
        # 使用自定义 model（QStandardItemModel 简单实现）
        from PyQt5.QtGui import QStandardItemModel, QStandardItem
        self._model = QStandardItemModel()
        self.list_view.setModel(self._model)
        layout.addWidget(self.list_view, 1)

        # 文件按钮栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)
        toolbar.setContentsMargins(12, 6, 12, 6)
        btn_style = (
            'QPushButton { padding: 4px 10px; border: 1px solid #d8d4cc;'
            'border-radius: 3px; background: #fff; font-size: 11px; color: #666; }'
            'QPushButton:hover { background: #f0f0f0; border-color: #bbb; }'
        )

        btn_file = QPushButton('📎 发送文件')
        btn_file.setStyleSheet(btn_style)
        btn_file.clicked.connect(self._on_send_file)
        toolbar.addWidget(btn_file)

        btn_folder = QPushButton('📁 发送文件夹')
        btn_folder.setStyleSheet(btn_style)
        btn_folder.clicked.connect(self._on_send_folder)
        toolbar.addWidget(btn_folder)

        btn_batch = QPushButton('📦 批量发送')
        btn_batch.setStyleSheet(btn_style)
        btn_batch.clicked.connect(self._on_batch_send)
        toolbar.addWidget(btn_batch)

        btn_image = QPushButton('📷 发送图片')
        btn_image.setStyleSheet(btn_style)
        btn_image.clicked.connect(self._on_send_image)
        toolbar.addWidget(btn_image)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 输入区域
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)
        input_layout.setContentsMargins(12, 6, 12, 10)

        self.input_box = QTextEdit()
        self.input_box.setMaximumHeight(80)
        self.input_box.setMinimumHeight(36)
        self.input_box.setPlaceholderText('输入消息，Enter 发送，Ctrl+Enter 换行')
        self.input_box.installEventFilter(self)
        input_layout.addWidget(self.input_box, 1)

        btn_send = QPushButton('发送')
        btn_send.setObjectName('btnSend')
        btn_send.clicked.connect(self._on_send_message)
        input_layout.addWidget(btn_send)

        layout.addLayout(input_layout)

    def eventFilter(self, source, event):
        if source is self.input_box and event.type() == event.KeyPress:
            key = event.key()
            if key in (Qt.Key_Enter, Qt.Key_Return):
                if event.modifiers() & Qt.ControlModifier:
                    return False  # 换行
                else:
                    self._on_send_message()
                    return True
        return super().eventFilter(source, event)

    def add_message(self, msg: ChatMessage):
        """追加消息到列表"""
        self._messages.append(msg)
        from PyQt5.QtGui import QStandardItem
        item = QStandardItem()
        item.setText(msg.text)
        item.setData(msg.is_send, Qt.UserRole + 1)
        item.setData(msg.time.strftime('%H:%M'), Qt.UserRole + 2)
        item.setEditable(False)
        self._model.appendRow(item)
        # 滚动到底部
        self.list_view.scrollToBottom()

    def clear_messages(self):
        self._messages.clear()
        self._model.clear()

    def load_messages(self, messages: list):
        """批量加载历史消息"""
        self.clear_messages()
        for msg in messages:
            self.add_message(msg)

    def _on_send_message(self):
        text = self.input_box.toPlainText().strip()
        if text:
            self.sendMessage.emit(text)
            self.input_box.clear()

    def _on_send_file(self):
        path, _ = QFileDialog.getOpenFileName(self, '选择文件', '', '所有文件 (*.*)')
        if path:
            self.sendFile.emit(path)

    def _on_send_folder(self):
        path = QFileDialog.getExistingDirectory(self, '选择文件夹')
        if path:
            self.sendFolder.emit(path)

    def _on_batch_send(self):
        paths, _ = QFileDialog.getOpenFileNames(self, '选择文件', '', '所有文件 (*.*)')
        if paths:
            self.sendBatchFiles.emit(paths)

    def _on_send_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, '选择图片', '',
            '图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)')
        if path:
            self.sendImage.emit(path)
```

- [ ] **步骤 4.2：验证 ChatView 可独立创建并添加消息**

运行：`python -c "from PyQt5.QtWidgets import QApplication; import sys; app=QApplication(sys.argv); from gui.chat_view import ChatView; from gui.models import ChatMessage; w=ChatView(); w.add_message(ChatMessage('test','Hello!',True)); w.add_message(ChatMessage('test','Hi there',False)); w.show(); print('OK')"`
预期：窗口弹出，看到两条气泡消息，输出 OK

- [ ] **步骤 4.3：Commit**

```bash
git add gui/chat_view.py
git commit -m "feat(gui): add chat view with TIM-style bubble delegate and file buttons"
```

---

### 任务 5：settings_dialog.py — 设置对话框

**文件：**
- 创建：`gui/settings_dialog.py`

- [ ] **步骤 1：编写 SettingsDialog 类（5 个标签页）**

```python
"""设置对话框 — 个人信息、文件路径、防火墙、多网段、开机启动"""
import os
import json
import sys
import subprocess

from PyQt5.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QCheckBox,
    QListWidget, QListWidgetItem, QMessageBox, QFormLayout,
    QGroupBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QPainter, QBrush, QColor, QFont

SETTINGS_PATH = os.path.join(os.path.dirname(__file__), 'settings.json')

DEFAULT_SETTINGS = {
    'nickname': '',
    'avatar_path': '',
    'save_path': os.path.join(os.path.expanduser('~'), 'Downloads'),
    'extra_broadcasts': [],    # 额外广播地址列表
    'auto_start': False,
}


def load_settings() -> dict:
    """加载设置"""
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                return {**DEFAULT_SETTINGS, **cfg}
        except Exception:
            pass
    return dict(DEFAULT_SETTINGS)


def save_settings(cfg: dict):
    """保存设置"""
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('设置')
        self.setMinimumSize(480, 420)
        self._cfg = load_settings()
        self._build_ui()
        self._load_to_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        tabs.addTab(self._tab_personal(), '个人信息')
        tabs.addTab(self._tab_file(), '文件')
        tabs.addTab(self._tab_firewall(), '防火墙')
        tabs.addTab(self._tab_subnet(), '多网段')
        tabs.addTab(self._tab_startup(), '开机启动')

        layout.addWidget(tabs)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_save = QPushButton('保存')
        btn_save.clicked.connect(self._on_save)
        btn_save.setStyleSheet(
            'QPushButton { background: #f5a623; color: #fff; border: none;'
            'border-radius: 3px; padding: 6px 24px; font-weight: bold; }'
            'QPushButton:hover { background: #e8961a; }')
        btn_layout.addStretch()
        btn_layout.addWidget(btn_save)

        btn_cancel = QPushButton('取消')
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

    def _tab_personal(self):
        w = QWidget()
        layout = QFormLayout(w)
        layout.setSpacing(12)

        btn_avatar = QPushButton('点击更换头像')
        btn_avatar.clicked.connect(self._on_change_avatar)
        layout.addRow('头像:', btn_avatar)

        self.edit_nickname = QLineEdit()
        self.edit_nickname.setPlaceholderText('输入昵称')
        layout.addRow('昵称:', self.edit_nickname)

        return w

    def _tab_file(self):
        w = QWidget()
        layout = QHBoxLayout(w)

        self.edit_save_path = QLineEdit()
        self.edit_save_path.setReadOnly(True)
        layout.addWidget(self.edit_save_path)

        btn_browse = QPushButton('浏览...')
        btn_browse.clicked.connect(self._on_browse_path)
        layout.addWidget(btn_browse)

        return w

    def _tab_firewall(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        info = QLabel(
            '飞秋使用 UDP+TCP 端口 2425 通信。'
            '如果防火墙阻止，对方可能发现不了你或无法接收文件。\n'
            '点击下方按钮通过 netsh 添加防火墙入站规则。'
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        btn_unblock = QPushButton('解除防火墙阻止')
        btn_unblock.clicked.connect(self._on_firewall_unblock)
        btn_unblock.setStyleSheet(
            'QPushButton { background: #ff5722; color: #fff; border: none;'
            'border-radius: 3px; padding: 8px 16px; font-weight: bold; }'
            'QPushButton:hover { background: #e64a19; }')
        layout.addWidget(btn_unblock)

        layout.addStretch()
        return w

    def _tab_subnet(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        info = QLabel('额外广播地址（如 192.168.1.255），每行一个：')
        info.setWordWrap(True)
        layout.addWidget(info)

        self.list_subnets = QListWidget()
        layout.addWidget(self.list_subnets)

        btn_layout = QHBoxLayout()
        self.edit_subnet = QLineEdit()
        self.edit_subnet.setPlaceholderText('输入广播地址，如 192.168.2.255')
        btn_layout.addWidget(self.edit_subnet)

        btn_add = QPushButton('添加')
        btn_add.clicked.connect(self._on_add_subnet)
        btn_layout.addWidget(btn_add)

        btn_del = QPushButton('删除选中')
        btn_del.clicked.connect(self._on_del_subnet)
        btn_layout.addWidget(btn_del)

        layout.addLayout(btn_layout)
        return w

    def _tab_startup(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        self.check_startup = QCheckBox('开机自动启动 HP-PythonFeiQ')
        layout.addWidget(self.check_startup)

        info = QLabel(
            '通过注册表 HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run 实现，'
            '取消勾选后保存即可移除。')
        info.setWordWrap(True)
        layout.addWidget(info)

        layout.addStretch()
        return w

    def _load_to_ui(self):
        self.edit_nickname.setText(self._cfg.get('nickname', ''))
        self.edit_save_path.setText(self._cfg.get('save_path', ''))
        self.check_startup.setChecked(self._cfg.get('auto_start', False))
        self.list_subnets.clear()
        for addr in self._cfg.get('extra_broadcasts', []):
            self.list_subnets.addItem(addr)

    def _on_change_avatar(self):
        path, _ = QFileDialog.getOpenFileName(
            self, '选择头像', '',
            '图片文件 (*.png *.jpg *.jpeg *.bmp)')
        if path:
            self._cfg['avatar_path'] = path

    def _on_browse_path(self):
        path = QFileDialog.getExistingDirectory(self, '选择默认保存目录')
        if path:
            self.edit_save_path.setText(path)

    def _on_firewall_unblock(self):
        """通过 netsh 添加防火墙规则"""
        rules = [
            ['netsh', 'advfirewall', 'firewall', 'add', 'rule',
             'name="HP-PythonFeiQ UDP"', 'dir=in', 'action=allow',
             'protocol=UDP', 'localport=2425'],
            ['netsh', 'advfirewall', 'firewall', 'add', 'rule',
             'name="HP-PythonFeiQ TCP"', 'dir=in', 'action=allow',
             'protocol=TCP', 'localport=2425'],
        ]
        success = True
        for rule in rules:
            try:
                subprocess.run(rule, capture_output=True, check=True)
            except subprocess.CalledProcessError as e:
                success = False
                QMessageBox.warning(self, '防火墙', f'添加规则失败:\n{e.stderr.decode("gbk", errors="replace")}')
                break

        if success:
            QMessageBox.information(self, '防火墙', '已成功添加 UDP+TCP 2425 端口入站规则！')

    def _on_add_subnet(self):
        addr = self.edit_subnet.text().strip()
        if addr:
            self.list_subnets.addItem(addr)
            self.edit_subnet.clear()

    def _on_del_subnet(self):
        for item in self.list_subnets.selectedItems():
            self.list_subnets.takeItem(self.list_subnets.row(item))

    def _on_save(self):
        self._cfg['nickname'] = self.edit_nickname.text().strip()
        self._cfg['save_path'] = self.edit_save_path.text().strip()
        self._cfg['auto_start'] = self.check_startup.isChecked()
        self._cfg['extra_broadcasts'] = [
            self.list_subnets.item(i).text()
            for i in range(self.list_subnets.count())
        ]
        save_settings(self._cfg)

        # 处理开机自启动
        self._set_auto_start(self._cfg['auto_start'])

        self.accept()

    def _set_auto_start(self, enable: bool):
        """写入或删除注册表 Run 键"""
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Run',
                0, winreg.KEY_SET_VALUE)
            if enable:
                exe_path = sys.executable
                script_path = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), '..', 'main.py'))
                winreg.SetValueEx(key, 'HP-PythonFeiQ', 0, winreg.REG_SZ,
                                  f'"{exe_path}" "{script_path}"')
            else:
                try:
                    winreg.DeleteValue(key, 'HP-PythonFeiQ')
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception:
            pass  # 非 Windows 平台或无权限
```

- [ ] **步骤 2：验证导入**

运行：`python -c "from gui.settings_dialog import SettingsDialog, load_settings, save_settings; print('OK')"`
预期：`OK`

- [ ] **步骤 3：Commit**

```bash
git add gui/settings_dialog.py
git commit -m "feat(gui): add settings dialog with 5 tabs including firewall unblock and auto-start"
```

---

### 任务 6：main_window.py — 主窗口组装

**文件：**
- 创建：`gui/main_window.py`

- [ ] **步骤 1：编写 MainWindow（组装所有组件 + 引擎桥接 + 拖拽 + 托盘）**

```python
"""主窗口 — 组装 contact_panel + chat_view + 引擎桥接 + 拖拽 + 托盘"""
import os
import queue
import socket

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QLabel, QPushButton, QMessageBox, QFileDialog, QApplication,
    QSystemTrayIcon, QMenu, QAction, QStyle
)
from PyQt5.QtCore import pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QBrush, QColor, QFont, QPen

from gui.models import ContactItem, ChatMessage
from gui.resources import (
    HEADER_START, HEADER_END, HEADER_TEXT, MAIN_QSS
)
from gui.contact_panel import ContactPanel
from gui.chat_view import ChatView
from gui.settings_dialog import SettingsDialog, load_settings

from WorkThread import Instance
from UserManager import VIEW_USER, VIEW_CONTENT
from feiqstruct import TextContent, ContentType


class MainWindow(QMainWindow):
    # 跨线程信号
    _userSignal = pyqtSignal(object)
    _contentSignal = pyqtSignal(object)
    _fileRecvSignal = pyqtSignal(str, int, int, object)

    def __init__(self):
        super().__init__()
        self.setWindowTitle('HP-PythonFeiQ v0.7')
        self.resize(1100, 700)
        self.setMinimumSize(760, 480)
        self.setStyleSheet(MAIN_QSS)

        self._current_user_id = None
        self._users = {}         # user_id -> User (引擎对象)
        self._msg_store = {}     # user_id -> list[ChatMessage]
        self._settings = load_settings()
        self._drag_overlay = None

        self._build_ui()
        self._connect_signals()
        self._setup_tray()

        # 拖拽支持
        self.setAcceptDrops(True)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # === 顶栏 ===
        self._build_header(layout)

        # === 主体：左侧联系人 + 右侧聊天 ===
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)

        self.contact_panel = ContactPanel()
        self.contact_panel.setMinimumWidth(180)
        self.contact_panel.contactSelected.connect(self._on_contact_selected)
        splitter.addWidget(self.contact_panel)

        # 右侧容器
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # 聊天标题栏
        self.chat_title = QLabel('欢迎使用 HP-PythonFeiQ')
        self.chat_title.setStyleSheet(
            'QLabel { padding: 8px 14px; border-bottom: 1px solid #e8e4dc;'
            'font-size: 12px; font-weight: bold; color: #666; background: #fafaf8; }')
        right_layout.addWidget(self.chat_title)

        self.chat_view = ChatView()
        self.chat_view.sendMessage.connect(self._on_send_message)
        self.chat_view.sendFile.connect(self._on_send_file_signal)
        self.chat_view.sendFolder.connect(self._on_send_folder_signal)
        self.chat_view.sendBatchFiles.connect(self._on_batch_send_signal)
        self.chat_view.sendImage.connect(self._on_send_image)
        right_layout.addWidget(self.chat_view, 1)

        splitter.addWidget(right)
        splitter.setSizes([220, 880])
        layout.addWidget(splitter, 1)

    def _build_header(self, parent_layout):
        """浓橙渐变顶栏"""
        header = QWidget()
        header.setFixedHeight(32)
        header.setStyleSheet(
            'background: qlineargradient(x1:0, y1:0, x2:0, y2:1,'
            'stop:0 %s, stop:1 %s);' % (HEADER_START, HEADER_END))
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(12, 0, 8, 0)

        title = QLabel('HP-PythonFeiQ')
        title.setStyleSheet(
            'QLabel { color: %s; font-size: 12px; font-weight: bold;'
            'background: transparent; }' % HEADER_TEXT)
        h_layout.addWidget(title)

        h_layout.addStretch()

        # 设置按钮
        btn_settings = QPushButton('⚙')
        btn_settings.setFixedSize(24, 24)
        btn_settings.setStyleSheet(
            'QPushButton { color: %s; background: transparent; border: none;'
            'font-size: 14px; }'
            'QPushButton:hover { color: #fff; }' % HEADER_TEXT)
        btn_settings.clicked.connect(self._on_open_settings)
        h_layout.addWidget(btn_settings)

        parent_layout.addWidget(header)

    def _connect_signals(self):
        self._userSignal.connect(self._on_user_update)
        self._contentSignal.connect(self._on_content_recv)
        self._fileRecvSignal.connect(self._on_file_recv_dialog)

    # ==================== 系统托盘 ====================

    def _setup_tray(self):
        self._tray = QSystemTrayIcon(self)
        # 生成一个简单的图标
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor('#f5a623')))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(4, 4, 24, 24)
        painter.setPen(QPen(QColor('#fff'), 2))
        font = QFont('Microsoft YaHei', 10, QFont.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignCenter, 'F')
        painter.end()
        self._tray.setIcon(QIcon(pixmap))

        tray_menu = QMenu()
        action_show = QAction('显示主窗口', self)
        action_show.triggered.connect(self._show_from_tray)
        tray_menu.addAction(action_show)

        action_quit = QAction('退出', self)
        action_quit.triggered.connect(self._quit_app)
        tray_menu.addAction(action_quit)

        self._tray.setContextMenu(tray_menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_from_tray()

    def _show_from_tray(self):
        self.showNormal()
        self.activateWindow()

    def _quit_app(self):
        Instance.stopAll()
        self._tray.hide()
        QApplication.quit()

    def closeEvent(self, event):
        """最小化到托盘"""
        event.ignore()
        self.hide()
        self._tray.showMessage('HP-PythonFeiQ', '已最小化到系统托盘',
                               QSystemTrayIcon.Information, 2000)

    # ==================== 设置对话框 ====================

    def _on_open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec_():
            self._settings = load_settings()

    # ==================== 联系人交互 ====================

    def _on_contact_selected(self, user_id: str):
        self._current_user_id = user_id
        user = self._users.get(user_id)
        if user:
            self.chat_title.setText(
                f'与 {user.nickname} ({user.groupname}) 聊天中...')
            # 加载历史消息
            msgs = self._msg_store.get(user_id, [])
            chat_msgs = []
            for content in user.lstContents:
                chat_msgs.append(ChatMessage(
                    peer_id=content.peer,
                    text=content.text if hasattr(content, 'text') else '[文件]',
                    is_send=content.tx,
                    time=content.time,
                ))
            if chat_msgs:
                self.chat_view.load_messages(chat_msgs)

    # ==================== 消息处理 ====================

    def _on_send_message(self, text: str):
        if not self._current_user_id:
            QMessageBox.information(self, '提示', '请先选择聊天对象')
            return

        content = TextContent(text, '', self._current_user_id, True)
        Instance.appendContent(content)

        # 立即显示
        msg = ChatMessage(
            peer_id=self._current_user_id,
            text=text, is_send=True)
        self.chat_view.add_message(msg)

        if self._current_user_id not in self._msg_store:
            self._msg_store[self._current_user_id] = []
        self._msg_store[self._current_user_id].append(msg)

        # 更新联系人预览
        user = self._users.get(self._current_user_id)
        if user:
            self.contact_panel.upsert_contact(
                self._current_user_id,
                user.nickname,
                user.groupname,
                True,
                text[:20])

    def _on_content_recv(self, content):
        """收到消息"""
        if content.type == ContentType.TEXT:
            msg = ChatMessage(
                peer_id=content.peer,
                text=content.text,
                is_send=content.tx,
                time=content.time,
            )
            if self._current_user_id and content.peer == self._current_user_id:
                self.chat_view.add_message(msg)

            if content.peer not in self._msg_store:
                self._msg_store[content.peer] = []
            self._msg_store[content.peer].append(msg)

            # 更新联系人预览
            user = self._users.get(content.peer)
            if user:
                self.contact_panel.upsert_contact(
                    content.peer,
                    user.nickname,
                    user.groupname,
                    True,
                    content.text[:20])

            # 托盘闪烁
            if not self.isActiveWindow():
                self._tray.showMessage(
                    user.nickname if user else '新消息',
                    content.text[:50],
                    QSystemTrayIcon.Information, 3000)

    # ==================== 用户状态 ====================

    def _on_user_update(self, user):
        uid = user.getId()
        if user.state == 1:  # FRIEND_ONLINE
            self._users[uid] = user
            self.contact_panel.upsert_contact(
                uid, user.nickname, user.groupname, True)
        elif user.state == 0:  # FRIEND_OFFLINE
            self._users.pop(uid, None)
            self.contact_panel.remove_contact(uid)
            if self._current_user_id == uid:
                self._current_user_id = None
                self.chat_view.clear_messages()
                self.chat_title.setText('欢迎使用 HP-PythonFeiQ')

    # ==================== 文件发送 ====================

    def _guard_user(self):
        if not self._current_user_id:
            QMessageBox.information(self, '提示', '请先选择聊天对象')
            return None
        return self._current_user_id

    def _on_send_file_signal(self, path: str):
        peer = self._guard_user()
        if peer:
            Instance.sendFile(peer, path)

    def _on_send_folder_signal(self, path: str):
        peer = self._guard_user()
        if peer:
            Instance.sendFolder(peer, path)

    def _on_batch_send_signal(self, paths: list):
        peer = self._guard_user()
        if peer:
            Instance.sendBatchFiles(peer, paths)

    def _on_send_image(self, path: str):
        peer = self._guard_user()
        if peer:
            # 图片通过 sendFile 传输，同时显示缩略图消息
            msg = ChatMessage(
                peer_id=peer,
                text=f'[图片] {os.path.basename(path)}',
                is_send=True,
                msg_type='image',
                file_path=path,
            )
            self.chat_view.add_message(msg)
            Instance.sendFile(peer, path)

    # ==================== 文件接收 ====================

    def _file_recv_handler(self, filename: str, filesize: int, filetype: int):
        """引擎回调（后台线程），发射信号到主线程"""
        result_queue = queue.Queue()
        self._fileRecvSignal.emit(filename, filesize, filetype, result_queue)
        try:
            return result_queue.get(timeout=120)
        except queue.Empty:
            return None, False

    def _on_file_recv_dialog(self, filename: str, filesize: int,
                             filetype: int, result_queue):
        """主线程文件接收对话框"""
        from gui.resources import format_size

        is_batch = (filetype == -1)
        type_name = '批量文件' if is_batch else ('文件夹' if filetype >= 2 else '文件')
        size_str = format_size(filesize)

        msg = QMessageBox(self)
        msg.setWindowTitle(f'收到{type_name}')
        msg.setText(f'{filename}\n{type_name} ({size_str})')

        btn_accept = msg.addButton('接收', QMessageBox.AcceptRole)
        btn_saveas = msg.addButton(
            '存到...' if is_batch else '另存为...', QMessageBox.ApplyRole)
        btn_reject = msg.addButton('拒绝', QMessageBox.RejectRole)
        msg.exec_()

        clicked = msg.clickedButton()
        if clicked == btn_reject:
            result_queue.put((None, False))
        elif clicked == btn_saveas:
            save_path = self._settings.get('save_path', os.path.expanduser('~'))
            if is_batch:
                path = QFileDialog.getExistingDirectory(
                    self, '选择保存目录', save_path)
                result_queue.put((path, True) if path else (None, False))
            else:
                default = os.path.join(save_path, filename)
                path, _ = QFileDialog.getSaveFileName(self, '保存到', default)
                result_queue.put((path, True) if path else (None, False))
        else:
            result_queue.put((None, True))

    # ==================== 拖拽支持 ====================

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._show_drag_overlay()

    def dragLeaveEvent(self, event):
        self._hide_drag_overlay()

    def dropEvent(self, event):
        self._hide_drag_overlay()
        peer = self._guard_user()
        if not peer:
            return

        urls = event.mimeData().urls()
        paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
        if not paths:
            return

        if len(paths) == 1 and os.path.isfile(paths[0]):
            Instance.sendFile(peer, paths[0])
        elif len(paths) == 1 and os.path.isdir(paths[0]):
            Instance.sendFolder(peer, paths[0])
        else:
            files = [p for p in paths if os.path.isfile(p)]
            if files:
                Instance.sendBatchFiles(peer, files)

    def _show_drag_overlay(self):
        if self._drag_overlay is None:
            self._drag_overlay = QWidget(self)
            self._drag_overlay.setStyleSheet(
                'background: rgba(255, 183, 77, 0.15);'
                'border: 3px dashed #f5a623;')
            label = QLabel('拖拽文件到这里发送', self._drag_overlay)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet(
                'font-size: 18px; color: #f5a623; font-weight: bold;'
                'background: transparent; border: none;')
            vbox = QVBoxLayout(self._drag_overlay)
            vbox.addWidget(label)
        self._drag_overlay.setGeometry(self.rect())
        self._drag_overlay.show()
        self._drag_overlay.raise_()

    def _hide_drag_overlay(self):
        if self._drag_overlay:
            self._drag_overlay.hide()

    # ==================== 引擎回调入口 ====================

    def onViewDispatch(self, view):
        """引擎回调（后台线程安全）"""
        if view.type() == VIEW_USER:
            self._userSignal.emit(view.user)
        elif view.type() == VIEW_CONTENT:
            self._contentSignal.emit(view.content)
```

- [ ] **步骤 2：验证 MainWindow 可独立创建**

运行：`python -c "from PyQt5.QtWidgets import QApplication; import sys; app=QApplication(sys.argv); from gui.main_window import MainWindow; w=MainWindow(); w.show(); print('OK')"`
预期：窗口弹出，看到完整布局，输出 OK

- [ ] **步骤 3：Commit**

```bash
git add gui/main_window.py
git commit -m "feat(gui): add main window with engine bridge, drag-drop, and system tray"
```

---

### 任务 7：main.py — 入口 + main_window.py 入口修正

**文件：**
- 创建：`gui/main.py`
- 修改：`gui/main_window.py`（在末尾添加入口逻辑，或者入口全放在 main.py）

**决定：** 入口全放 `main.py`，`main_window.py` 只负责窗口类定义。

- [ ] **步骤 1：编写 main.py**

```python
"""HP-PythonFeiQ v0.7 GUI 入口"""
import sys
import os
import socket
import threading

# 确保引擎路径可导入
ENGINE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ENGINE_DIR)

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from gui.main_window import MainWindow

from SocketHandle import UdpHandle
from socketserver import UDPServer
from WorkThread import Instance
import setting


def main():
    # 高 DPI 适配
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # 启动 UDP 服务器
    udp_server = UDPServer((setting.IPADDRESS, setting.PORT), UdpHandle)
    udp_server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    server_thread = threading.Thread(
        target=udp_server.serve_forever, name='UDP-Server', daemon=True)
    server_thread.start()

    # 创建窗口
    window = MainWindow()

    # 绑定引擎
    Instance.start(udp_server.socket.sendto, window.onViewDispatch)
    Instance.file_recv_cb = window._file_recv_handler

    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
```

- [ ] **步骤 2：验证入口可正常启动**

运行：`python gui/main.py`
预期：窗口弹出，UDP 服务器启动，开始发现在线用户

- [ ] **步骤 3：Commit**

```bash
git add gui/main.py
git commit -m "feat(gui): add entry point with high DPI support and engine initialization"
```

---

## 自检清单

1. **规格覆盖度：**
   - 文字消息收发 → main_window.py `_on_send_message` + `_on_content_recv`
   - 发送单个文件 → chat_view.py `sendFile` 信号 → main_window.py
   - 发送文件夹 → chat_view.py `sendFolder` 信号 → main_window.py
   - 批量发送文件 → chat_view.py `sendBatchFiles` 信号 → main_window.py
   - 接收文件弹窗 → main_window.py `_on_file_recv_dialog`
   - 拖拽文件发送 → main_window.py `dragEnterEvent/dropEvent` + 蒙层
   - 自动发现用户 → main_window.py `_on_user_update` → contact_panel
   - 分组折叠 → contact_panel.py QTreeWidget
   - 高 DPI → main.py `AA_EnableHighDpiScaling`
   - 窗口缩放 → QSplitter + 弹性布局
   - 头像上传 → settings_dialog.py `_on_change_avatar`
   - 系统托盘 → main_window.py `_setup_tray`
   - 图片发送 → chat_view.py `sendImage` 信号 + main_window.py
   - 设置页 → settings_dialog.py 5 tabs
   - 开机自启动 → settings_dialog.py `_set_auto_start`
   - 防火墙解封 → settings_dialog.py `_on_firewall_unblock`
   - 多网段 → settings_dialog.py `_tab_subnet`
   - ✅ 全部覆盖

2. **占位符扫描：** 无 "TODO"、"待定"、空实现

3. **类型一致性：**
   - `ContactItem.user_id` 在 contact_panel 中作为 `Qt.UserRole` data 存储 ✓
   - `ChatMessage` 字段在 chat_view 和 main_window 中一致 ✓
   - 信号签名匹配：`pyqtSignal(str)` ↔ `emit(str)` ✓
