"""聊天视图 — 消息列表（气泡 delegate）+ 输入区 + 文件按钮"""
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListView, QTextEdit,
    QPushButton, QFileDialog, QStyledItemDelegate
)
from PyQt5.QtCore import pyqtSignal, Qt, QSize, QRect, QRectF
from PyQt5.QtGui import (
    QFont, QPainter, QPainterPath, QTextDocument, QPen, QBrush,
    QColor, QStandardItemModel, QStandardItem, QPalette
)

from gui.models import ChatMessage
from gui.resources import (
    BUBBLE_SELF_BG, BUBBLE_SELF_BORDER,
    BUBBLE_OTHER_BG, BUBBLE_OTHER_BORDER,
    CHAT_BG, format_size
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
        self._doc.setTextWidth(max_bubble_w - 28)  # 减去 padding
        self._doc.setHtml(text)
        doc_h = self._doc.size().height()
        doc_w = self._doc.size().width()

        bubble_w = min(int(doc_w) + 28, max_bubble_w)
        bubble_h = max(int(doc_h) + 16, 24)

        # 计算气泡位置
        margin = 12
        if is_self:
            bubble_x = view_width - bubble_w - margin
        else:
            bubble_x = margin

        bubble_y = option.rect.top() + 4
        bubble_rect = QRect(bubble_x, bubble_y, bubble_w, int(bubble_h))

        # 绘制气泡背景
        path = QPainterPath()
        path.addRoundedRect(
            QRectF(0, 0, float(bubble_w), float(bubble_h)).translated(bubble_rect.topLeft()),
            8.0, 8.0)

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
        time_rect = QRect(bubble_x, bubble_y + int(bubble_h) + 2,
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

        return QSize(view_width, max(int(doc_h) + 36, 40))  # bubble + padding + timestamp


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
        self.list_view.setStyleSheet(
            'QListView { border: none; background: %s; }' % CHAT_BG)
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

    def eventFilter(self, source, event):
        if source is self.input_box and event.type() == event.KeyPress:
            key = event.key()
            if key in (Qt.Key_Enter, Qt.Key_Return):
                if event.modifiers() & Qt.ControlModifier:
                    return False  # 让换行正常处理
                else:
                    self._on_send_message()
                    return True
        return super().eventFilter(source, event)

    def add_message(self, msg: ChatMessage):
        """追加消息到列表"""
        self._messages.append(msg)
        item = QStandardItem()
        # HTML 转义文本中的特殊字符
        text = msg.text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        # 支持换行
        text = text.replace('\n', '<br>')
        item.setText(text)
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
            if hasattr(msg, 'type') and hasattr(msg, 'text'):
                # 引擎的 PacketContent 对象
                cm = ChatMessage(
                    peer_id=str(msg.peer),
                    text=getattr(msg, 'text', ''),
                    is_send=msg.tx,
                    time=msg.time,
                )
            else:
                cm = msg
            self.add_message(cm)

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
