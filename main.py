import traceback

import PyQt5.QtSvg
from PyQt5 import Qt
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import sys
import yaml
import requests
import json
import os
import logging
import datetime
import webbrowser
import re
import threading
import UI.setting_ui as setting_ui
from PyQt5.QtWinExtras import QtWin


class Notification:
    def __init__(self, api, tray):
        self.tray = tray
        self.scroll = QScrollArea()
        self.scroll.setFixedSize(800, 800)
        self.scroll.setWindowTitle("Новые сообщения")
        self.window = QWidget()
        icon = QIcon('img/logo.svg')
        self.scroll.setWindowIcon(icon)
        self.layout = QVBoxLayout()
        self.layout.setGeometry(QtCore.QRect(10, 10, 0, 0))
        self.notification_ui = []
        self.api = api

    def get_additional_information(self, notifications):
        if not (notifications['subject']['latest_comment_url'] == ''):
            return json.loads(self.api.get_comment(
                re.search(r'comments/\d+', format(notifications['subject']['latest_comment_url']))[0].replace(
                    'comments/',
                    '')).text)
        else:
            repo = re.search(r'repos/.+/issues', notifications['subject']['url'])[0].replace('repos/', '').replace(
                '/issues', '')
            issues = re.search(r'/issues/.+', notifications['subject']['url'])[0].replace('/issues/', '')
            notification = json.loads(self.api.get_repos_issues(repo, issues).text)
            notification['body'] = 'новая задача'
            return notification

    def formatting_the_date(self, date):
        date = datetime.datetime.strptime(date['created_at'], '%Y-%m-%dT%H:%M:%SZ')
        timezone = str(datetime.datetime.now(datetime.timezone.utc).astimezone())
        timezone = int(timezone[len(timezone) - 5:len(timezone) - 3])
        date = date + datetime.timedelta(hours=timezone)
        return date.strftime('%H:%M %d-%m-%Y')

    def show_notifications(self, notifications):
        for i in range(len(notifications)):
            notification = self.get_additional_information(notifications[i])
            date = self.formatting_the_date(notification)
            tasks = notifications[i]['subject']['title']
            if len(tasks) > 11:
                tasks = "{}...".format(tasks[0:11])
            repo = " {}, задача #{} - {}".format(notifications[i]['repository']['full_name'],
                                                 re.search(r'issues/\d+', notifications[i]['subject']['url'])[0].replace(
                                                     'issues/', ''), str(tasks))
            label = QLabel(
                'Пользователь: {}, репозиторий: {}, время создания: {}.'.format(notification['user']['login'], repo,
                                                                                date))
            label.setStyleSheet("font-size:12px;")
            self.layout.addWidget(label)
            self.notification_ui.append(label)
            plain_text = QPlainTextEdit('Сообщение: {}.'.format(notification['body']))
            plain_text.setReadOnly(True)
            plain_text.setFixedSize(750, 75)
            self.layout.addWidget(plain_text)
            self.notification_ui.append(plain_text)
            open_notification = self.open_notification(notifications[i]['subject']['url'].replace('api/v1/repos/', ''))
            button = QPushButton("Перейти в - {}/issues/{} ".format(notifications[i]['repository']['full_name'],
                                                                    re.search(r'issues/\d+', notifications[i]['subject']['url'])[
                                                                        0].replace('issues/', '')))
            button.setStyleSheet(
                "font-size:12px; color: #23619e; background: rgba(255,255,255,0); border-radius: .28571429rem; height: 20px; border-color: #dedede; text-align:right;")
            button.clicked.connect(open_notification)
            self.layout.addWidget(button)
            self.notification_ui.append(button)

    def create_window_notification(self, notifications):
        self.notification_ui = []
        self.layout = QVBoxLayout()
        self.window = QWidget()
        layout = QHBoxLayout()
        label = QLabel("Не прочитано - {} сообщений.".format(len(notifications)))
        label.setStyleSheet("font-size:24px;")
        layout.addWidget(label)
        button = QPushButton("Обновить")
        button.setStyleSheet("max-width:75px; min-width:75px;")
        button.clicked.connect(self.update)
        layout.addWidget(button)
        self.layout.addLayout(layout)
        self.notification_ui.append(label)
        self.show_notifications(notifications)
        self.layout.addStretch()
        self.window.setLayout(self.layout)
        self.scroll.setWidget(self.window)
        self.scroll.show()
        screen_geometry = QApplication.desktop().availableGeometry()
        screen_size = (screen_geometry.width(), screen_geometry.height())
        window_size = (self.scroll.frameSize().width(), self.scroll.frameSize().height())
        self.scroll.move(int(screen_size[0] / 2) - int(window_size[0] / 2),
                         int(screen_size[1] / 2) - int(window_size[1] / 2) - 20)

    def update(self):
        self.create_window_notification(self.tray.get_notifications())

    def open_notification(self, url):
        logging.debug("Переход по ссылке - {}".format(url))
        return lambda: webbrowser.open_new(url)


