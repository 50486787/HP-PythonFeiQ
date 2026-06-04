"""气泡渲染 Delegate — 纯绘制，不涉及业务逻辑"""
from PyQt5.QtWidgets import QStyledItemDelegate
from PyQt5.QtCore import Qt, QSize, QRect, QRectF
from PyQt5.QtGui import (
    QFont, QPainter, QPainterPath, QTextDocument, QPen, QBrush, QColor
)

from gui.resources import (
    BUBBLE_SELF_BG, BUBBLE_SELF_BORDER,
    BUBBLE_OTHER_BG, BUBBLE_OTHER_BORDER,
    format_size,
)

# UserRole 常量（与 chat_view 共享）
ROLE_IS_SELF = Qt.UserRole + 1
ROLE_TIME = Qt.UserRole + 2
ROLE_PROGRESS = Qt.UserRole + 3
ROLE_MSG_TYPE = Qt.UserRole + 4
ROLE_TRANSFER_DONE = Qt.UserRole + 5
ROLE_TRANSFER_CANCELLED = Qt.UserRole + 6
ROLE_FILE_NAME = Qt.UserRole + 7
ROLE_FILE_SIZE = Qt.UserRole + 8
ROLE_CANCEL_RECT = Qt.UserRole + 9
ROLE_BYTES_DONE = Qt.UserRole + 10
ROLE_BYTES_TOTAL = Qt.UserRole + 11
ROLE_FAIL_REASON = Qt.UserRole + 12


