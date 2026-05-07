"""Windows 11 Desktop Pet - a simple smiley face that lives on your desktop."""
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush
from PyQt5.QtCore import Qt, QPoint, QRectF

SIZE = 128


class PetWidget(QWidget):
    """Draws the pet character (smiley face)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(SIZE, SIZE)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Body (yellow circle)
        center = self.rect().center()
        radius = SIZE // 2 - 8
        painter.setBrush(QBrush(QColor("#FFD700")))
        painter.setPen(QPen(QColor("#CC8800"), 3))
        painter.drawEllipse(center, radius, radius)

        # Eyes
        eye_radius = 8
        pupil_radius = 3
        left_eye_x = center.x() - SIZE // 6
        right_eye_x = center.x() + SIZE // 6
        eye_y = center.y() - SIZE // 8

        painter.setBrush(QBrush(Qt.white))
        painter.setPen(QPen(Qt.black, 2))
        painter.drawEllipse(QPoint(left_eye_x, eye_y), eye_radius, eye_radius)
        painter.drawEllipse(QPoint(right_eye_x, eye_y), eye_radius, eye_radius)

        # Pupils
        painter.setBrush(QBrush(Qt.black))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPoint(left_eye_x + 2, eye_y), pupil_radius, pupil_radius)
        painter.drawEllipse(QPoint(right_eye_x + 2, eye_y), pupil_radius, pupil_radius)

        # Mouth (arc smile)
        painter.setPen(QPen(Qt.black, 2))
        painter.setBrush(Qt.NoBrush)
        mouth_rect = QRectF(
            center.x() - SIZE // 6,
            center.y() - SIZE // 12,
            SIZE // 3,
            SIZE // 4,
        )
        painter.drawArc(mouth_rect, 0, 180 * 16)  # 180 degrees = smile


class PetWindow(QMainWindow):
    """Frameless transparent always-on-top window hosting the pet."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(SIZE, SIZE)

        self.pet = PetWidget(self)
        self.setCentralWidget(self.pet)

        self._drag_pos = None

        # Center on screen
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - SIZE) // 2
        y = (screen.height() - SIZE) // 2
        self.move(x, y)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()
