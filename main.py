from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import sys
import yaml
import requests
import json
import os
import logging
import datetime


class Api:
    def __init__(self, server, access_token):
        self.server = server
        self.access_token = access_token

    def get_user(self):
        try:
            response = requests.get("http://{}/api/v1/user?access_token={}".format(self.server, self.access_token))
            return response
        except requests.exceptions.ConnectionError:
            logging.error('Введен не существующий сервер" {}'.format(self.server))
            msg = QMessageBox()
            msg.setText('Этот сервер не работает, использован сервер, по-умолчанию')
            msg.exec()

    def set_access_token(self, access_token):
        self.access_token = access_token

    def set_server(self, server):
        self.server = server


class Config:

    def __init__(self, name):
        self.name = name
        if not (os.path.exists(name)):
            to_yaml = {"server": '', "token": '', "default_server": "server300:1080"}
            with open(name, 'w') as f_obj:
                yaml.dump(to_yaml, f_obj)

    def save_settings(self, dict_setting):
        with open(self.name) as f_obj:
            to_yaml = yaml.load(f_obj, Loader=yaml.FullLoader)
        for key, value in dict_setting.items():
            to_yaml[key] = value
        with open(self.name, 'w') as f_obj:
            yaml.dump(to_yaml, f_obj)

    def get_settings(self):
        with open(self.name) as f_obj:
            read_data = yaml.load(f_obj, Loader=yaml.FullLoader)
        return read_data


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
        save_token = self.save_settings
        self.button.clicked.connect(save_token)
        self.layout.addWidget(self.button)
        self.button_close = QPushButton("Отмена")
        close_app = self.window.hide
        self.button_close.clicked.connect(close_app)
        self.layout.addWidget(self.button_close)
        self.window.setLayout(self.layout)
        read_data = self.tray_icon.config.get_settings()
        self.edit_token.setText(read_data['token'])
        self.edit_server.setText(read_data['server'])
        self.show()

    def show(self):
        self.window.show()
        screen_geometry = QApplication.desktop().availableGeometry()
        screen_size = (screen_geometry.width(), screen_geometry.height())
        window_size = (self.window.frameSize().width(), self.window.frameSize().height())
        x = screen_size[0] - window_size[0] - 50
        y = screen_size[1] - window_size[1] - 10
        self.window.move(x, y)

    def save_settings(self):
        to_yaml = self.tray_icon.config.get_settings()
        to_yaml['token'] = self.edit_token.text()
        self.tray_icon.api.set_access_token(to_yaml['token'])
        to_yaml['server'] = self.edit_server.text()
        self.tray_icon.api.set_server(to_yaml['server'])
        self.tray_icon.config.save_settings(to_yaml)
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
        self.config = Config('conf.yaml')
        read_data = self.config.get_settings()
        self.api = Api(read_data['server'], read_data['token'])
        self.create_menu()

    def download_icon(self):
        response = self.api.get_user()
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
        response = self.api.get_user()
        if response.status_code == 200:
            user = json.loads(response.text)
            self.name_user = QAction("{}({})".format(user['full_name'], user["login"]))
            self.name_user.setEnabled(False)
            menu.addAction(self.name_user)
            self.download_icon()
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
        to_yaml = self.config.get_settings()
        to_yaml['token'] = ''
        self.api.set_access_token(to_yaml['token'])
        self.config.save_settings(to_yaml)
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