class BubbleDelegate(QStyledItemDelegate):
    """TIM 风格扁平气泡 + 文件进度条 + 取消按钮"""

    MAX_WIDTH_RATIO = 0.6

    def __init__(self, parent=None):
        super().__init__(parent)
        self._doc = QTextDocument()

    # ─── size hint ────────────────────────────────────────────

    def sizeHint(self, option, index):
        text = index.data(Qt.DisplayRole) or ''
        msg_type = index.data(ROLE_MSG_TYPE) or 'text'
        progress = index.data(ROLE_PROGRESS)
        if progress is None:
            progress = -1.0
        transfer_done = index.data(ROLE_TRANSFER_DONE) or False
        transfer_cancelled = index.data(ROLE_TRANSFER_CANCELLED) or False
        is_file = (msg_type == 'file')
        show_progress = is_file and not transfer_done and not transfer_cancelled and progress >= 0
        has_status = is_file and (transfer_done or transfer_cancelled)

        view_width = option.widget.viewport().width() if option.widget else 400
        max_w = int(view_width * self.MAX_WIDTH_RATIO)

        self._doc.setDefaultFont(option.font)
        self._doc.setTextWidth(max_w - 28)
        self._doc.setHtml(text)
        doc_h = self._doc.size().height()

        extra = 0
        if show_progress:
            extra += 30
        if has_status:
            extra += 16
        return QSize(view_width, max(int(doc_h) + 36 + extra, 40))

    # ─── paint ────────────────────────────────────────────────

    def paint(self, painter: QPainter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        is_self = index.data(ROLE_IS_SELF)
        text = index.data(Qt.DisplayRole) or ''
        time_str = index.data(ROLE_TIME) or ''
        msg_type = index.data(ROLE_MSG_TYPE) or 'text'
        progress = index.data(ROLE_PROGRESS)
        if progress is None:
            progress = -1.0
        transfer_done = index.data(ROLE_TRANSFER_DONE) or False
        transfer_cancelled = index.data(ROLE_TRANSFER_CANCELLED) or False
        bytes_done = index.data(ROLE_BYTES_DONE) or 0
        total = index.data(ROLE_BYTES_TOTAL) or 0

        is_file = (msg_type == 'file')
        show_progress = is_file and not transfer_done and not transfer_cancelled and progress >= 0

        view_width = option.widget.viewport().width() if option.widget else 400
        max_bubble_w = int(view_width * self.MAX_WIDTH_RATIO)

        self._doc.setDefaultFont(option.font)
        self._doc.setTextWidth(max_bubble_w - 28)
        self._doc.setHtml(text)
        doc_h = self._doc.size().height()
        doc_w = self._doc.size().width()

        bubble_w = min(int(doc_w) + 28, max_bubble_w)
        progress_h = 28 if show_progress else 0
        status_h = 16 if (is_file and (transfer_done or transfer_cancelled)) else 0
        bubble_h = max(int(doc_h) + 16, 24) + progress_h + status_h

        margin = 12
        bubble_x = (view_width - bubble_w - margin) if is_self else margin
        bubble_y = option.rect.top() + 4
        bubble_rect = QRect(bubble_x, bubble_y, bubble_w, int(bubble_h))

        # 气泡背景
        path = QPainterPath()
        path.addRoundedRect(
            QRectF(0, 0, float(bubble_w), float(bubble_h)).translated(bubble_rect.topLeft()),
            8.0, 8.0)
        bg = QColor(BUBBLE_SELF_BG) if is_self else QColor(BUBBLE_OTHER_BG)
        border = QColor(BUBBLE_SELF_BORDER) if is_self else QColor(BUBBLE_OTHER_BORDER)
        painter.fillPath(path, bg)
        painter.setPen(QPen(border, 1))
        painter.drawPath(path)

        # 文本
        painter.translate(bubble_x + 14, bubble_y + 8)
        self._doc.drawContents(painter)
        painter.resetTransform()
        painter.restore()

        # 进度条 / 状态
        if show_progress:
            self._draw_progress(painter, bubble_x, bubble_y + int(doc_h) + 16,
                                bubble_w, progress, bytes_done, total, is_self,
                                index, option)
        elif is_file and transfer_done:
            self._draw_status(painter, bubble_x, bubble_y, int(doc_h),
                              bubble_w, is_self,
                              index.data(ROLE_FAIL_REASON) or '')
        elif is_file and transfer_cancelled:
            self._draw_status(painter, bubble_x, bubble_y, int(doc_h),
                              bubble_w, is_self, fallback='✗ 已取消')

        # 时间戳
        painter.save()
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)
        painter.setPen(QColor('#999'))
        time_y = bubble_y + int(bubble_h) + 2
        time_rect = QRect(bubble_x, time_y, bubble_w, 16)
        align = Qt.AlignRight if is_self else Qt.AlignLeft
        painter.drawText(time_rect, align, time_str)
        painter.restore()

    # ─── status line ──────────────────────────────────────────

    def _draw_status(self, painter, bx, by, doc_h, bw, is_self, fail_reason='',
                     fallback=''):
        painter.save()
        if fail_reason:
            painter.setPen(QColor('#e67e22'))
            text = f'✗ {fail_reason}'
        elif fallback:
            painter.setPen(QColor('#999'))
            text = fallback
        else:
            painter.setPen(QColor('#4caf50'))
            text = '✓ 发送完成' if is_self else '✓ 接收完成'
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(QRect(bx + 14, by + doc_h + 14, bw - 28, 16),
                         Qt.AlignLeft, text)
        painter.restore()

    # ─── progress bar + cancel button ─────────────────────────

    def _draw_progress(self, painter, bx, by, bw, progress,
                       bytes_done, total, is_self, index, option):
        painter.save()

        bar_w = bw - 60
        bar_h = 10
        bar_x = bx + 14
        bar_y = by + 2

        # 背景
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor('#e0e0e0'))
        painter.drawRoundedRect(
            QRectF(float(bar_x), float(bar_y), float(bar_w), float(bar_h)), 3, 3)

        # 填充
        if progress > 0:
            fill = QColor('#f5a623') if is_self else QColor('#4caf50')
            painter.setBrush(fill)
            fill_w = max(int(bar_w * progress), 4)
            painter.drawRoundedRect(
                QRectF(float(bar_x), float(bar_y), float(fill_w), float(bar_h)), 3, 3)

        # 百分比 + 大小
        painter.setPen(QColor('#666'))
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)
        pct = int(progress * 100)
        info = '%d%%' % pct
        if bytes_done > 0 and total > 0:
            info += ' | %s/%s' % (format_size(bytes_done), format_size(total))
        painter.drawText(QRect(bar_x, bar_y + bar_h + 2, bar_w, 14),
                         Qt.AlignLeft, info)

        # 取消按钮
        cancel_w, cancel_h = 36, 20
        cancel_x = bx + bw - cancel_w - 8
        cancel_y = by + (bar_h + 14 - cancel_h) // 2
        painter.setPen(QPen(QColor('#c0c0c0'), 1))
        painter.setBrush(QColor('#fafafa'))
        painter.drawRoundedRect(
            QRectF(float(cancel_x), float(cancel_y),
                   float(cancel_w), float(cancel_h)), 3, 3)
        painter.setPen(QColor('#999'))
        painter.drawText(QRect(cancel_x, cancel_y, cancel_w, cancel_h),
                         Qt.AlignCenter, '取消')

        # 存储取消按钮区域（viewport 坐标）
        index.model().setData(index, (cancel_x, cancel_y, cancel_w, cancel_h),
                              ROLE_CANCEL_RECT)

        painter.restore()
