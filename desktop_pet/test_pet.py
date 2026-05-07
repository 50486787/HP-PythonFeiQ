"""Smoke tests for desktop pet."""
import os
import sys

import pytest
from PyQt5.QtCore import Qt, QEvent, QPoint, QPointF
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QApplication

from pet import PetWidget, PetWindow


@pytest.fixture(scope="session")
def qapp():
    """Session-scoped QApplication for headless testing."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app
    app.quit()


def test_app_instantiation(qapp):
    """QApplication can be created without a display (headless)."""
    assert qapp is not None


def test_pet_widget_creation(qapp):
    """PetWidget should be creatable and have correct size."""
    widget = PetWidget()
    assert widget.width() == 128
    assert widget.height() == 128


def test_pet_widget_transparent(qapp):
    """PetWidget should have transparent background attribute."""
    widget = PetWidget()
    assert widget.testAttribute(Qt.WA_TranslucentBackground)


def test_pet_window_flags(qapp):
    """PetWindow should be frameless, transparent, always-on-top, and skip taskbar."""
    window = PetWindow()
    flags = window.windowFlags()
    assert flags & Qt.FramelessWindowHint
    assert flags & Qt.WindowStaysOnTopHint
    assert flags & Qt.Tool
    assert window.testAttribute(Qt.WA_TranslucentBackground)


def test_pet_window_centered(qapp):
    """PetWindow should be created at the center of the screen."""
    window = PetWindow()
    screen = qapp.primaryScreen().availableGeometry()
    expected_x = (screen.width() - window.width()) // 2
    expected_y = (screen.height() - window.height()) // 2
    assert window.x() == expected_x
    assert window.y() == expected_y


def test_pet_window_drag(qapp):
    """PetWindow drag: mousePressEvent sets _drag_pos, mouseMoveEvent moves
    window, mouseReleaseEvent clears _drag_pos."""
    window = PetWindow()

    # Initial: no drag in progress
    assert window._drag_pos is None

    # Simulate left-button press
    press_local = QPointF(20, 20)
    press_global = QPointF(window.x() + 20, window.y() + 20)
    press_event = QMouseEvent(
        QEvent.MouseButtonPress,
        press_local, press_global,
        Qt.LeftButton, Qt.LeftButton, Qt.NoModifier,
    )
    window.mousePressEvent(press_event)

    # _drag_pos should now be set
    assert window._drag_pos is not None
    expected_drag = QPoint(
        int(press_global.x()), int(press_global.y())
    ) - window.frameGeometry().topLeft()
    assert window._drag_pos == expected_drag

    # Simulate mouse move with left button held
    move_local = QPointF(70, 50)
    move_global = QPointF(window.x() + 70, window.y() + 50)
    move_event = QMouseEvent(
        QEvent.MouseMove,
        move_local, move_global,
        Qt.NoButton, Qt.LeftButton, Qt.NoModifier,
    )
    old_pos = window.pos()
    window.mouseMoveEvent(move_event)

    # Window should have moved
    assert window.pos() != old_pos
    expected_new_pos = QPoint(
        int(move_global.x()), int(move_global.y())
    ) - expected_drag
    assert window.pos() == expected_new_pos

    # Simulate mouse release
    release_event = QMouseEvent(
        QEvent.MouseButtonRelease,
        move_local, move_global,
        Qt.LeftButton, Qt.NoButton, Qt.NoModifier,
    )
    window.mouseReleaseEvent(release_event)

    # _drag_pos should be cleared
    assert window._drag_pos is None
