"""主窗口 — 组装 contact_panel + chat_view + 引擎桥接 + 拖拽 + 托盘"""
import os
import queue

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QLabel, QPushButton, QMessageBox, QFileDialog, QApplication,
    QSystemTrayIcon, QMenu, QAction
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QBrush, QColor, QFont, QPen

from gui.models import ContactItem, ChatMessage
from gui.resources import (
    HEADER_START, HEADER_END, HEADER_TEXT, MAIN_QSS, format_size
)
from gui.contact_panel import ContactPanel
from gui.chat_view import ChatView
from gui.settings_dialog import SettingsDialog, load_settings

from WorkThread import Instance
from UserManager import VIEW_USER, VIEW_CONTENT
from feiqstruct import TextContent, ContentType
import setting


class MainWindow(QMainWindow):
    # 跨线程信号（引擎回调在后台线程，通过信号桥接到主线程）
    _userSignal = pyqtSignal(object)       # User 对象
    _contentSignal = pyqtSignal(object)    # PacketContent 对象
    _fileRecvSignal = pyqtSignal(str, int, int, object)  # name, size, type, result_queue

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

    # ==================== UI 构建 ====================

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
        """浓橙渐变顶栏 32px"""
        header = QWidget()
        header.setFixedHeight(32)
        header.setStyleSheet(
            'QWidget { background: qlineargradient(x1:0, y1:0, x2:0, y2:1,'
            'stop:0 %s, stop:1 %s); }' % (HEADER_START, HEADER_END))
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(12, 0, 8, 0)
        h_layout.setSpacing(4)

        title = QLabel('HP-PythonFeiQ')
        title.setStyleSheet(
            'QLabel { color: %s; font-size: 12px; font-weight: bold;'
            'background: transparent; }' % HEADER_TEXT)
        h_layout.addWidget(title)

        h_layout.addStretch()

        # 当前用户名
        self.lbl_username = QLabel('')
        self.lbl_username.setStyleSheet(
            'QLabel { color: %s; font-size: 11px;'
            'background: transparent; opacity: 0.85; }' % HEADER_TEXT)
        h_layout.addWidget(self.lbl_username)

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
        # 生成托盘图标
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
        self._tray.setToolTip('HP-PythonFeiQ')

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
        """关闭窗口 → 最小化到托盘"""
        event.ignore()
        self.hide()
        self._tray.showMessage(
            'HP-PythonFeiQ', '已最小化到系统托盘',
            QSystemTrayIcon.Information, 2000)

    # ==================== 设置对话框 ====================

    def _on_open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec_():
            self._settings = load_settings()
            # 更新顶栏用户名
            nickname = self._settings.get('nickname', '')
            if nickname:
                self.lbl_username.setText(nickname)

    # ==================== 联系人交互 ====================

    def _on_contact_selected(self, user_id: str):
        self._current_user_id = user_id
        user = self._users.get(user_id)
        if user:
            self.chat_title.setText(
                f'与 {user.nickname} ({user.groupname}) 聊天中...')
            # 加载引擎中的历史消息
            if hasattr(user, 'lstContents'):
                chat_msgs = []
                for content in user.lstContents:
                    if hasattr(content, 'type') and content.type == ContentType.TEXT:
                        chat_msgs.append(ChatMessage(
                            peer_id=str(content.peer),
                            text=getattr(content, 'text', ''),
                            is_send=content.tx,
                            time=content.time,
                        ))
                if chat_msgs:
                    self.chat_view.load_messages(chat_msgs)
                else:
                    self.chat_view.clear_messages()
            else:
                self.chat_view.clear_messages()

    # ==================== 消息发送 ====================

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

        # 更新联系人最后消息预览
        user = self._users.get(self._current_user_id)
        if user:
            self.contact_panel.upsert_contact(
                self._current_user_id,
                user.nickname,
                user.groupname,
                True,
                text[:30])

    # ==================== 消息接收 ====================

    def _on_content_recv(self, content):
        """收到消息（主线程）"""
        if content.type == ContentType.TEXT:
            msg = ChatMessage(
                peer_id=str(content.peer),
                text=content.text,
                is_send=content.tx,
                time=content.time,
            )
            # 保存到消息存储
            if content.peer not in self._msg_store:
                self._msg_store[content.peer] = []
            self._msg_store[content.peer].append(msg)

            # 当前选中用户 → 实时显示
            if self._current_user_id and str(content.peer) == self._current_user_id:
                self.chat_view.add_message(msg)

            # 更新联系人预览
            user = self._users.get(str(content.peer))
            if user:
                self.contact_panel.upsert_contact(
                    str(content.peer),
                    user.nickname,
                    user.groupname,
                    True,
                    content.text[:30])

            # 窗口未激活时托盘闪烁提示
            if not self.isActiveWindow():
                name = user.nickname if user else str(content.peer)
                self._tray.showMessage(
                    name,
                    content.text[:50],
                    QSystemTrayIcon.Information,
                    3000)

    # ==================== 用户状态 ====================

    def _on_user_update(self, user):
        """用户上线/下线"""
        uid = user.getId()
        if user.state == setting.FRIEND_ONLINE:
            self._users[uid] = user
            self.contact_panel.upsert_contact(
                uid, user.nickname, user.groupname, True)
        elif user.state == setting.FRIEND_OFFLINE:
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
            # 图片通过 sendFile 传输，同时在聊天区显示缩略图消息
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
        """引擎回调（后台线程）→ 发射信号到主线程，阻塞等待用户选择"""
        result_queue = queue.Queue()
        self._fileRecvSignal.emit(filename, filesize, filetype, result_queue)
        try:
            save_path, accepted = result_queue.get(timeout=120)
        except queue.Empty:
            save_path, accepted = None, False
        return save_path, accepted

    def _on_file_recv_dialog(self, filename: str, filesize: int,
                             filetype: int, result_queue):
        """主线程弹出文件接收对话框"""
        is_batch = (filetype == -1)
        if is_batch:
            type_name = '批量文件'
        elif filetype >= 2:
            type_name = '文件夹'
        else:
            type_name = '文件'

        size_str = format_size(filesize)

        msg = QMessageBox(self)
        msg.setWindowTitle(f'收到{type_name}')
        msg.setText(f'{filename}\n{type_name} ({size_str})')

        btn_accept = msg.addButton('接收', QMessageBox.AcceptRole)
        btn_saveas = msg.addButton(
            '存到...' if is_batch else '另存为...', QMessageBox.ApplyRole)
        btn_reject = msg.addButton('拒绝', QMessageBox.RejectRole)
        msg.setDefaultButton(btn_accept)
        msg.exec_()

        clicked = msg.clickedButton()
        if clicked == btn_reject:
            result_queue.put((None, False))
        elif clicked == btn_saveas:
            save_path = self._settings.get(
                'save_path', os.path.join(os.path.expanduser('~'), 'Downloads'))
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

    # ==================== 拖拽支持（全窗口） ====================

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._show_drag_overlay()

    def dragLeaveEvent(self, event):
        self._hide_drag_overlay()

    def dropEvent(self, event):
        self._hide_drag_overlay()
        if not self._current_user_id:
            return

        urls = event.mimeData().urls()
        paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
        if not paths:
            return

        if len(paths) == 1 and os.path.isfile(paths[0]):
            Instance.sendFile(self._current_user_id, paths[0])
        elif len(paths) == 1 and os.path.isdir(paths[0]):
            Instance.sendFolder(self._current_user_id, paths[0])
        else:
            files = [p for p in paths if os.path.isfile(p)]
            if files:
                Instance.sendBatchFiles(self._current_user_id, files)

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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._drag_overlay and self._drag_overlay.isVisible():
            self._drag_overlay.setGeometry(self.rect())

    # ==================== 引擎回调入口（后台线程安全） ====================

    def onViewDispatch(self, view):
        """引擎回调 — 可能被后台线程调用，通过信号桥接到主线程"""
        if view.type() == VIEW_USER:
            self._userSignal.emit(view.user)
        elif view.type() == VIEW_CONTENT:
            self._contentSignal.emit(view.content)
