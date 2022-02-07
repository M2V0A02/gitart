import pytest
import sys
import json
from PyQt5.QtWidgets import *
sys.path.append('../')
import main


class TestTrayIcon:
    def test__init__tray_icon_creation_successfully(self):
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)
        tray_icon = main.TrayIcon('../img/icon.png', app)
        