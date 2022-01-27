from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import sys

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
icon = QIcon("icon.png")
tray = QSystemTrayIcon()
tray.setIcon(icon)
tray.setVisible(True)
menu = QMenu()
quit = QAction("Выйти")
quit.triggered.connect(app.quit)
menu.addAction(quit)
tray.setContextMenu(menu)
app.exec_()