class Api:

    def __init__(self, server, access_token):
        logging.debug("Создание экземляра класса - Api.")
        self.server = server
        self.access_token = access_token

    def get_notifications(self):
        logging.debug("Получение всех новых оповещений для пользователя.")
        return requests.get("http://{}/api/v1/notifications?access_token={}".format(self.server, self.access_token))

    def get_issues(self):
        logging.debug("Получение задач.")
        return requests.get('http://{}/api/v1/repos/issues/search?access_token={}'.format(self.server, self.access_token))

    def get_repos_issues(self, repo, issues):
        logging.debug("Получение информации о задачи в репозитории.")
        return requests.get("http://{}/api/v1/repos/{}/issues/{}".format(self.server, repo, issues))

    def get_comment(self, comment):
        logging.debug("Получение  комментария")
        return requests.get("http://{}/api/v1/repos/VolodinMA/MyGitRepository/issues/comments/{}".format(self.server, comment))

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
            to_yaml = {"server": '', "token": '', "delay_notification": "45"}
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


class Setting(QtWidgets.QMainWindow, setting_ui.Ui_MainWindow):

    def __init__(self, tray_icon):
        self.tray_icon = tray_icon
        super().__init__()
        self.setupUi(self)
        self.setFixedSize(self.width(), self.height())
        renderer = PyQt5.QtSvg.QSvgWidget("img/logo.svg", self.centralwidget)
        renderer.setGeometry(self.label_4.geometry())
        renderer.show()
        self.setWindowFlags(QtCore.Qt.CustomizeWindowHint)
        self.pushButton.clicked.connect(self.save_settings)
        self.pushButton_2.clicked.connect(self.hide)
        read_data = self.tray_icon.config.get_settings()
        self.edit_token = self.textEdit
        self.edit_server = self.textEdit_2
        self.edit_delay_notification = self.textEdit_3
        self.edit_token.setText(read_data.get('token', ''))
        self.edit_server.setText(read_data.get('server', ''))
        self.edit_delay_notification.setText(read_data.get('delay_notification', ''))

    def my_show(self):
        logging.debug("Показ окна настроек.")
        self.show()
        screen_geometry = QApplication.desktop().availableGeometry()
        screen_size = (screen_geometry.width(), screen_geometry.height())
        window_size = (self.frameSize().width(), self.frameSize().height())
        x = screen_size[0] - window_size[0] - 50
        y = screen_size[1] - window_size[1] - 10
        self.move(x, y)

    def save_settings(self):
        logging.debug("Передача новых настроек в конфигурационный файл.")
        to_yaml = self.tray_icon.config.get_settings()
        to_yaml['token'] = self.edit_token.toPlainText()
        self.tray_icon.api.set_access_token(to_yaml['token'])
        to_yaml['server'] = self.edit_server.toPlainText()
        if not(self.edit_delay_notification.toPlainText().isdigit()):
            self.edit_delay_notification.setText('45')
        if float(self.edit_delay_notification.toPlainText()) > 0:
            to_yaml['delay_notification'] = self.edit_delay_notification.toPlainText()
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
        self.hide()


