"""Smoke tests for desktop pet."""
import sys
import pytest


def test_pyqt5_available():
    """PyQt5 should be installed and importable."""
    from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow
    from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont
    from PyQt5.QtCore import Qt, QPoint
    assert True  # imports succeeded


def test_app_instantiation():
    """QApplication can be created without a display (headless)."""
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    assert app is not None
