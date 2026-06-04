"""主窗口 — 组装所有组件 + 引擎桥接 + 拖拽 + 托盘"""
import os
import queue

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QLabel, QPushButton, QMessageBox, QFileDialog, QApplication,
    QSystemTrayIcon, QMenu, QAction
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QBrush, QColor, QFont, QPen

from gui.models import ChatMessage
from gui.resources import MAIN_QSS, format_size
from gui.contact_panel import ContactPanel
from gui.chat_view import ChatView
from gui.transfer_manager import TransferManager
from gui.settings_dialog import SettingsDialog, load_settings
from gui.chat_history import save_messages as history_save, load_messages as history_load

from core.WorkThread import Instance
from core.UserManager import VIEW_USER, VIEW_CONTENT
from core.feiqstruct import TextContent, ContentType
from core import setting
class MainWindow(QMainWindow):
    _userSignal = pyqtSignal(object)
    _contentSignal = pyqtSignal(object)
    _fileRecvSignal = pyqtSignal(str, int, int, object)

    def __init__(self, width=1100, height=700):
        super().__init__()
        self.setWindowTitle('HP-PythonFeiQ v0.8')
        self.resize(width, height)
        self.setMinimumSize(760, 480)
        self.setStyleSheet(MAIN_QSS)

        self._current_user_id = None
        self._users = {}
        self._msg_store = {}
        self._settings = load_settings()
        self._drag_overlay = None
        self._received_files = set()  # (filename, filesize) 已收文件去重

        # 传输管理器（进度 + 取消 + 超时）
        self.transfer_mgr = TransferManager(self)

        self._build_ui()
        self._connect_signals()
        self._setup_tray()
        self.setAcceptDrops(True)

    # ═══════════════ UI 构建 ═══════════════════════════════════

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)

        self.contact_panel = ContactPanel()
        self.contact_panel.setMinimumWidth(180)
        self.contact_panel.contactSelected.connect(self._on_contact_selected)
        splitter.addWidget(self.contact_panel)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        title_bar = QWidget()
        title_bar.setStyleSheet(
            'QWidget { border-bottom: 1px solid #e8e4dc; background: #fafaf8; }')
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(14, 8, 8, 8)

        self.chat_title = QLabel('欢迎使用 HP-PythonFeiQ')
        self.chat_title.setStyleSheet(
            'QLabel { font-size: 13px; font-weight: bold; color: #666;'
            'background: transparent; border: none; }')
        tb_layout.addWidget(self.chat_title)
        tb_layout.addStretch()

        btn_settings = QPushButton('⚙ 设置')
        btn_settings.setCursor(Qt.PointingHandCursor)
        btn_settings.setStyleSheet(
            'QPushButton { padding: 3px 10px; border: 1px solid #d8d4cc;'
            'border-radius: 3px; background: #fff; font-size: 11px; color: #666; }'
            'QPushButton:hover { background: #f0f0f0; }')
        btn_settings.clicked.connect(self._on_open_settings)
        tb_layout.addWidget(btn_settings)

        right_layout.addWidget(title_bar)

        self.chat_view = ChatView()
        self.chat_view.sendMessage.connect(self._on_send_message)
        self.chat_view.sendFile.connect(self._on_send_file)
        self.chat_view.sendFolder.connect(self._on_send_folder)
        self.chat_view.sendBatchFiles.connect(self._on_batch_send)
        right_layout.addWidget(self.chat_view, 1)

        splitter.addWidget(right)
        splitter.setSizes([240, 860])
        layout.addWidget(splitter, 1)

    # ═══════════════ 信号连接 ═════════════════════════════════

    def _connect_signals(self):
        self._userSignal.connect(self._on_user_update)
        self._contentSignal.connect(self._on_content_recv)
        self._fileRecvSignal.connect(self._on_file_recv_dialog)

        # 传输管理器 ↔ 引擎
        self.transfer_mgr.bind_engine(Instance)

        # 传输管理器 → chat_view 显示更新
        self.transfer_mgr.progressUpdated.connect(self._on_transfer_progress)
        self.transfer_mgr.transferCancelled.connect(self.chat_view.mark_transfer_cancelled)
        self.transfer_mgr.transferFailed.connect(self.chat_view.mark_transfer_failed)

        # chat_view 取消按钮 → 传输管理器
        self.chat_view.cancelTransfer.connect(self.transfer_mgr.request_cancel)

    # ═══════════════ 系统托盘 ═════════════════════════════════

    def _setup_tray(self):
        self._tray = QSystemTrayIcon(self)
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
        event.ignore()
        self.hide()
        self._tray.showMessage(
            'HP-PythonFeiQ', '已最小化到系统托盘',
            QSystemTrayIcon.Information, 2000)

    # ═══════════════ 设置 ═════════════════════════════════════

    def _on_open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec_():
            self._settings = load_settings()

    # ═══════════════ 联系人 ═══════════════════════════════════

    def _on_contact_selected(self, user_id: str):
        self._current_user_id = user_id
        user = self._users.get(user_id)
        if user:
            self.chat_title.setText(
                f'与 {user.nickname} ({user.groupname}) 聊天中...')
        # 合并 JSON 持久化历史 + 当前会话内存记录
        msgs = self._msg_store.get(user_id, [])
        try:
            disk_msgs = history_load(user_id)
        except Exception:
            disk_msgs = []
        # 去重合并（以内存为准，磁盘补漏）
        seen = set()
        merged = []
        for m in msgs + disk_msgs:
            key = (m.time.isoformat(), m.text[:50])
            if key not in seen:
                seen.add(key)
                merged.append(m)
        if merged:
            self._msg_store[user_id] = merged
            self.chat_view.load_messages(merged)
        else:
            self.chat_view.clear_messages()

    # ═══════════════ 消息发送 ═════════════════════════════════

    def _on_send_message(self, text: str):
        if not self._current_user_id:
            QMessageBox.information(self, '提示', '请先选择聊天对象')
            return
        content = TextContent(text, '', self._current_user_id, True)
        Instance.appendContent(content)
        msg = ChatMessage(peer_id=self._current_user_id, text=text, is_send=True)
        self._save_and_show_msg(self._current_user_id, msg)
        user = self._users.get(self._current_user_id)
        if user:
            self.contact_panel.upsert_contact(
                self._current_user_id, user.nickname, user.groupname, True,
                text[:30])

    def _save_and_show_msg(self, peer_id: str, msg: ChatMessage):
        """存入 _msg_store → 自动写 JSON → 显示到当前聊天"""
        if peer_id not in self._msg_store:
            self._msg_store[peer_id] = []
        self._msg_store[peer_id].append(msg)
        self._persist(peer_id)
        if self._current_user_id == peer_id:
            self.chat_view.add_message(msg)

    def _persist(self, peer_id: str):
        """写 JSON"""
        try:
            history_save(peer_id, self._msg_store.get(peer_id, []))
        except Exception:
            pass

    def _on_transfer_progress(self, filename: str, bytes_done: int, total: int):
        """进度更新 → 完成时先持久化再刷新视图"""
        if bytes_done >= total > 0:
            self._mark_transfer_done(filename)
        self.chat_view.update_file_progress(filename, bytes_done, total)

    def _mark_transfer_done(self, filename: str):
        """传输完成时更新 _msg_store 中对应消息的 transfer_done 并写盘"""
        for msgs in self._msg_store.values():
            for m in msgs:
                if m.msg_type == 'file' and m.file_name == filename and not m.transfer_done:
                    m.transfer_done = True
                    m.transfer_bytes = m.file_size
                    self._persist(m.peer_id)
                    return

    # ═══════════════ 消息接收 ═════════════════════════════════

    def _on_content_recv(self, content):
        if content.type == ContentType.TEXT:
            text = content.text
            preview = content.text[:30]
            fname = ''; fsize = 0
        elif content.type == ContentType.FILE:
            fname = getattr(content, 'filename', '')
            fsize = getattr(content, 'file_size', 0)
            if (fname, fsize) in self._received_files:
                return  # 已收过的文件，跳过重复气泡
            text = f'[收到文件] {fname} ({format_size(fsize)})'
            preview = f'[文件] {fname}'
        else:
            return

        is_file = (content.type == ContentType.FILE)
        msg = ChatMessage(peer_id=str(content.peer), text=text,
                          is_send=False, time=content.time,
                          msg_type='file' if is_file else 'text',
                          file_name=fname if is_file else '',
                          file_size=fsize if is_file else 0)
        self._save_and_show_msg(str(content.peer), msg)
        if is_file:
            self._received_files.add((fname, fsize))  # 记录已收，后续重复自动跳过

        user = self._users.get(str(content.peer))
        if user:
            self.contact_panel.upsert_contact(
                str(content.peer), user.nickname, user.groupname, True, preview)

        if not self.isActiveWindow():
            name = user.nickname if user else str(content.peer)
            self._tray.showMessage(name, text[:50],
                                   QSystemTrayIcon.Information, 3000)

    # ═══════════════ 用户状态 ═════════════════════════════════

    def _on_user_update(self, user):
        uid = user.getId()
        if user.state == setting.FRIEND_ONLINE:
            # 引擎后续更新可能不带昵称，保留已有值
            old = self._users.get(uid)
            if old:
                if not user.nickname.strip() and old.nickname.strip():
                    user.nickname = old.nickname
                if not user.groupname.strip() and old.groupname.strip():
                    user.groupname = old.groupname
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

    # ═══════════════ 文件发送 ═════════════════════════════════

    def _guard_user(self):
        if not self._current_user_id:
            QMessageBox.information(self, '提示', '请先选择聊天对象')
            return None
        return self._current_user_id

    def _on_send_file(self, path: str):
        peer = self._guard_user()
        if not peer:
            return
        fname = os.path.basename(path)
        fsize = os.path.getsize(path)
        self.transfer_mgr.start_transfer(fname)
        msg = ChatMessage(peer_id=peer, text=f'[发送文件] {fname} ({format_size(fsize)})',
                          is_send=True, msg_type='file', file_path=path,
                          file_name=fname, file_size=fsize)
        self._save_and_show_msg(peer, msg)
        Instance.sendFile(peer, path)

    def _on_send_folder(self, path: str):
        peer = self._guard_user()
        if not peer:
            return
        fname = os.path.basename(path)
        self.transfer_mgr.start_transfer(fname)
        msg = ChatMessage(peer_id=peer, text=f'[发送文件夹] {fname}',
                          is_send=True, msg_type='file', file_path=path,
                          file_name=fname)
        self._save_and_show_msg(peer, msg)
        Instance.sendFolder(peer, path)

    def _on_batch_send(self, paths: list):
        peer = self._guard_user()
        if not peer:
            return
        for p in paths:
            fname = os.path.basename(p)
            fsize = os.path.getsize(p)
            self.transfer_mgr.start_transfer(fname)
            self._save_and_show_msg(peer, ChatMessage(
                peer_id=peer,
                text=f'[批量] {fname} ({format_size(fsize)})',
                is_send=True, msg_type='file', file_name=fname, file_size=fsize))
        Instance.sendBatchFiles(peer, paths)

    # ═══════════════ 文件接收 ═════════════════════════════════

    def _file_recv_handler(self, filename, filesize, filetype):
        # 去重：聊天记录最近 5 条 + 已收暂存（防竞态）
        for msgs in self._msg_store.values():
            for m in msgs[-5:]:
                if m.msg_type == 'file' and m.file_name == filename and m.file_size == filesize:
                    return None, False
        if (filename, filesize) in self._received_files:
            return None, False
        result_queue = queue.Queue()
        self._fileRecvSignal.emit(filename, filesize, filetype, result_queue)
        try:
            result = result_queue.get(timeout=120)
            if result[1]:
                self._received_files.add((filename, filesize))
            return result
        except queue.Empty:
            return None, False

    def _on_file_recv_dialog(self, filename, filesize, filetype, result_queue):
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
        msg.setDefaultButton(btn_accept)
        msg.exec_()

        clicked = msg.clickedButton()
        if clicked == btn_reject:
            result_queue.put((None, False))
        elif clicked == btn_accept:
            # 检查默认保存路径是否已有同名文件
            save_dir = self._settings.get(
                'save_path', os.path.join(os.path.expanduser('~'), 'Downloads'))
            default = os.path.join(save_dir, filename)
            if os.path.exists(default):
                overwrite = QMessageBox.question(
                    self, '文件已存在',
                    f'"{filename}" 已存在，是否覆盖？',
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if overwrite != QMessageBox.Yes:
                    result_queue.put((None, False))
                    return
            result_queue.put((None, True))
        elif clicked == btn_saveas:
            save_path = self._settings.get(
                'save_path', os.path.join(os.path.expanduser('~'), 'Downloads'))
            if is_batch:
                path = QFileDialog.getExistingDirectory(self, '选择保存目录', save_path)
                result_queue.put((path, True) if path else (None, False))
            else:
                default = os.path.join(save_path, filename)
                path, _ = QFileDialog.getSaveFileName(self, '保存到', default)
                result_queue.put((path, True) if path else (None, False))
        else:
            result_queue.put((None, True))

    # ═══════════════ 拖拽（仅聊天区） ═════════════════════════

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and event.pos().x() > self.contact_panel.width():
            event.acceptProposedAction()
            self._show_drag_overlay()

    def dragMoveEvent(self, event):
        if event.pos().x() > self.contact_panel.width():
            event.acceptProposedAction()
            self._show_drag_overlay()
        else:
            self._hide_drag_overlay()

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
            self._on_send_file(paths[0])
        elif len(paths) == 1 and os.path.isdir(paths[0]):
            self._on_send_folder(paths[0])
        else:
            files = [p for p in paths if os.path.isfile(p)]
            if files:
                self._on_batch_send(files)

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
        x = self.contact_panel.width()
        self._drag_overlay.setGeometry(x, 0, self.width() - x, self.height())
        self._drag_overlay.show()
        self._drag_overlay.raise_()

    def _hide_drag_overlay(self):
        if self._drag_overlay:
            self._drag_overlay.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._drag_overlay and self._drag_overlay.isVisible():
            x = self.contact_panel.width()
            self._drag_overlay.setGeometry(x, 0, self.width() - x, self.height())

    # ═══════════════ 引擎回调 ═════════════════════════════════

    def onViewDispatch(self, view):
        if view.type() == VIEW_USER:
            self._userSignal.emit(view.user)
        elif view.type() == VIEW_CONTENT:
            self._contentSignal.emit(view.content)