class TrayIcon:

    def __init__(self, icon, app):
        logging.debug("Создание экземпляра класса - TrayIcon")
        self.app = app
        self.tray = QSystemTrayIcon()
        self.window_notification = ''
        self.tray.authorization = False
        self.tray.activated.connect(self.controller_tray_icon)
        self.name_icon = icon
        self.menu_items = []
        self.icon = QIcon(icon)
        self.tray.setIcon(self.icon)
        self.tray.setVisible(True)
        self.menu = QMenu()
        self.hint = ''
        self.setting = ''
        self.notifications = []
        self.timer_constructor_menu = threading.Timer(3, self.constructor_menu)
        self.config = Config('conf.yaml')
        read_data = self.config.get_settings()
        self.api = Api(read_data.get('server', ''), read_data.get('token', ''))
        self.timer_animation = QtCore.QTimer()
        self.timer_animation.timeout.connect(self.animation)
        self.timer_subscribe_notifications = QtCore.QTimer()
        self.timer_subscribe_notifications.timeout.connect(self.subscribe_notification)
        self.constructor_menu()

    def subscribe_notification(self):
        logging.debug("Проверка новых сообщений")
        response = self.api.get_user()
        if response is None:
            logging.debug("Закончить проверку новых сообщений")
            exit()
        response = self.api.get_notifications()
        self.notifications = json.loads(response.text)
        if len(self.notifications) != 0 and not(self.timer_animation.isActive()):
            self.constructor_menu()
            self.timer_animation.start(2000)

    def download_icon(self):
        logging.debug("Скачивание изображения из интернета.")
        response = self.api.get_user()
        resource = requests.get(json.loads(response.text)['avatar_url'])
        if not(os.path.exists('img')):
            os.mkdir('img')
        with open("img/{}.jpg".format(str(json.loads(response.text)['id'])), "wb") as out:
            out.write(resource.content)

    def get_notifications(self):
        return self.notifications

    def animation(self):
        response = self.api.get_user()
        user = json.loads(response.text)
        if len(self.notifications) == 0:
            logging.debug("Закончить анимацию, оповещения о новых сообщениях")
            self.set_icon("img/{}.jpg".format(str(user['id'])))
            return
        if self.name_icon == "img/notification.png" and response.status_code == 200:
            self.set_icon("img/{}.jpg".format(str(user['id'])))
        else:
            self.set_icon('img/notification.png')

    def show_notification(self):
        if len(self.notifications) == 0:
            self.tray.setToolTip('Новых сообщений нет')
        else:
            self.window_notification = Notification(self.api, self)
            self.window_notification.create_window_notification(self.notifications)

    def controller_tray_icon(self, trigger):
        if trigger == 3 and self.tray.authorization:  # Левая кнопка мыши
            self.show_notification()
        if trigger == 1:  # Правая кнопка мыши
            self.tray.show()

    def set_icon(self, icon):
        logging.debug("Установление изображение для TrayIcon.")
        self.name_icon = icon
        self.icon = QIcon(icon)
        self.tray.setIcon(self.icon)

    def authentication_successful(self, response):
        self.tray.authorization = True
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
        self.tray.setToolTip("{}({})".format(user['full_name'], user["login"]))
        with open('conf.yaml') as f_obj:
            read_data = yaml.load(f_obj, Loader=yaml.FullLoader)
        if not(str(read_data.get('delay_notification', '')).isdigit()):
            self.config.save_settings({'delay_notification': '45'})
            with open('conf.yaml') as f_obj:
                read_data = yaml.load(f_obj, Loader=yaml.FullLoader)
        if float(read_data.get('delay_notification', '')) < 0.001:
            self.config.save_settings({'delay_notification': '45'})
        if not(self.timer_subscribe_notifications.isActive()):
            self.timer_subscribe_notifications.start(int(float(read_data.get('delay_notification', '45')) * 1000))

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
        self.setting.my_show()

    def logout(self):
        logging.info("TrayIcon: Выход из учетной записи")
        to_yaml = self.config.get_settings()
        self.timer_animation.stop()
        self.timer_subscribe_notifications.stop()
        to_yaml['token'] = ''
        self.data = []
        self.tray.authorization = False
        self.api.set_access_token(to_yaml['token'])
        self.config.save_settings(to_yaml)
        self.set_icon('img/icon.png')
        self.constructor_menu()


def crash_script(error_type, value, tb):
    list_tb = str(traceback.extract_tb(tb)).split('>, ')
    critical_error = "Название ошибки - {}, значение - {},".format(error_type, value)
    indent_format = 22
    critical_error += "\n {} tb - {}".format(" " * indent_format, list_tb[0] + ">, ")
    for i in range(1, len(list_tb)):
        critical_error += "\n {} {}".format(" " * indent_format, list_tb[i])
    logging.critical(critical_error)
    sys.__excepthook__(error_type, value, tb)


def main():
    myappid = 'myproduct'
    QtWin.setCurrentProcessExplicitAppUserModelID(myappid)
    sys.excepthook = crash_script
    if not (os.path.exists('logs')):
        os.mkdir('logs')
    current_date = datetime.datetime.today().strftime('%d-%m-%Y')
    format_logging = '%(asctime)s   %(levelname)-10s   %(message)s'
    logging.basicConfig(filename="logs/Debug-{}.log".format(current_date), level=logging.DEBUG, format=format_logging, datefmt='%H:%M:%S')
    logging.info("Запуск программы")
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('./img/logo.svg'))
    app.setQuitOnLastWindowClosed(False)
    tray_icon = TrayIcon('img/icon.png', app)
    app.exec_()


if __name__ == '__main__':
    main()
