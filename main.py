from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import sys
import yaml
import requests
import json


class Setting:

    def __init__(self, tray_icon):
        self.tray_icon = tray_icon
        self.window = QWidget()
        self.layout = QVBoxLayout()
        self.label = QLabel("Вставьте ваш токен")
        self.layout.addWidget(self.label)
        self.edit = QLineEdit()
        self.layout.addWidget(self.edit)
        self.button = QPushButton("Сохранить токен")
        save_token = self.save_token
        self.button.clicked.connect(save_token)
        self.layout.addWidget(self.button)
        self.window.setLayout(self.layout)
        self.show()

    def show(self):
        self.window.show()
        screen_geometry = QApplication.desktop().availableGeometry()
        screen_size = (screen_geometry.width(), screen_geometry.height())
        window_size = (self.window.frameSize().width(), self.window.frameSize().height())
        x = screen_size[0] - window_size[0] - 50
        y = screen_size[1] - window_size[1] - 10
        self.window.move(x, y)

    def save_token(self):
        f = open('conf.yaml', 'w')
        f.write('token: ' + self.edit.text())
        f.close()
        self.tray_icon.create_menu()
        self.window.hide()


class TrayIcon:

    def __init__(self, icon, app):
        self.app = app
        self.tray = QSystemTrayIcon()
        self.icon = QIcon(icon)
        self.tray.setIcon(self.icon)
        self.tray.setVisible(True)
        self.create_menu()

    def create_menu(self):
        menu = QMenu()
        try:
            with open('conf.yaml') as fh:
                read_data = yaml.load(fh, Loader=yaml.FullLoader)
        except:
            open('conf.yaml', 'w')
        try:
            token = read_data.get("token", "")
        except:
            token = ""
        response = requests.get("http://server300:1080/api/v1/user?access_token={}".format(token))
        if response.status_code == 200:
            user = json.loads(response.text)
            self.login = QAction(user['full_name'] + "(" + user["login"] + ")")
            menu.addAction(self.login)
            self.tray.setToolTip(user['full_name'] + "(" + user["login"] + ")")
        else:
            self.auth = QAction("Необходима авторизация через токен")
            menu.addAction(self.auth)
            self.tray.setToolTip("Необходима авторизация через токен")
        self.settings = QAction("Настройки")
        setting = self.setting
        self.settings.triggered.connect(setting)
        menu.addAction(self.settings)
        self.quit = QAction("Завершить программу")
        self.quit.triggered.connect(self.app.quit)
        menu.addAction(self.quit)
        self.tray.setContextMenu(menu)

    def setting(self):
        self.win_setting = Setting(self)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    tray_icon = TrayIcon('icon.png', app)
    app.exec_()


if __name__ == '__main__':
    main()

