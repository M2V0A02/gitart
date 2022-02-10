import traceback
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import sys
import yaml
import requests
import json
import os
import logging
import datetime
import threading
import webbrowser


class Notification:
    def __init__(self, data):
        self.window = QWidget()
        self.layout = QVBoxLayout()
        self.notification = []
        if len(data) == 0:
            label = QLabel('Новых сообщений нет')
            self.layout.addWidget(label)
            self.notification.append(label)
        for i in range(len(data)):
            label = QLabel('Сообщение: {}.'.format(data[i]['subject']['title']))
            self.layout.addWidget(label)
            open_notification = self.open_notification(data[i]['subject']['url'].replace('api/v1/repos/', ''))
            button = QPushButton("Перейти в репозиторий - {}".format(data[i]['repository']['name']))
            button.clicked.connect(open_notification)
            self.layout.addWidget(button)
            self.notification.append(label)
            self.notification.append(button)
        self.window.setLayout(self.layout)
        self.window.show()

    def open_notification(self, url):
        logging.debug("Переход по ссылке - {}".format(url))
        def myfunc():
            webbrowser.open_new(url)
        return myfunc


class Api:

    def __init__(self, server, access_token):
        logging.debug("Создание экземляра класса - Api.")
        self.server = server
        self.access_token = access_token

    def get_notifications(self):
        logging.debug("Получение всех новых оповещений для пользователя.")
        return requests.get("http://{}/api/v1/notifications?access_token={}".format(self.server, self.access_token))

    def get_user(self):
        try:
            logging.debug("Обращение к Api для получение информацию о своей учетной записи.")
            response = requests.get("http://{}/api/v1/user?access_token={}".format(self.server, self.access_token))
            return response
        except requests.exceptions.ConnectionError:
            logging.error('Соединение не установленно имя сервера - {}')
            msg = QMessageBox()
            msg.setText('Соединение с сервером, не установлено.')
            msg.exec()
        except requests.exceptions.InvalidURL:
            logging.error('Server - пустой, url - {}'.format("http://{}/api/v1/user?access_token={}".format(self.server,self.access_token)))
            msg = QMessageBox()
            msg.setText('Server - пустой')
            msg.exec()

    def set_access_token(self, access_token):
        logging.debug("Перезапись токена доступа.")
        self.access_token = access_token

    def get_access_token(self):
        return self.access_token

    def get_server(self):
        return self.server

    def set_server(self, server):
        logging.debug("Перезапись адреса сервера.")
        self.server = server


class Config:

    def __init__(self, name):
        logging.debug("Создание экземпляра класса - конфиг.")
        self.name = name
        if not (os.path.exists(name)):
            to_yaml = {"server": '', "token": '', "delay_notification": "5"}
            with open(name, 'w') as f_obj:
                yaml.dump(to_yaml, f_obj)

    def save_settings(self, dict_setting):
        logging.debug("Перезапись  настроек в конфигурационном файле.")
        with open(self.name) as f_obj:
            to_yaml = yaml.load(f_obj, Loader=yaml.FullLoader)
        for key, value in dict_setting.items():
            to_yaml[key] = value
        with open(self.name, 'w') as f_obj:
            yaml.dump(to_yaml, f_obj)

    def get_settings(self):
        logging.debug("Получение данных из конфигурационого файла.")
        with open(self.name) as f_obj:
            read_data = yaml.load(f_obj, Loader=yaml.FullLoader)
        return read_data


