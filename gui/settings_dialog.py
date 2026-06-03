"""设置对话框 — 个人信息、文件路径、防火墙、多网段、开机启动"""
import os
import json
import sys
import subprocess

from PyQt5.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QCheckBox,
    QListWidget, QListWidgetItem, QMessageBox, QFormLayout
)
from PyQt5.QtCore import Qt

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
        self.edit_save_path.setPlaceholderText('选择默认文件保存目录')
        layout.addWidget(self.edit_save_path)

        btn_browse = QPushButton('浏览...')
        btn_browse.clicked.connect(self._on_browse_path)
        layout.addWidget(btn_browse)

        return w

    def _tab_firewall(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        info = QLabel(
            '飞秋使用 UDP+TCP 端口 2425 通信。\n'
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
            '通过注册表 HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run 实现，\n'
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
                stderr = e.stderr.decode('gbk', errors='replace') if e.stderr else str(e)
                QMessageBox.warning(self, '防火墙', f'添加规则失败:\n{stderr}')
                break

        if success:
            QMessageBox.information(self, '防火墙', '已成功添加 UDP+TCP 2425 端口入站规则！')

    def _on_add_subnet(self):
        addr = self.edit_subnet.text().strip()
        if addr:
            # 简单校验 IP 格式
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
                    os.path.join(os.path.dirname(__file__), 'main.py'))
                winreg.SetValueEx(key, 'HP-PythonFeiQ', 0, winreg.REG_SZ,
                                  f'"{exe_path}" "{script_path}"')
            else:
                try:
                    winreg.DeleteValue(key, 'HP-PythonFeiQ')
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception:
            pass  # 非 Windows 平台或无管理员权限
