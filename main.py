from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import sys
import yaml
import requests
import json

class TrayIcon():
    def __init__(self, icon, app):
        self.app = app
        self.tray = QSystemTrayIcon()
        self.icon = QIcon(icon)
        self.tray.setIcon(self.icon)
        self.tray.setVisible(True)
        menu = QMenu()
        with open('conf.yaml') as fh:
            read_data = yaml.load(fh, Loader=yaml.FullLoader)
        token = read_data.get('token', '')
        response = requests.get('http://server300:1080/api/v1/user?access_token={}'.format(token))
        if response.status_code == 200:
            user = json.loads(response.text)
            self.login = QAction(user["login"])
            menu.addAction(self.login)
            self.full_name = QAction(user['full_name'])
            menu.addAction(self.full_name)
        else:
            self.auth = QAction('Необходима авторизация через токен')
            menu.addAction(self.auth)
        self.settings = QAction("Настройки")
        setting = self.setting
        self.settings.triggered.connect(setting)
        menu.addAction(self.settings)
        self.quit = QAction("Завершить программу")
        self.quit.triggered.connect(app.quit)
        menu.addAction(self.quit)
        self.tray.setContextMenu(menu)

    def save_token(self):
        f = open('conf.yaml', 'w')
        f.write('token: ' + self.window.layout().itemAt(1).widget().text())
        f.close()
        self.__init__(self.icon, self.app)
        return

    def setting(self):
        self.window = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Вставьте ваш токен"))
        layout.addWidget(QLineEdit())
        save_token = self.save_token
        button = QPushButton("Сохранить токен")
        button.clicked.connect(save_token)
        layout.addWidget(button)
        self.window.setLayout(layout)
        self.window.show()
        screen_geometry = QApplication.desktop().availableGeometry()
        screen_size = (screen_geometry.width(), screen_geometry.height())
        window_size = (self.window.frameSize().width(), self.window.frameSize().height())
        x = screen_size[0] - window_size[0] - 50
        y = screen_size[1] - window_size[1] - 10
        self.window.move(x, y)

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
tray_icon = TrayIcon('icon.png', app)
app.exec_()