from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import sys
import yaml
import requests
import json


class Hint:

    def __init__(self, hint):
        self.window = QWidget()
        self.layout = QVBoxLayout()
        self.label_hint = QLabel(hint)
        self.layout.addWidget(self.label_hint)
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


class Setting:

    def __init__(self, tray_icon):
        self.tray_icon = tray_icon
        self.window = QWidget()
        self.layout = QVBoxLayout()
        self.label_token = QLabel("Вставьте ваш токен")
        self.layout.addWidget(self.label_token)
        self.edit_token = QLineEdit()
        self.edit_server = QLineEdit()
        self.layout.addWidget(self.edit_token)
        self.label_server = QLabel("Вставьте ваш сервер, если он не дефолтный")
        self.layout.addWidget(self.label_server)
        self.layout.addWidget(self.edit_server)
        self.button = QPushButton("Сохранить токен")
        save_token = self.save_setting
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

    def save_setting(self):
        with open('conf.yaml') as f_obj:
            read_data = yaml.load(f_obj, Loader=yaml.FullLoader)
        if read_data is None:
            token = ''
            server = "server300:1080"
        else:
            token = read_data.get("token", '')
            server = read_data.get("server", "server300:1080")
        if self.edit_token.text() != '':
            token = self.edit_token.text()
        if self.edit_server.text() != '':
            server = self.edit_server.text()
        to_yaml = {"token": token, "server": server}
        with open('conf.yaml', 'w') as f_obj:
            yaml.dump(to_yaml, f_obj)
        self.tray_icon.create_menu()
        self.window.hide()


class TrayIcon:

    def __init__(self, icon, app):
        self.app = app
        self.tray = QSystemTrayIcon()
        self.icon = QIcon(icon)
        self.tray.setIcon(self.icon)
        self.tray.setVisible(True)
        self.login = QAction()
        self.auth = QAction()
        self.quit = QAction()
        self.hint = ''
        self.create_menu()

    @staticmethod
    def download_icon(self, token):
        with open('conf.yaml') as f_obj:
            read_data = yaml.load(f_obj, Loader=yaml.FullLoader)
        server = read_data.get('server', 'server300:1080')
        try:
            response = requests.get("http://{}/api/v1/user?access_token={}".format(server, token))
        except requests.exceptions.ConnectionError:
            self.hint = Hint('Такой сервер не существуют, использован дефолтный')
            response = requests.get("http://{}/api/v1/user?access_token={}".format('server300:1080', token))
        resource = requests.get(json.loads(response.text)['avatar_url'])
        out = open("img/{}.jpg".format(str(json.loads(response.text)['id'])), "wb")
        out.write(resource.content)
        out.close()

    def set_icon(self, icon):
        self.icon = QIcon(icon)
        self.tray.setIcon(self.icon)

    def create_menu(self):
        menu = QMenu()
        try:
            with open('conf.yaml') as fh:
                read_data = yaml.load(fh, Loader=yaml.FullLoader)
        except IOError:
            open('conf.yaml', 'w')
        if read_data is None:
            token = ""
            server = "server300:1080"
        else:
            token = read_data.get("token", "")
            server = read_data.get("server", "server300:1080")
        try:
            response = requests.get("http://{}/api/v1/user?access_token={}".format(server, token))
        except requests.exceptions.ConnectionError:
            self.hint = Hint('Такой сервер не существуют, использован дефолтный')
            response = requests.get("http://{}/api/v1/user?access_token={}".format("server300:1080", token))
        if response.status_code == 200:
            user = json.loads(response.text)
            self.download_icon(token)
            self.set_icon("img/{}.jpg".format(str(user['id'])))
            logout = self.logout
            self.login = QAction('Выйти из {}({})'.format(user['full_name'], user["login"]))
            self.login.triggered.connect(logout)
            menu.addAction(self.login)
            self.tray.setToolTip("{}({})".format(user['full_name'], user["login"]))
        else:
            self.auth = QAction("Настройки")
            def_setting = self.create_settings_window
            self.auth.triggered.connect(def_setting)
            menu.addAction(self.auth)
            self.tray.setToolTip("Необходима авторизация через токен")
        self.quit = QAction("Завершить программу")
        self.quit.triggered.connect(self.app.quit)
        menu.addAction(self.quit)
        self.tray.setContextMenu(menu)

    def create_settings_window(self):
        self.setting = Setting(self)

    def logout(self):
        with open('conf.yaml', 'w') as f_obj:
            to_yaml = {'token': '', 'server': 'server300:1080'}
            yaml.dump(to_yaml, f_obj)
        self.set_icon('icon.png')
        self.create_menu()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    tray_icon = TrayIcon('icon.png', app)
    app.exec_()


if __name__ == '__main__':
    main()

