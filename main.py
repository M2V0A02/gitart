from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import sys
import yaml
import requests
import json
import os
import logging
import datetime


class Hint:

    def __init__(self, hint):
        self.window = QWidget()
        self.layout = QVBoxLayout()
        self.label_hint = QLabel(hint)
        self.layout.addWidget(self.label_hint)
        self.window.setLayout(self.layout)
        logging.info(hint)
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
        self.label_token = QLabel("Укажите ваш токен")
        self.layout.addWidget(self.label_token)
        self.edit_token = QLineEdit()
        self.edit_server = QLineEdit()
        self.layout.addWidget(self.edit_token)
        self.label_server = QLabel("Укажите сервер, если он отличается от сервера, по-умолчанию")
        self.layout.addWidget(self.label_server)
        self.layout.addWidget(self.edit_server)
        self.button = QPushButton("Сохранить настройки")
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
            to_yaml = yaml.load(f_obj, Loader=yaml.FullLoader)
        if self.edit_token.text() != '':
            to_yaml['token'] = self.edit_token.text()
        if self.edit_server.text() != '':
            to_yaml['server'] = self.edit_server.text()
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
        self.name_user = QAction()
        self.hint = ''
        self.setting = ''
        if not(os.path.exists('conf.yaml')):
            self.initiation_config()
        self.create_menu()

    def initiation_config(self):
        to_yaml = {"server": '', "token": '', "default_server": "server300:1080"}
        with open('conf.yaml', 'w') as f_obj:
            yaml.dump(to_yaml, f_obj)

    def download_icon(self, token):
        with open('conf.yaml') as f_obj:
            read_data = yaml.load(f_obj, Loader=yaml.FullLoader)
        server = read_data.get('server', '')
        if server == '':
            server = read_data.get('default_server', '')
        try:
            response = requests.get("http://{}/api/v1/user?access_token={}".format(server, token))
        except requests.exceptions.ConnectionError:
            logging.error('Введен не существующий сервер" {}'.format(server))
            self.hint = Hint('Такой сервер не существуют, использован сервер, по-умолчанию')
            try:
                response = requests.get("http://{}/api/v1/user?access_token={}".format(read_data['default_server'], token))
            except requests.exceptions.ConnectionError:
                logging.error('Сервер по умолчанию удален, несуществует или недействительный')
                self.hint = Hint('сервер по-умолчанию не действителен')
                return
        resource = requests.get(json.loads(response.text)['avatar_url'])
        if not(os.path.exists('img')):
            os.mkdir('img')
        with open("img/{}.jpg".format(str(json.loads(response.text)['id'])), "wb") as out:
            out.write(resource.content)

    def set_icon(self, icon):
        self.icon = QIcon(icon)
        self.tray.setIcon(self.icon)

    def create_menu(self):
        menu = QMenu()
        with open('conf.yaml') as fh:
            read_data = yaml.load(fh, Loader=yaml.FullLoader)
        default_server = read_data.get("default_server", "")
        token = read_data.get("token", "")
        server = read_data.get("server", "")
        if server == "":
            server = default_server
        try:
            response = requests.get("http://{}/api/v1/user?access_token={}".format(server, token))
        except requests.exceptions.ConnectionError:
            logging.error('Введен не существующий сервер" {}'.format(server))
            self.hint = Hint('Такой сервер не существуют, использован сервер, по-умолчанию')
            try:
                response = requests.get(
                    "http://{}/api/v1/user?access_token={}".format(read_data['default_server'], token))
            except requests.exceptions.ConnectionError:
                logging.error('Сервер по умолчанию удален, несуществует или недействительный')
                self.hint = Hint('сервер, по-умолчанию не работает')
                return
        if response.status_code == 200:
            user = json.loads(response.text)
            self.name_user = QAction("{}({})".format(user['full_name'], user["login"]))
            self.name_user.setEnabled(False)
            menu.addAction(self.name_user)
            self.download_icon(token)
            self.set_icon("img/{}.jpg".format(str(user['id'])))
            logout = self.logout
            self.login = QAction('Выйти из {}'.format(user["login"]))
            self.login.triggered.connect(logout)
            menu.addAction(self.login)
            self.auth = QAction("Настройки")
            def_setting = self.create_settings_window
            self.auth.triggered.connect(def_setting)
            menu.addAction(self.auth)
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
        with open('conf.yaml') as f_obj:
            to_yaml = yaml.load(f_obj, Loader=yaml.FullLoader)
        with open('conf.yaml', 'w') as f_obj:
            to_yaml['token'] = ''
            yaml.dump(to_yaml, f_obj)
        self.set_icon('img/icon.png')
        self.create_menu()


def main():
    if not (os.path.exists('logs')):
        os.mkdir('logs')
    current_date = datetime.datetime.today().strftime('%d-%m-%Y')
    logging.basicConfig(filename="logs/{}.log".format(current_date), level=logging.INFO)
    logging.info("Запуск программы")
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    tray_icon = TrayIcon('img/icon.png', app)
    app.exec_()


if __name__ == '__main__':
    main()
