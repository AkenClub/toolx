import os


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    owns_app = app is None
    if owns_app:
        app = QApplication([])
    yield app
    if owns_app:
        app.quit()
