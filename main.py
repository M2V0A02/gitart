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
        logging.debug("   {}   Создание экземляра класса - Api.".format(datetime.datetime.now().strftime('%H:%M:%S')))
        self.server = server
        self.access_token = access_token

    def get_user(self):
        try:
            logging.debug("   {}   Обращение к Api для получение информацию о своей учетной записи.".format(datetime.datetime.now().strftime('%H:%M:%S')))
            response = requests.get("http://{}/api/v1/user?access_token={}".format(self.server, self.access_token))
            return response
        except requests.exceptions.ConnectionError:
            logging.error('{}Соединение не установленно имя сервера - {}'.format(datetime.datetime.now().strftime('%H:%M:%S'), self.server))
            msg = QMessageBox()
            msg.setText('Соединение с сервером, не установлено.')
            msg.exec()

    def set_access_token(self, access_token):
        logging.debug("   {}   Api: Перезапись токена доступа.".format(datetime.datetime.now().strftime('%H:%M:%S')))
        self.access_token = access_token

    def set_server(self, server):
        logging.debug("   {}   Api: Перезапись адреса сервера.".format(datetime.datetime.now().strftime('%H:%M:%S')))
        self.server = server


class Config:

    def __init__(self, name):
        logging.debug("   {}   Создание экземпляра класса - конфиг.".format(datetime.datetime.now().strftime('%H:%M:%S')))
        self.name = name
        if not (os.path.exists(name)):
            to_yaml = {"server": 'server300:1080', "token": ''}
            with open(name, 'w') as f_obj:
                yaml.dump(to_yaml, f_obj)

    def save_settings(self, dict_setting):
        logging.debug("   {}   Перезапись  настроек в конфигурационном файле.".format(datetime.datetime.now().strftime('%H:%M:%S')))
        with open(self.name) as f_obj:
            to_yaml = yaml.load(f_obj, Loader=yaml.FullLoader)
        for key, value in dict_setting.items():
            to_yaml[key] = value
        with open(self.name, 'w') as f_obj:
            yaml.dump(to_yaml, f_obj)

    def get_settings(self):
        logging.debug("   {}   Получение данных из конфигурационого файла.".format(datetime.datetime.now().strftime('%H:%M:%S')))
        with open(self.name) as f_obj:
            read_data = yaml.load(f_obj, Loader=yaml.FullLoader)
        return read_data


class Setting:

    def __init__(self, tray_icon):
        logging.debug("   {}   Создание экземляра класса Setting.".format(datetime.datetime.now().strftime('%H:%M:%S')))
        self.tray_icon = tray_icon
        self.window = QWidget()
        self.layout = QVBoxLayout()
        self.label_token = QLabel("Укажите ваш токен")
        self.layout.addWidget(self.label_token)
        self.edit_token = QLineEdit()
        self.edit_server = QLineEdit()
        self.layout.addWidget(self.edit_token)
        self.label_server = QLabel("Укажите сервер, если он отличается от сервера по-умолчанию")
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
        logging.debug("   {}   Setting: Показ окна настроек.".format(datetime.datetime.now().strftime('%H:%M:%S')))
        self.window.show()
        screen_geometry = QApplication.desktop().availableGeometry()
        screen_size = (screen_geometry.width(), screen_geometry.height())
        window_size = (self.window.frameSize().width(), self.window.frameSize().height())
        x = screen_size[0] - window_size[0] - 50
        y = screen_size[1] - window_size[1] - 10
        self.window.move(x, y)

    def save_settings(self):
        logging.debug("   {}   Setting: Передача новых настроек в конфигурационный файл.".format(datetime.datetime.now().strftime('%H:%M:%S')))
        to_yaml = self.tray_icon.config.get_settings()
        to_yaml['token'] = self.edit_token.text()
        self.tray_icon.api.set_access_token(to_yaml['token'])
        to_yaml['server'] = self.edit_server.text()
        self.tray_icon.api.set_server(to_yaml['server'])
        if self.tray_icon.api.get_user() is None:
            logging.debug("   {}   response - пустой в save_settings".format(datetime.datetime.now().strftime('%H:%M:%S')))
        else:
            if not(self.tray_icon.api.get_user().status_code == 200):
                msg = QMessageBox()
                msg.setText('Авторизация не удалась')
                msg.exec()
        self.tray_icon.config.save_settings(to_yaml)
        self.tray_icon.constructor_menu()
        self.window.hide()


