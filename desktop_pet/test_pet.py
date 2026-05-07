"""Smoke tests for desktop pet."""
import os
import sys

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from pet import PetWidget


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
    from pet import PetWindow
    window = PetWindow()
    flags = window.windowFlags()
    assert flags & Qt.FramelessWindowHint
    assert flags & Qt.WindowStaysOnTopHint
    assert flags & Qt.Tool
    assert window.testAttribute(Qt.WA_TranslucentBackground)
