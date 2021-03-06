import time
import traceback
from PyQt5 import QtCore
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import sys
from PyQt5 import QtGui
import requests
import json
import os
import logging
import datetime
import webbrowser
import re
import UI.setting_ui as setting_ui
import UI.main_window_ui as main_window_ui
import my_sql_lite
from PyQt5.QtWinExtras import QtWin
from PyQt5.QtCore import QThread
from plyer.utils import platform
from plyer import notification


# Когда лог, больше несколько строк indent_format показывает сколько должно быть отступов у новой строки.
indent_format = 24


def show_message_in_tray(title, message, icon_path):
    logging.debug("Вывод сообщения в трей, title - {}, message - {}".format(title, message))
    notification.notify(
        title=title,
        message=message,
        app_name='Gitart',
        app_icon=icon_path
    )


def download_icon(url, name):
    logging.debug("Скачивание аватара пользователя. name - {}".format("img/{}.jpg".format(name)))
    resource = requests.get(url)
    if not (os.path.exists('img')):
        os.mkdir('img')
    with open("img/{}.jpg".format(name), 'wb') as out:
        out.write(resource.content)


def formatting_the_date(string_date):
    try:
        string_date = datetime.datetime.strptime(string_date, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return ''
    timezone = str(datetime.datetime.now(datetime.timezone.utc).astimezone())
    timezone = int(timezone[len(timezone) - 5:len(timezone) - 3])
    string_date = string_date + datetime.timedelta(hours=timezone)
    return string_date


def save_notifications(api, notifications, table):
    for notification in notifications:
        message = 'null'
        user_login = 'null'
        user_avatar_name = 'null'
        if not (notification['subject']['url'] == ''):
            repo = re.search(r'repos/.+/issues', notification['subject']['url'])[0]. \
                replace('repos/', '').replace('/issues', '')
            issues = re.search(r'/issues/.+', notification['subject']['url'])[0].replace('/issues/', '')
            try:
                try:
                    repo = json.loads(api.get_repos_issues(repo, issues).text)
                except AttributeError:
                    return
                user_login = "'{}'".format(repo['user']['login'])
                start = - 1
                for i in range(4):
                    start = repo['user']['avatar_url'].find("/", start + 1)
                user_avatar_name = "{}".format(repo['user']['avatar_url'][start:len(repo['user']['avatar_url'])])
                download_icon(repo['user']['avatar_url'], user_avatar_name)
                user_avatar_name = "'{}'".format(user_avatar_name)
            except (json.decoder.JSONDecodeError, AttributeError):
                user_login = 'null'
            if not (notification['subject']['latest_comment_url'] == ''):
                id_comments = re.search(r'comments/\d+', format(notification['subject']
                                                                ['latest_comment_url']))[0].replace('comments/', '')
                try:
                    message = "'{}'".format(json.loads(api.get_comment(repo['repository']['name'],
                                                                       repo['repository']['owner'],
                                                                       id_comments).text)['body'])
                except (json.decoder.JSONDecodeError, AttributeError, KeyError):
                    message = 'null'
        id_notification = "'{}'".format(notification['id'])
        full_name = "'{}'".format(notification.get('repository', {}).get('full_name', 'null'))
        created_time = "'{}'".format(formatting_the_date(notification.get('updated_at', 'null')))
        url = "'{}'".format(notification.get('subject', {}).get('url', 'null'))
        state = "'{}'".format(notification['subject']['state'])
        title = "'{}'".format(notification['subject']['title'])
        table.save(id_notification, message, user_login, full_name, created_time, url, user_avatar_name, state, title)


def get_assigned_tasks(assigned_to_you_tasks):
    assigned_tasks = []
    for assigned_to_you_task in assigned_to_you_tasks:
        title = assigned_to_you_task['title']
        task_id = assigned_to_you_task['id']
        full_name = assigned_to_you_task['repository']['full_name']
        created_time = formatting_the_date(assigned_to_you_task['created_at']).strftime('%d-%m-%Y')
        creator = assigned_to_you_task['user']['login']
        url = assigned_to_you_task['html_url']
        milestone_title = ""
        if not (assigned_to_you_task['milestone'] is None):
            milestone_title = assigned_to_you_task['milestone']['title']
        assigned_tasks.append({'id': task_id, 'title': title, 'created_at': created_time,
                               'full_name': full_name, 'creator': creator, 'url': url,
                               'milestone_title': milestone_title})
    return assigned_tasks


def update_user(api):
    try:
        user_json = json.loads(api.get_user().text)
    except AttributeError:
        user_json = {}
    full_name = "'{}'".format(user_json.get('full_name', 'NULL'))
    login = "'{}'".format(user_json.get('login', 'NULL'))
    avatar_url = "'{}'".format(user_json.get('avatar_url', 'NULL'))
    data_base.update_user({'full_name': full_name, 'login': login, 'avatar_url': avatar_url})


def crash_script(error_type, value, tb):
    traces = traceback.extract_tb(tb)
    critical_error = '{}: {},  \n'.format(error_type, value)
    for frame_summary in traces:
        critical_error += "{:24}File '{}', line {}, in {}, \n{:24} {} \n".format('', frame_summary.filename,
                                                                                 frame_summary.lineno,
                                                                                 frame_summary.name, '',
                                                                                 frame_summary.line)
    logging.critical(critical_error)
    sys.__excepthook__(error_type, value, tb)


def get_ending_by_number(number, possible_endings):
    if number == 1:
        return possible_endings[0]
    elif 1 < number < 5:
        return possible_endings[1]
    else:
        return possible_endings[2]


class DataBase(QThread):
    def __init__(self, parent=None):
        super(DataBase, self).__init__(parent)
        self.table_notifications = my_sql_lite.Notifications()
        self.last_notifications = self.table_notifications.get_all()
        self.notifications = []
        self.assigned_tasks = []
        self.table_assigned_tasks = my_sql_lite.AssignedTasks()
        self.last_assigned_tasks = self.table_assigned_tasks.get_all()
        self.table_users = my_sql_lite.Users()
        self.last_user = self.table_users.get()
        self.api = Api(self.last_user['server'], self.last_user['token'])
        self.authorisation = False

    def run(self):
        while True:
            if self.authorisation:
                try:
                    if not json.loads(self.api.get_notifications().text) == self.notifications:
                        self.notifications = json.loads(self.api.get_notifications().text)
                        self.table_notifications.clear()
                        save_notifications(self.api, json.loads(self.api.get_notifications().text),
                                           self.table_notifications)
                        self.last_notifications = self.table_notifications.get_all()
                except AttributeError:
                    pass
                try:
                    assigned_tasks = get_assigned_tasks(json.loads(self.api.get_issues().text))
                except AttributeError:
                    assigned_tasks = None
                if not (assigned_tasks == self.last_assigned_tasks or assigned_tasks is None):

                    self.assigned_tasks = assigned_tasks
                    for assigned_task in assigned_tasks:
                        if_exist = False
                        for last_assigned_task in self.last_assigned_tasks:
                            if assigned_task['id'] == last_assigned_task['id']:
                                if_exist = True
                                break
                        if not if_exist:
                            show_message_in_tray("Новая назначенная задача от {}".format(assigned_task['creator']),
                                                 assigned_task['title'],
                                                 'img/logo.ico')
                            self.table_assigned_tasks.save(assigned_task['id'],
                                                           "'{}'".format(assigned_task['title']),
                                                           "'{}'".format(assigned_task['created_at']),
                                                           "'{}'".format(assigned_task['full_name']),
                                                           "'{}'".format(assigned_task['creator']),
                                                           "'{}'".format(assigned_task['url']),
                                                           "'{}'".format(assigned_task['milestone_title']))
                        for last_assigned_task in self.last_assigned_tasks:
                            if_exist = False
                            for assigned_task in assigned_tasks:
                                if assigned_task['id'] == last_assigned_task['id']:
                                    if_exist = True
                                    break
                            if not if_exist:
                                self.table_assigned_tasks.delete_by_id(last_assigned_task['id'])
                    self.last_assigned_tasks = self.table_assigned_tasks.get_all()
                time.sleep(5)

    def get_notifications(self):
        return self.last_notifications

    def get_assigned_tasks(self):
        return self.last_assigned_tasks

    def get_user(self):
        return self.last_user

    def update_user(self, data_user):
        self.table_users.update(data_user)
        self.last_user = self.table_users.get()
        self.api.update_access_token(data_base.get_user()['token'])
        self.api.update_server(data_base.get_user()['server'])

    def get_user_data_from_api(self):
        update_user(self.api)

    def set_authorisation(self, authorisation):
        self.authorisation = authorisation

    def get_there_connection(self):
        return self.api.there_connection


class MainWindowTasks(QMainWindow, main_window_ui.Ui_MainWindow):

    def __init__(self, tray):
        self.tray = tray
        super().__init__()
        self.setupUi(self)
        self.pushButton.clicked.connect(self.update_notifications)
        self.label_3.setText("Последние обновление: {}".format(datetime.datetime.today().strftime('%H:%M:%S')))
        self.setWindowTitle('Gitart')
        self.setFixedSize(self.width(), self.height())
        icon = QIcon('img/dart.png')
        self.setWindowIcon(icon)
        layout = QHBoxLayout()
        self.frame.setLayout(layout)

    @staticmethod
    def create_notification_title(notification):
        qv_layout = QVBoxLayout()
        layout = QHBoxLayout()
        label = QLabel('Заголовок:')
        label.setStyleSheet("color: #6957A1;")
        layout.addWidget(label)
        layout.addWidget(QLabel("{}, ".format(notification['title'])))
        label = QLabel('Репозиторий:')
        label.setStyleSheet("color: #6957A1;")
        layout.addWidget(label)
        layout.addWidget(QLabel("{}, ".format(notification['full_name'])))
        label = QLabel('Дата создания:')
        label.setStyleSheet('color: #6957A1;')
        layout.addWidget(label)
        layout.addWidget(QLabel("{}, ".format(notification['created_time'])))
        layout.addStretch()
        qv_layout.addLayout(layout)
        if not (notification['user_login'] is None):
            layout = QHBoxLayout()
            label = QLabel('Состояние задачи:')
            label.setStyleSheet('color: #6957A1;')
            layout.addWidget(label)
            state = "открыта, " if notification['state'] == "open" else "закрыта, "
            layout.addWidget(QLabel(state))
            label = QLabel('Пользователь: ')
            label.setStyleSheet('color: #6957A1;')
            layout.addWidget(label)
            label = QLabel()
            pixmap = QtGui.QPixmap('img/{}.jpg'.format(notification['user_avatar_name']))
            label.setPixmap(pixmap.scaled(16, 16, QtCore.Qt.KeepAspectRatio))
            label.setStyleSheet('margin:0; padding:0;')
            layout.addWidget(label)
            layout.addWidget(QLabel('{}.'.format(notification['user_login'])))
            layout.addStretch()
            qv_layout.addLayout(layout)
        return qv_layout

    def create_window_notification(self):
        self.label_3.setText("Последние обновление: {}".format(datetime.datetime.today().strftime('%H:%M:%S')))
        group_box = QGroupBox()
        notifications = data_base.get_notifications()
        self.label_2.setText("Не прочитано - {} сообщен{}".format(
            len(notifications),
            get_ending_by_number(len(notifications), ['ие', 'ия', 'ий'])))
        widget = QWidget()
        main_layout = QVBoxLayout()
        layout = QVBoxLayout()
        for notification in notifications:
            layout_notification = QVBoxLayout()
            notification['number_issues'] = re.search(r'issues/\d+', notification['url'])[0].replace('issues/', '')
            layout_notification.addLayout(self.create_notification_title(notification))
            if not(notification['message'] is None):
                plain_text = QPlainTextEdit('Сообщение: {}.'.format(notification['message']))
                plain_text.setReadOnly(True)
                plain_text.setFixedSize(740, 75)
                layout_notification.addWidget(plain_text)
            open_notification = self.open_url(notification['url'].replace('api/v1/repos/', ''))
            button = QPushButton("Перейти в - {}/issues/{} ".format(notification['full_name'],
                                                                    notification['number_issues']))
            button.setStyleSheet(
                """font-size:12px; color: #337AB7; background: rgba(255,255,255,0); 
                   text-align:right; margin:0, 0, 0, 0""")
            button.clicked.connect(open_notification)
            layout_notification.addWidget(button)
            layout_notification.setSpacing(10)
            widget_notification = QWidget()
            widget_notification.setFixedSize(790, 1)
            widget_notification.setStyleSheet("border: 1px solid rgba(0, 0, 0, 15);")
            layout_notification.addWidget(widget_notification)
            layout.addLayout(layout_notification)
        layout.setSpacing(50)
        group_box.setLayout(layout)
        main_layout.addWidget(group_box)
        main_layout.addStretch()
        widget.setLayout(main_layout)
        self.scrollArea.setWidget(widget)

    def my_show(self):
        self.show()
        if self.isMinimized():
            self.showNormal()

    def update_notifications(self):
        self.label_3.setText("Последние обновление: {}".format(datetime.datetime.today().strftime('%H:%M:%S')))
        self.create_window_notification()

    @staticmethod
    def open_url(url):
        logging.debug("Переход по ссылке - {}".format(url))
        return lambda: webbrowser.open_new(url)


class Api:

    def __init__(self, server, token):
        logging.debug("Создание экземляра класса - Api")
        self.there_connection = True
        self.__server = server
        self.__access_token = token
        self.first_connection = True

    def connection_server(self):
        try:
            requests.get("{}".format(self.__server))
            logging.debug("Попытка с сервером востановлена.")
            show_message_in_tray("Подключение к серверу", 'Установлено', 'img/dart.ico')
            tray_icon.set_icon('img/dart.png')
            tray_icon.constructor_menu()
            self.there_connection = True
            self.__server = data_base.get_user()['server']
            tray_icon.constructor_menu()
            self.timer_connection_server.stop()
        except(requests.exceptions.ConnectionError, requests.exceptions.InvalidURL,
               requests.exceptions.InvalidSchema, requests.exceptions.MissingSchema,
               requests.exceptions.ReadTimeout, requests.exceptions.MissingSchema):
            logging.debug("Неудачная попытка соединение с сервером.")

    def check_connection_server(self):
        try:
            requests.get('{}'.format(self.__server))
            self.first_connection = False
            return True
        except(requests.exceptions.ConnectionError, requests.exceptions.InvalidURL,
               requests.exceptions.InvalidSchema, requests.exceptions.MissingSchema,
               requests.exceptions.ReadTimeout, requests.exceptions.MissingSchema):
            icon = QIcon('img/connection_lost.png')
            if not self.first_connection:
                show_message_in_tray("Подключение к серверу", 'Прервано', 'img/connection_lost.ico')
            self.first_connection = True
            self.there_connection = False
            tray_icon.tray.setIcon(icon)
            tray_icon.constructor_menu()
            tray_icon.window_tasks.hide()
            if tray_icon.timer_animation.isActive():
                tray_icon.timer_animation.stop()
            self.timer_connection_server = QtCore.QTimer()
            self.timer_connection_server.timeout.connect(self.connection_server)
            self.timer_connection_server.start(1000)
            return False

    def get_notifications(self):
        if self.check_connection_server():
            response = requests.get("{}/api/v1/notifications?access_token={}".format(self.__server, self.__access_token))
            logging.debug("Получение новых сообщений")
            return response

    def get_issues(self):
        if self.check_connection_server():
            if self.__access_token == '':
                return
            response = requests.get("{}/api/v1/repos/issues/search?access_token={}&assigned=true".format(self.__server,
                                                                                                     self.__access_token))
            logging.debug("Получение задач")
            return response

    def get_repos_issues(self, repo, issues):
        if self.check_connection_server():
            response = requests.get("{}/api/v1/repos/{}/issues/{}".format(self.__server, repo, issues))
            logging.debug("Получение информации о задачи в репозитории")
            return response

    def get_comment(self, repo, owner, comment):
        if self.check_connection_server():
            response = requests.get("{}/api/v1/repos/{}/{}/issues/comments/{}".format(self.__server, owner, repo,
                                                                                      comment))
            logging.debug("Получение комментария")
            return response

    def get_user(self):
        if self.check_connection_server():
            response = requests.get("{}/api/v1/user?access_token={}".format(self.__server, self.__access_token))
            logging.debug("Обращение к Api для получение информацию о своей учетной записи")
            return response

    def update_access_token(self, token):
        logging.debug("Перезапись токена доступа")
        self.__access_token = token

    @property
    def get_access_token(self):
        return self.__access_token

    @property
    def get_server(self):
        return self.__server

    def update_server(self, server):
        logging.debug("Перезапись адреса сервера: {}".format(server))
        self.__server = server


class Setting(QMainWindow, setting_ui.Ui_MainWindow):

    def __init__(self, tray_icon):
        self.tray_icon = tray_icon
        super().__init__()
        self.setupUi(self)
        self.edit_token = self.lineEdit
        self.edit_server = self.lineEdit_2
        self.edit_server.setInputMask(r'\http{}'.format('x' * 20))
        self.setFixedSize(self.width(), self.height())

    def my_show(self):
        self.label_4.setPixmap(QtGui.QPixmap('img/dart.png'))
        self.setWindowFlags(QtCore.Qt.CustomizeWindowHint)
        self.pushButton.clicked.connect(self.save_settings)
        self.pushButton_2.clicked.connect(self.hide)
        read_data = data_base.get_user()
        self.edit_token.setText(read_data.get('token', ''))
        self.edit_server.setText(read_data.get('server', ''))
        logging.debug("Показ окна настроек")
        self.show()
        screen_geometry = QApplication.desktop().availableGeometry()
        screen_size = (screen_geometry.width(), screen_geometry.height())
        window_size = (self.frameSize().width(), self.frameSize().height())
        x = screen_size[0] - window_size[0] - 50
        y = screen_size[1] - window_size[1] - 10
        self.move(x, y)

    def save_settings(self):
        logging.debug("Передача новых настроек в конфигурационный файл.")
        self.edit_token.setText(self.edit_token.text())
        self.edit_server.setText(self.edit_server.text())
        if not self.tray_icon.user_logged:
            self.edit_token.setText(data_base.get_user()['token'])
        data_base.update_user({'token': "'{}'".format(self.edit_token.text()),
                              'server': "'{}'".format(self.edit_server.text())})
        self.tray_icon.constructor_menu()
        self.hide()


class TrayIcon:

    def __init__(self, icon, app):
        logging.debug("Создание экземпляра класса - TrayIcon.")
        self.app = app
        self.tray = QSystemTrayIcon()
        self.status_animation = 0
        self.tray.activated.connect(self.controller_tray_icon)
        self.name_icon = icon
        self.menu_items = []
        self.user_id = 0
        self.icon = QIcon(icon)
        self.tray.setIcon(self.icon)
        self.len_new_notification = 0
        self.tray.setVisible(True)
        self.menu = QMenu()
        self.hint = ''
        self.user_logged = True
        self.notifications = []
        self.setting = Setting(self)
        self.exist_messages = data_base.get_notifications()
        self.window_tasks = MainWindowTasks(self)
        self.timer_animation = QtCore.QTimer()
        self.timer_animation.timeout.connect(self.animation)
        self.timer_subscribe_notifications = QtCore.QTimer()
        self.timer_subscribe_notifications.timeout.connect(self.subscribe_notification)

    def output_in_tray_data_about_tasks(self, notifications):
        for notification in notifications:
            if notification['state'] == 'closed':
                message = "Задача закрыта"
            elif not (notification['message'] == '' or notification['message'] is None):
                message = "\n'Новое сообщение:{}'".format(notification['message'])
            else:
                message = "Задача открыта"
            show_message_in_tray(notification['title'], message, 'img/notification.ico')

    def subscribe_notification(self):
        logging.debug("Проверка новых сообщений")
        notifications = data_base.get_notifications()
        change_notifications = []
        new_notifications = []
        for notification in notifications:
            if_exist = False
            new_notifications.append(notification)
            for exist_message in self.exist_messages:
                new_notifications.append(exist_message)
                if exist_message['id'] == notification['id'] and exist_message['message'] == notification['message'] \
                   and exist_message['state'] == notification['state']:
                    if_exist = True
                    break
            if not if_exist:
                change_notifications.append(notification)
        self.exist_messages = new_notifications
        self.output_in_tray_data_about_tasks(change_notifications)
        self.tray.setToolTip("Не прочитано - {} сообщен{}.".format(len(notifications),
                             get_ending_by_number(len(notifications), ['ие', 'ия', 'ий'])))
        if not len(data_base.get_notifications()) == 0 and not(self.timer_animation.isActive()):
            self.constructor_menu()
            self.timer_animation.start(2000)

    def animation(self):
        if self.status_animation == 0:
            self.set_icon("img/{}.jpg".format(str(data_base.get_user()['id'])))
            self.status_animation = 1
        else:
            self.set_icon("img/notification.png")
            self.status_animation = 0

    def show_notification(self):
        if not len(data_base.get_notifications()) == 0:
            self.window_tasks.create_window_notification()
            self.window_tasks.my_show()

    def controller_tray_icon(self, trigger):
        if trigger == 3 and not self.user_logged:  # Левая кнопка мыши
            self.show_notification()
        if trigger == 1:  # Правая кнопка мыши
            self.tray.show()

    def set_icon(self, icon):
        logging.debug("Установление изображение для TrayIcon, путь до картинки: {}".format(icon))
        self.name_icon = icon
        self.icon = QIcon(icon)
        self.tray.setIcon(self.icon)

    def authentication_successful(self):
        data_base.set_authorisation(True)
        user = data_base.get_user()
        download_icon(user['avatar_url'], data_base.get_user()['id'])
        self.user_logged = False
        logging.debug("TrayIcon: Токен доступа действителен. Информация о пользователе: {}".format(user['full_name']))
        name_user = QAction("{}({})".format(user['full_name'], user["login"]))
        name_user.setEnabled(False)
        self.menu.addAction(name_user)
        self.menu_items.append(name_user)
        self.set_icon('img/{}.jpg'.format(str(user['id'])))
        logout = self.logout
        login = QAction('Выйти из {}'.format(user['login']))
        login.triggered.connect(logout)
        self.menu.addAction(login)
        self.menu_items.append(login)
        if not(self.timer_subscribe_notifications.isActive()):
            self.timer_subscribe_notifications.start(1000)

    def constructor_menu(self):
        self.tray.setToolTip("Необходима авторизация через токен")
        logging.debug("TrayIcon: Создание контекстного меню для TrayIcon")
        name_aplication = QAction("Gitart")
        name_aplication.setEnabled(False)
        self.menu.addAction(name_aplication)
        self.menu_items.append(name_aplication)
        try:
            if data_base.get_there_connection():
                data_base.get_user_data_from_api()
        except (json.decoder.JSONDecodeError, AttributeError):
            self.tray.setToolTip("Подключение к серверу отсуствует")
            logging.debug("Подключение к серверу отсуствует")
        if data_base.get_user()['server'] == '':
            self.tray.setToolTip("Введите адрес сервера")
        self.menu_items = []
        self.menu = QMenu()
        if data_base.get_there_connection() and not (data_base.get_user()['full_name'] is None
                                                     or data_base.get_user()['full_name'] == 'NULL'):
            self.authentication_successful()
        else:
            logging.debug("TrayIcon: Токена доступа нет или он недействителен")
        auth = QAction('Настройки')
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
        data_base.set_authorisation(False)
        self.timer_animation.stop()
        self.timer_subscribe_notifications.stop()
        self.window_tasks.close()
        time.sleep(1)
        data_base.update_user({'token': 'null'})
        self.set_icon('img/dart.png')
        self.user_logged = True
        self.constructor_menu()


tray_icon = None
data_base = DataBase()
data_base.start()


def main():
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    current_date = datetime.datetime.today().strftime('%d-%m-%Y')
    format_logging = '%(asctime)s   %(levelname)-10s   %(message)s'
    myappid = 'myproduct'
    QtWin.setCurrentProcessExplicitAppUserModelID(myappid)
    sys.excepthook = crash_script
    if not (os.path.exists('logs')):
        os.mkdir('logs')
    logging.basicConfig(filename="logs/Debug-{}.log".format(current_date),
                        level=logging.DEBUG, format=format_logging, datefmt='%H:%M:%S', force=True)
    logging.info("Запуск программы")
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('./img/dart.png'))
    app.setQuitOnLastWindowClosed(False)
    global tray_icon
    tray_icon = TrayIcon('img/dart.png', app)
    app.processEvents()
    tray_icon.constructor_menu()
    app.exec_()


if __name__ == '__main__':
    main()