class TrayIcon:

    def __init__(self, icon, app):
        logging.debug("   {}   Создание экземпляра класса - TrayIcon".format(datetime.datetime.now().strftime('%H:%M:%S')))
        self.app = app
        self.tray = QSystemTrayIcon()
        self.icon = QIcon(icon)
        self.tray.setIcon(self.icon)
        self.tray.setVisible(True)
        self.login = QAction()
        self.auth = QAction()
        self.quit = QAction()
        self.name_user = QAction()
        self.menu = QMenu()
        self.hint = ''
        self.setting = ''
        self.config = Config('conf.yaml')
        read_data = self.config.get_settings()
        self.api = Api(read_data['server'], read_data['token'])
        self.constructor_menu()

    def download_icon(self):
        logging.debug("   {}   TrayIcon: Скачивание изображения из интернета.".format(datetime.datetime.now().strftime('%H:%M:%S')))
        response = self.api.get_user()
        resource = requests.get(json.loads(response.text)['avatar_url'])
        if not(os.path.exists('img')):
            os.mkdir('img')
        with open("img/{}.jpg".format(str(json.loads(response.text)['id'])), "wb") as out:
            out.write(resource.content)

    def set_icon(self, icon):
        logging.debug("   {}   Установление изображение для TrayIcon.".format(datetime.datetime.now().strftime('%H:%M:%S')))
        self.icon = QIcon(icon)
        self.tray.setIcon(self.icon)

    def authentication_successful(self, response):
        logging.debug("   {}   TrayIcon: Токен доступа действителен.".format(datetime.datetime.now().strftime('%H:%M:%S')))
        user = json.loads(response.text)
        self.name_user = QAction("{}({})".format(user['full_name'], user["login"]))
        self.name_user.setEnabled(False)
        self.menu.addAction(self.name_user)
        self.download_icon()
        self.set_icon("img/{}.jpg".format(str(user['id'])))
        logout = self.logout
        self.login = QAction('Выйти из {}'.format(user["login"]))
        self.login.triggered.connect(logout)
        self.menu.addAction(self.login)
        self.tray.setToolTip("{}({})".format(user['full_name'], user["login"]))

    def constructor_menu(self):
        logging.debug("   {}   TrayIcon: Создание контекстного меню для TrayIcon.".format(datetime.datetime.now().strftime('%H:%M:%S')))
        self.menu = QMenu()
        response = self.api.get_user()
        if response is None:
            logging.debug("   {}   response - пустой".format(datetime.datetime.now().strftime('%H:%M:%S')))
        else:
            if response.status_code == 200:
                self.authentication_successful(response)
            else:
                logging.debug("   {}   TrayIcon: Токена доступа нет или он недействителен.".format(datetime.datetime.now().strftime('%H:%M:%S')))
                self.tray.setToolTip("Необходима авторизация через токен")
        self.auth = QAction("Настройки")
        def_setting = self.create_settings_window
        self.auth.triggered.connect(def_setting)
        self.menu.addAction(self.auth)
        self.quit = QAction("Завершить программу")
        self.quit.triggered.connect(self.app.quit)
        self.menu.addAction(self.quit)
        self.tray.setContextMenu(self.menu)

    def create_settings_window(self):
        logging.debug("   {}   TrayIcon: Показ окна настроек".format(datetime.datetime.now().strftime('%H:%M:%S')))
        self.setting = Setting(self)

    def logout(self):
        logging.info("    {}   TrayIcon: Выход из учетной записи".format(datetime.datetime.now().strftime('%H:%M:%S')))
        to_yaml = self.config.get_settings()
        to_yaml['token'] = ''
        self.api.set_access_token(to_yaml['token'])
        self.config.save_settings(to_yaml)
        self.set_icon('img/icon.png')
        self.constructor_menu()


def crash_script(exctype, value, tb):
    logging.critical(" {}   Название ошибки - {}, значение - {}, tb - {}".format(datetime.datetime.now().strftime('%H:%M:%S'), exctype, value, tb))


def main():
    sys.excepthook = crash_script
    if not (os.path.exists('logs')):
        os.mkdir('logs')
    current_date = datetime.datetime.today().strftime('%d-%m-%Y')
    logging.basicConfig(filename="logs/Debug-{}.log".format(current_date), level=logging.DEBUG)
    logging.info("    {}   Запуск программы".format(datetime.datetime.now().strftime('%H:%M:%S')))
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    tray_icon = TrayIcon('img/icon.png', app)
    app.exec_()


if __name__ == '__main__':
    main()
