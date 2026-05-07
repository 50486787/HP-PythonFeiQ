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


def test_pet_widget_creation():
    """PetWidget should be creatable and have correct size."""
    import os
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    from pet import PetWidget
    widget = PetWidget()
    assert widget.width() == 128
    assert widget.height() == 128
    app.quit()


def test_pet_widget_transparent():
    """PetWidget should have transparent background attribute."""
    import os
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import Qt
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    from pet import PetWidget
    widget = PetWidget()
    assert widget.testAttribute(Qt.WA_TranslucentBackground)
    app.quit()