class Setting:

    def __init__(self, tray_icon):
        logging.debug("Создание экземляра класса Setting.")
        self.tray_icon = tray_icon
        self.window = QWidget()
        self.layout = QVBoxLayout()
        self.label_token = QLabel("Укажите ваш токен")
        self.layout.addWidget(self.label_token)
        self.edit_token = QLineEdit()
        self.edit_server = QLineEdit()
        self.layout.addWidget(self.edit_token)
        self.label_server = QLabel("Укажите сервер")
        self.layout.addWidget(self.label_server)
        self.layout.addWidget(self.edit_server)
        self.label_delay_notification = QLabel("Укажите задержки между оповещениями.")
        self.layout.addWidget(self.label_delay_notification)
        self.edit_delay_notification = QLineEdit()
        self.layout.addWidget(self.edit_delay_notification)
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
        self.edit_delay_notification.setText(read_data['delay_notification'])
        self.show()

    def show(self):
        logging.debug("Показ окна настроек.")
        self.window.show()
        screen_geometry = QApplication.desktop().availableGeometry()
        screen_size = (screen_geometry.width(), screen_geometry.height())
        window_size = (self.window.frameSize().width(), self.window.frameSize().height())
        x = screen_size[0] - window_size[0] - 50
        y = screen_size[1] - window_size[1] - 10
        self.window.move(x, y)

    def save_settings(self):
        logging.debug("Передача новых настроек в конфигурационный файл.")
        to_yaml = self.tray_icon.config.get_settings()
        to_yaml['token'] = self.edit_token.text()
        self.tray_icon.api.set_access_token(to_yaml['token'])
        to_yaml['server'] = self.edit_server.text()
        if (self.edit_delay_notification.text().isdigit()) and int(self.edit_delay_notification.text()) > 0:
            to_yaml['delay_notification'] = self.edit_delay_notification.text()
        self.tray_icon.api.set_server(to_yaml['server'])
        if self.tray_icon.api.get_user() is None:
            logging.debug("response - пустой в save_settings")
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
        logging.debug("Создание экземпляра класса - TrayIcon")
        self.app = app
        self.tray = QSystemTrayIcon()
        self.name_icon = icon
        self.menu_items = []
        self.icon = QIcon(icon)
        self.tray.setIcon(self.icon)
        self.tray.setVisible(True)
        self.menu = QMenu()
        self.hint = ''
        self.setting = ''
        self.data = []
        self.config = Config('conf.yaml')
        read_data = self.config.get_settings()
        self.api = Api(read_data['server'], read_data['token'])
        self.timer_animation = threading.Timer(2.0, self.animation)
        self.timer_subscribe_notifications = threading.Timer(5.0, self.subscribe_notification)
        self.constructor_menu()

    def subscribe_notification(self):
        logging.debug("Проверка новых сообщений")
        response = self.api.get_user()
        if response is None:
            logging.debug("Закончить проверку новых сообщений")
            self.timer_subscribe_notifications.cancel()
            exit()
        response = self.api.get_notifications()
        self.data = json.loads(response.text)
        self.timer_animation = threading.Timer(2.0, self.animation)
        if len(self.data) != 0 and not(self.timer_animation.is_alive()):
            self.timer_animation.start()
        self.timer_subscribe_notifications.run()

    def download_icon(self):
        logging.debug("Скачивание изображения из интернета.")
        response = self.api.get_user()
        resource = requests.get(json.loads(response.text)['avatar_url'])
        if not(os.path.exists('img')):
            os.mkdir('img')
        with open("img/{}.jpg".format(str(json.loads(response.text)['id'])), "wb") as out:
            out.write(resource.content)

    def animation(self):
        if self.name_icon == "img/notification.png":
            response = self.api.get_user()
            user = json.loads(response.text)
            self.set_icon("img/{}.jpg".format(str(user['id'])))
        else:
            self.set_icon('img/notification.png')
        if len(self.data) == 0:
            logging.debug("Закончить анимацию, оповещения о новых сообщениях")
            response = self.api.get_user()
            user = json.loads(response.text)
            self.set_icon("img/{}.jpg".format(str(user['id'])))
            self.timer_animation.cancel()
        self.timer_animation.run()

    def show_notification(self):
        self.window_notification = Notification(self.data)

    def set_icon(self, icon):
        logging.debug("Установление изображение для TrayIcon.")
        self.name_icon = icon
        self.icon = QIcon(icon)
        self.tray.setIcon(self.icon)

    def authentication_successful(self, response):
        logging.debug("TrayIcon: Токен доступа действителен.")
        user = json.loads(response.text)
        name_user = QAction("{}({})".format(user['full_name'], user["login"]))
        name_user.setEnabled(False)
        self.menu.addAction(name_user)
        self.menu_items.append(name_user)
        self.download_icon()
        self.set_icon("img/{}.jpg".format(str(user['id'])))
        logout = self.logout
        login = QAction('Выйти из {}'.format(user["login"]))
        login.triggered.connect(logout)
        self.menu.addAction(login)
        self.menu_items.append(login)
        show_notification = self.show_notification
        notification = QAction('Новые сообщение')
        notification.triggered.connect(show_notification)
        self.menu_items.append(notification)
        self.menu.addAction(notification)
        self.tray.setToolTip("{}({})".format(user['full_name'], user["login"]))
        with open('conf.yaml') as f_obj:
            read_data = yaml.load(f_obj, Loader=yaml.FullLoader)
        self.timer_subscribe_notifications = threading.Timer(int(read_data['delay_notification']), self.subscribe_notification)
        if not(self.timer_subscribe_notifications.is_alive()):
            self.timer_subscribe_notifications.start()

    def constructor_menu(self):
        self.menu_items = []
        self.menu = QMenu()
        logging.debug("TrayIcon: Создание контекстного меню для TrayIcon.")
        response = self.api.get_user()
        if response is None:
            logging.debug("response - пустой")
        else:
            if response.status_code == 200:
                self.authentication_successful(response)
            else:
                logging.debug("TrayIcon: Токена доступа нет или он недействителен.")
                self.tray.setToolTip("Необходима авторизация через токен")
        auth = QAction("Настройки")
        def_setting = self.create_settings_window
        auth.triggered.connect(def_setting)
        self.menu.addAction(auth)
        self.menu_items.append(auth)
        quit_programm = QAction("Завершить программу")
        quit_programm.triggered.connect(self.app.quit)
        self.menu.addAction(quit_programm)
        self.menu_items.append(quit_programm)
        self.tray.setContextMenu(self.menu)

    def create_settings_window(self):
        logging.debug("TrayIcon: Показ окна настроек")
        self.setting = Setting(self)

    def logout(self):
        logging.info("TrayIcon: Выход из учетной записи")
        to_yaml = self.config.get_settings()
        to_yaml['token'] = ''
        self.api.set_access_token(to_yaml['token'])
        self.config.save_settings(to_yaml)
        self.set_icon('img/icon.png')
        self.constructor_menu()


def crash_script(error_type, value, tb):
    logging.critical("Название ошибки - {}, значение - {}, tb - {}".format(error_type, value, traceback.extract_tb(tb)))
    sys.__excepthook__(error_type, value, tb)


def main():
    sys.excepthook = crash_script
    if not (os.path.exists('logs')):
        os.mkdir('logs')
    current_date = datetime.datetime.today().strftime('%d-%m-%Y')
    format_logging = '%(asctime)s   %(levelname)-10s   %(message)s'
    logging.basicConfig(filename="logs/Debug-{}.log".format(current_date), level=logging.DEBUG, format=format_logging, datefmt='%H:%M:%S')
    logging.info("Запуск программы")
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    tray_icon = TrayIcon('img/icon.png', app)
    app.exec_()


if __name__ == '__main__':
    main()
