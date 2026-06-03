import sys
import os
import queue
import socket
import threading
from socketserver import UDPServer

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QComboBox, QTextEdit, QPushButton, QLabel, QFileDialog,
    QMessageBox, QStatusBar, QSplitter
)

from SocketHandle import UdpHandle
from WorkThread import Instance
from UserManager import VIEW_USER, VIEW_CONTENT
from feiqstruct import TextContent, ContentType
import setting


class MainWindow(QMainWindow):
    _userSignal = pyqtSignal(object)       # User object
    _contentSignal = pyqtSignal(object)    # PacketContent object
    _fileRecvSignal = pyqtSignal(str, int, int, object)  # name, size, type, result_queue

    def __init__(self):
        super().__init__()
        self.setWindowTitle('HP-PythonFeiQ v0.6')
        self.resize(640, 520)

        self._current_user_id = None
        self._users = {}  # user_id -> User

        self._buildUi()
        self._connectSignals()

    # ==================== UI 构建 ====================

    def _buildUi(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # --- 顶部：联系人选择 ---
        top = QHBoxLayout()
        top.addWidget(QLabel('聊天对象:'))
        self.comboUser = QComboBox()
        self.comboUser.setMinimumWidth(200)
        self.comboUser.currentIndexChanged.connect(self._onUserSelected)
        top.addWidget(self.comboUser, 1)
        layout.addLayout(top)

        # --- 中间：聊天记录 ---
        self.chatHistory = QTextEdit()
        self.chatHistory.setReadOnly(True)
        layout.addWidget(self.chatHistory, 3)

        # --- 文件发送按钮 ---
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        btn_style = (
            'QPushButton { padding: 4px 12px; border: 1px solid #ccc;'
            'border-radius: 3px; background: #f8f8f8; font-size: 12px; }'
            'QPushButton:hover { background: #e0e0e0; border-color: #aaa; }'
        )

        self.btnFile = QPushButton('📎 发送文件')
        self.btnFile.setStyleSheet(btn_style)
        self.btnFile.clicked.connect(self._onSendFile)
        toolbar.addWidget(self.btnFile)

        self.btnFolder = QPushButton('📁 发送文件夹')
        self.btnFolder.setStyleSheet(btn_style)
        self.btnFolder.clicked.connect(self._onSendFolder)
        toolbar.addWidget(self.btnFolder)

        self.btnBatch = QPushButton('📦 批量发送')
        self.btnBatch.setStyleSheet(btn_style)
        self.btnBatch.clicked.connect(self._onBatchSend)
        toolbar.addWidget(self.btnBatch)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # --- 底部：消息输入 + 发送按钮 ---
        bottom = QHBoxLayout()
        bottom.setSpacing(6)

        self.textInput = QTextEdit()
        self.textInput.setMaximumHeight(80)
        self.textInput.setPlaceholderText('输入消息，Enter 发送，Ctrl+Enter 换行')
        self.textInput.installEventFilter(self)
        bottom.addWidget(self.textInput, 1)

        self.btnSend = QPushButton('发送')
        self.btnSend.setMinimumWidth(70)
        self.btnSend.clicked.connect(self._onSendMessage)
        bottom.addWidget(self.btnSend)

        layout.addLayout(bottom)

        # --- 状态栏 ---
        self.statusBar().showMessage('就绪')

        self._updateFileButtons()

    def eventFilter(self, source, event):
        """捕获输入框的 Enter 键发送消息"""
        if source is self.textInput and event.type() == event.KeyPress:
            key = event.key()
            modifiers = event.modifiers()
            if key in (Qt.Key_Enter, Qt.Key_Return):
                if modifiers & Qt.ControlModifier:
                    # Ctrl+Enter → 换行
                    return super().eventFilter(source, event)
                else:
                    # Enter → 发送
                    self._onSendMessage()
                    return True
        return super().eventFilter(source, event)

    def _connectSignals(self):
        self._userSignal.connect(self._onUserUpdate)
        self._contentSignal.connect(self._onContentRecv)
        self._fileRecvSignal.connect(self._onFileRecvDialog)

    # ==================== 按钮状态 ====================

    def _updateFileButtons(self):
        enabled = self._current_user_id is not None
        self.btnFile.setEnabled(enabled)
        self.btnFolder.setEnabled(enabled)
        self.btnBatch.setEnabled(enabled)

    # ==================== 用户管理 ====================

    def _onUserUpdate(self, user):
        """后台线程上报的用户更新（上线/状态变化）"""
        uid = user.getId()
        if user.state == setting.FRIEND_ONLINE:
            self._users[uid] = user
            self._updateCombo()
        elif user.state == setting.FRIEND_OFFLINE:
            self._users.pop(uid, None)
            if self._current_user_id == uid:
                self._current_user_id = None
                self.chatHistory.clear()
                self._updateFileButtons()
            self._updateCombo()

    def _updateCombo(self):
        """同步 _users 到 QComboBox"""
        current_id = self._current_user_id
        self.comboUser.blockSignals(True)
        self.comboUser.clear()
        self.comboUser.addItem('-- 请选择联系人 --', None)
        for uid, u in self._users.items():
            label = '%s (%s)' % (u.nickname, u.groupname)
            self.comboUser.addItem(label, uid)
        # 恢复之前选中的用户
        if current_id and current_id in self._users:
            for i in range(self.comboUser.count()):
                if self.comboUser.itemData(i) == current_id:
                    self.comboUser.setCurrentIndex(i)
                    break
        self.comboUser.blockSignals(False)

    def _onUserSelected(self, index):
        """用户在 ComboBox 中选择了联系人"""
        if index < 0:
            return
        uid = self.comboUser.itemData(index)
        if uid is None:
            return
        user = self._users.get(uid)
        if user is None:
            return
        self._current_user_id = uid
        self._updateFileButtons()
        self._loadChatHistory(user)

    # ==================== 聊天记录 ====================

    def _loadChatHistory(self, user):
        """加载与指定用户的聊天记录到 QTextEdit"""
        self.chatHistory.clear()
        for content in user.lstContents:
            self._appendContent(content)

    def _appendContent(self, content):
        """追加一条消息到聊天记录"""
        time_str = content.time.strftime('%H:%M:%S')
        if content.type == ContentType.TEXT:
            if content.tx:
                self.chatHistory.append(
                    '<div style="color:#888;">我 [%s]</div>'
                    '<div style="margin-bottom:4px;">%s</div>'
                    % (time_str, content.text))
            else:
                self.chatHistory.append(
                    '<div style="color:#888;">%s [%s]</div>'
                    '<div style="margin-bottom:4px;color:#1a6fb5;">%s</div>'
                    % (content.peer_name if hasattr(content, 'peer_name') else '对方',
                       time_str, content.text))

    # ==================== 发送消息 ====================

    def _onSendMessage(self):
        text = self.textInput.toPlainText().strip()
        if not text:
            return
        if self._current_user_id is None:
            QMessageBox.information(self, '提示', '请先选择聊天对象')
            return

        content = TextContent(text, '', self._current_user_id, True)
        Instance.appendContent(content)
        self._appendContent(content)
        self.textInput.clear()

    # ==================== 文件发送 ====================

    def _checkUser(self):
        if self._current_user_id is None:
            QMessageBox.information(self, '提示', '请先选择聊天对象')
            return None
        return self._current_user_id

    def _onSendFile(self):
        peer_id = self._checkUser()
        if peer_id is None:
            return
        filepath, _ = QFileDialog.getOpenFileName(
            self, '选择要发送的文件', '', '所有文件 (*.*)')
        if filepath:
            Instance.sendFile(peer_id, filepath)
            self._showTip('已发送: %s (%s)' % (
                os.path.basename(filepath),
                self._formatSize(os.path.getsize(filepath))))

    def _onSendFolder(self):
        peer_id = self._checkUser()
        if peer_id is None:
            return
        folderpath = QFileDialog.getExistingDirectory(self, '选择要发送的文件夹')
        if folderpath:
            total = 0
            for dirpath, _, filenames in os.walk(folderpath):
                for f in filenames:
                    try:
                        total += os.path.getsize(os.path.join(dirpath, f))
                    except Exception:
                        pass
            Instance.sendFolder(peer_id, folderpath)
            self._showTip('已发送: %s (%s)' % (
                os.path.basename(folderpath), self._formatSize(total)))

    def _onBatchSend(self):
        peer_id = self._checkUser()
        if peer_id is None:
            return
        files, _ = QFileDialog.getOpenFileNames(
            self, '选择要批量发送的文件', '', '所有文件 (*.*)')
        if files:
            Instance.sendBatchFiles(peer_id, files)
            total = sum(os.path.getsize(fp) for fp in files)
            self._showTip('已发送: %d 个文件 (%s)' % (len(files), self._formatSize(total)))

    def _showTip(self, msg):
        self.statusBar().showMessage(msg, 5000)

    @staticmethod
    def _formatSize(size):
        if size >= 1024 * 1024 * 1024:
            return '%.1f GB' % (size / (1024 * 1024 * 1024))
        if size >= 1024 * 1024:
            return '%.1f MB' % (size / (1024 * 1024))
        if size >= 1024:
            return '%.1f KB' % (size / 1024)
        return '%d B' % size

    # ==================== 文件接收 ====================

    def _file_recv_handler(self, filename, filesize, filetype):
        """跨线程回调：发射信号到主线程，阻塞等待用户选择"""
        result_queue = queue.Queue()
        self._fileRecvSignal.emit(filename, filesize, filetype, result_queue)
        try:
            save_path, accepted = result_queue.get(timeout=120)
        except queue.Empty:
            save_path, accepted = None, False
        return save_path, accepted

    def _onFileRecvDialog(self, filename, filesize, filetype, result_queue):
        """在主线程弹出接收对话框"""
        is_batch = (filetype == -1)
        if is_batch:
            type_name = '批量文件'
        elif filetype >= 2:
            type_name = '文件夹'
        else:
            type_name = '文件'

        size_str = self._formatSize(filesize)

        msg = QMessageBox(self)
        msg.setWindowTitle('收到%s' % type_name)
        msg.setText('%s\n%s (%s)' % (filename, type_name, size_str))
        btn_accept = msg.addButton('接收', QMessageBox.AcceptRole)
        btn_saveas = msg.addButton('存到...' if is_batch else '另存为...', QMessageBox.ApplyRole)
        btn_reject = msg.addButton('拒绝', QMessageBox.RejectRole)
        msg.setDefaultButton(btn_accept)
        msg.exec_()

        clicked = msg.clickedButton()
        if clicked == btn_reject:
            result_queue.put((None, False))
        elif clicked == btn_saveas:
            if is_batch:
                path = QFileDialog.getExistingDirectory(
                    self, '选择保存目录', os.path.expanduser('~'))
                if path:
                    result_queue.put((path, True))
                else:
                    result_queue.put((None, False))
            else:
                dft = os.path.join(os.path.expanduser('~'), 'Downloads', filename)
                path, _ = QFileDialog.getSaveFileName(self, '保存到', dft)
                if path:
                    result_queue.put((path, True))
                else:
                    result_queue.put((None, False))
        else:
            result_queue.put((None, True))

    # ==================== 引擎回调 ====================

    def _onContentRecv(self, content):
        """收到消息：如果是当前聊天对象则实时显示"""
        if self._current_user_id and content.peer == self._current_user_id:
            self._appendContent(content)

    def onViewDispatch(self, view):
        """引擎回调入口，分发到对应信号"""
        if view.type() == VIEW_USER:
            self._userSignal.emit(view.user)
        elif view.type() == VIEW_CONTENT:
            self._contentSignal.emit(view.content)


# ==================== 入口 ====================

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()

    UDPSERVER = UDPServer((setting.IPADDRESS, setting.PORT), UdpHandle)
    UDPSERVER.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    server_thread = threading.Thread(
        target=UDPSERVER.serve_forever, name='UDP-Server', daemon=True)
    server_thread.start()

    Instance.start(UDPSERVER.socket.sendto, window.onViewDispatch)
    Instance.file_recv_cb = window._file_recv_handler

    window.show()
    sys.exit(app.exec_())
