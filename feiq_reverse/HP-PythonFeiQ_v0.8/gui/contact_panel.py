"""联系人面板 — 搜索框 + 可折叠分组树"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QTreeWidget, QTreeWidgetItem
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QBrush, QColor

from gui.resources import SIDEBAR_BG, ONLINE_DOT


class ContactPanel(QWidget):
    """左侧联系人面板"""

    contactSelected = pyqtSignal(str)  # user_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._groups = {}    # groupname -> QTreeWidgetItem
        self._contacts = {}  # user_id -> QTreeWidgetItem
        self._all_items = []  # (user_id, groupname, nickname, online, last_message)
        self._selected_user_id = None  # 跨重建保留选中
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
        self.tree.setRootIsDecorated(True)
        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.setStyleSheet(
            'QTreeWidget { background: %s; border: none; font-size: 13px; }'
            'QTreeWidget::item { padding: 4px 6px; }'
            'QTreeWidget::item:selected { background: #ffe4b5; color: #333; }'
            'QTreeWidget::branch:has-children:!adjoins-item { border: none; }'
            % SIDEBAR_BG)
        layout.addWidget(self.tree)

    def upsert_contact(self, user_id: str, nickname: str, groupname: str,
                       online: bool = True, last_message: str = ''):
        """添加或更新联系人"""
        changed = False
        for i, (uid, *_) in enumerate(self._all_items):
            if uid == user_id:
                new_data = (user_id, groupname, nickname, online, last_message)
                if self._all_items[i] != new_data:
                    self._all_items[i] = new_data
                    changed = True
                break
        else:
            self._all_items.append((user_id, groupname, nickname, online, last_message))
            changed = True

        if changed:
            self._rebuild_tree()

    def remove_contact(self, user_id: str):
        """移除联系人（下线）"""
        self._all_items = [x for x in self._all_items if x[0] != user_id]
        self._contacts.pop(user_id, None)
        self._rebuild_tree()

    def set_online_status(self, user_id: str, online: bool):
        """更新在线状态"""
        for i, (uid, g, n, _, lm) in enumerate(self._all_items):
            if uid == user_id:
                self._all_items[i] = (uid, g, n, online, lm)
                break
        self._rebuild_tree()

    def _rebuild_tree(self):
        """完全重建树（保证分组准确）"""
        self.tree.clear()
        self._groups.clear()
        self._contacts.clear()

        # 按分组排序
        grouped = {}
        for user_id, groupname, nickname, online, last_message in self._all_items:
            gname = groupname or '默认分组'
            if gname not in grouped:
                grouped[gname] = []
            grouped[gname].append((user_id, nickname, online, last_message))

        search_text = self.search_box.text().lower().strip()

        for gname in sorted(grouped.keys()):
            members = grouped[gname]
            online_count = sum(1 for _, _, on, _ in members if on)

            group_item = QTreeWidgetItem()
            group_item.setText(0, f'{gname} ({online_count})')
            group_item.setData(0, Qt.UserRole, '')  # 分组标记
            group_item.setFlags(group_item.flags() & ~Qt.ItemIsSelectable)
            self.tree.addTopLevelItem(group_item)
            self._groups[gname] = group_item

            visible_count = 0
            for user_id, nickname, online, last_message in members:
                # 空昵称 fallback（引擎初次发现时昵称尚未获取）
                display_name = nickname.strip() or user_id.split('@')[0] or '(在线)'
                # 搜索过滤
                if search_text and search_text not in display_name.lower():
                    continue

                item = QTreeWidgetItem()
                prefix = '●' if online else '○'
                display = f'{prefix} {display_name}'
                item.setText(0, display)
                item.setData(0, Qt.UserRole, user_id)
                color = ONLINE_DOT if online else '#999'
                item.setForeground(0, QBrush(QColor(color)))

                # 最后消息作为 tooltip
                if last_message:
                    item.setToolTip(0, last_message[:100])

                group_item.addChild(item)
                self._contacts[user_id] = item
                visible_count += 1

            group_item.setExpanded(visible_count > 0)
            # 隐藏空分组（搜索后全部被过滤的情况）
            group_item.setHidden(visible_count == 0)

        # 恢复上次选中的联系人
        if self._selected_user_id and self._selected_user_id in self._contacts:
            item = self._contacts[self._selected_user_id]
            self.tree.setCurrentItem(item)

    def _on_search(self, text: str):
        """搜索过滤 — 重建树"""
        self._rebuild_tree()

    def _on_item_clicked(self, item: QTreeWidgetItem, col: int):
        user_id = item.data(0, Qt.UserRole)
        if user_id:  # 联系人条目，非分组标题
            self._selected_user_id = user_id
            self.contactSelected.emit(user_id)
