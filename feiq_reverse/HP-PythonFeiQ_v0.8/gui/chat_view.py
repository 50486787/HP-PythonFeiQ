"""聊天视图 — 消息列表 + 输入框 + 文件按钮（渲染委托在 bubble_delegate.py）"""
import os

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListView, QTextEdit,
    QPushButton, QFileDialog,
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QStandardItemModel, QStandardItem

from gui.models import ChatMessage
from gui.bubble_delegate import BubbleDelegate
from gui.bubble_delegate import (
    ROLE_IS_SELF, ROLE_TIME, ROLE_PROGRESS, ROLE_MSG_TYPE,
    ROLE_TRANSFER_DONE, ROLE_TRANSFER_CANCELLED, ROLE_FILE_NAME,
    ROLE_FILE_SIZE, ROLE_CANCEL_RECT, ROLE_BYTES_DONE, ROLE_BYTES_TOTAL,
    ROLE_FAIL_REASON,
)
from gui.resources import CHAT_BG


class ChatView(QWidget):
    """聊天区组件"""

    # 发消息信号
    sendMessage = pyqtSignal(str)
    sendFile = pyqtSignal(str)
    sendFolder = pyqtSignal(str)
    sendBatchFiles = pyqtSignal(list)
    cancelTransfer = pyqtSignal(str)   # filename

    def __init__(self, parent=None):
        super().__init__(parent)
        self._messages = []
        self._build_ui()

    # ─── UI ───────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 消息列表
        self.list_view = QListView()
        self.list_view.setVerticalScrollMode(QListView.ScrollPerPixel)
        self.list_view.setSelectionMode(QListView.NoSelection)
        self.list_view.setItemDelegate(BubbleDelegate(self.list_view))
        self.list_view.setStyleSheet(
            'QListView { border: none; background: %s; }' % CHAT_BG)
        self._model = QStandardItemModel()
        self.list_view.setModel(self._model)
        self._viewport = self.list_view.viewport()
        self._viewport.installEventFilter(self)
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

        for text, slot in [('📎 发送文件', self._on_send_file),
                           ('📁 发送文件夹', self._on_send_folder),
                           ('📦 批量发送', self._on_batch_send)]:
            btn = QPushButton(text)
            btn.setStyleSheet(btn_style)
            btn.clicked.connect(slot)
            toolbar.addWidget(btn)
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

        self.btn_send = QPushButton('发送')
        self.btn_send.setObjectName('btnSend')
        self.btn_send.clicked.connect(self._on_send_message)
        input_layout.addWidget(self.btn_send)

        layout.addLayout(input_layout)

    # ─── event filter ─────────────────────────────────────────

    def eventFilter(self, source, event):
        # Enter 发送
        if (hasattr(self, 'input_box') and source is self.input_box
                and event.type() == event.KeyPress):
            key = event.key()
            if key in (Qt.Key_Enter, Qt.Key_Return):
                if event.modifiers() & Qt.ControlModifier:
                    return False
                self._on_send_message()
                return True

        # 取消按钮点击
        if (hasattr(self, '_viewport') and source is self._viewport
                and event.type() == event.MouseButtonPress):
            pos = event.pos()
            idx = self.list_view.indexAt(pos)
            if idx.isValid():
                rect = idx.data(ROLE_CANCEL_RECT)
                if rect:
                    x, y, w, h = rect
                    if x <= pos.x() <= x + w and y <= pos.y() <= y + h:
                        fname = idx.data(ROLE_FILE_NAME) or ''
                        if fname:
                            self.cancelTransfer.emit(fname)
                            return True

        return super().eventFilter(source, event)

    # ─── 消息管理 ─────────────────────────────────────────────

    def add_message(self, msg: ChatMessage):
        """追加消息到列表"""
        self._messages.append(msg)
        item = QStandardItem()
        text = msg.text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        text = text.replace('\n', '<br>')
        item.setText(text)
        item.setData(msg.is_send, ROLE_IS_SELF)
        item.setData(msg.time.strftime('%H:%M'), ROLE_TIME)
        item.setData(msg.msg_type, ROLE_MSG_TYPE)
        item.setData(msg.transfer_done, ROLE_TRANSFER_DONE)
        item.setData(msg.transfer_cancelled, ROLE_TRANSFER_CANCELLED)
        item.setData(msg.file_name, ROLE_FILE_NAME)
        item.setData(msg.file_size, ROLE_FILE_SIZE)
        item.setData(0.0 if msg.msg_type == 'file' else -1.0, ROLE_PROGRESS)
        item.setEditable(False)
        self._model.appendRow(item)
        self.list_view.scrollToBottom()

    def update_file_progress(self, filename: str, bytes_done: int, total: int):
        """更新进度条 — 传输中仅设数据；完成时重建视图确保刷新"""
        for row in range(self._model.rowCount()):
            item = self._model.item(row)
            if item and item.data(ROLE_FILE_NAME) == filename:
                pct = bytes_done / total if total > 0 else 0.0
                item.setData(pct, ROLE_PROGRESS)
                item.setData(bytes_done, ROLE_BYTES_DONE)
                item.setData(total, ROLE_BYTES_TOTAL)
                if bytes_done >= total > 0:
                    item.setData(1.0, ROLE_PROGRESS)
                    item.setData(True, ROLE_TRANSFER_DONE)
                    # 完成时：写回消息对象，重建视图确保显示
                    for msg in self._messages:
                        if msg.file_name == filename:
                            msg.transfer_done = True
                            msg.transfer_bytes = bytes_done
                    msgs = list(self._messages)
                    self.load_messages(msgs)
                else:
                    self.list_view.viewport().update()
                return

    def mark_transfer_cancelled(self, filename: str):
        """标记已取消"""
        self._set_item_flag(filename, ROLE_TRANSFER_CANCELLED)

    def mark_transfer_failed(self, filename: str, reason: str = '传输失败'):
        """标记失败"""
        for row in range(self._model.rowCount()):
            item = self._model.item(row)
            if item and item.data(ROLE_FILE_NAME) == filename:
                item.setData(True, ROLE_TRANSFER_DONE)
                item.setData(reason, ROLE_FAIL_REASON)
                self.list_view.viewport().update()
                return

    def _set_item_flag(self, filename: str, role: int):
        for row in range(self._model.rowCount()):
            item = self._model.item(row)
            if item and item.data(ROLE_FILE_NAME) == filename:
                item.setData(True, role)
                self.list_view.viewport().update()
                return

    def clear_messages(self):
        self._messages.clear()
        self._model.clear()

    def load_messages(self, messages: list):
        """批量加载历史消息"""
        self.clear_messages()
        for msg in messages:
            if hasattr(msg, 'type') and hasattr(msg, 'text'):
                cm = ChatMessage(
                    peer_id=str(msg.peer),
                    text=getattr(msg, 'text', ''),
                    is_send=msg.tx,
                    time=msg.time,
                )
            else:
                cm = msg
            self.add_message(cm)

    # ─── 发送动作 ─────────────────────────────────────────────

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
