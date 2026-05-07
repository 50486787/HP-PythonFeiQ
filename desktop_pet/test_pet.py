"""Smoke tests for desktop pet."""
import os
import sys


def test_pyqt5_available():
    """PyQt5 should be installed and importable."""
    from PyQt5.QtWidgets import QApplication


def test_app_instantiation():
    """QApplication can be created without a display (headless)."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    assert app is not None
    app.quit()
