import glob
import os
import sys
import shutil
from PyQt5.QtWidgets import *
sys.path.append('../')
import main


def test_menu_in_tray():
    app = QApplication(sys.argv)

    main.TrayIcon('img/dart.png', app).constructor_menu()


