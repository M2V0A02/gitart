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
import my_sql_lite
from PyQt5.QtWinExtras import QtWin
from PyQt5.QtCore import QThread

# Когда лог, больше несколько строк indent_format показывает сколько должно быть отступов у новой строки.
indent_format = 24


def download_icon(url, name):
    logging.debug("Скачивание аватара пользователя.")
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


def filter_assigned_you_task(all_tasks, user):
    def filter_tasks(assigned_to_you_tasks):
        if not (assigned_to_you_tasks['assignees'] is None):
            for assigned_to_you_task in (assigned_to_you_tasks['assignees']):
                if assigned_to_you_task['login'] == user['login']:
                    return True
        return False

    return list(filter(filter_tasks, all_tasks))


def save_notifications(api, notifications, table):
    for notification in notifications:
        message = 'null'
        if not (notification['subject']['latest_comment_url'] == ''):
            id_comments = re.search(r'comments/\d+', format(notification['subject']
                                                            ['latest_comment_url']))[0].replace('comments/', '')
            try:
                message = "'{}'".format(json.loads(api.get_comment(id_comments).text)['body'])
            except (json.decoder.JSONDecodeError, AttributeError):
                message = 'null'
        user_login = 'null'
        user_avatar_name = 'null'
        if not (notification['subject']['url'] == ''):
            repo = re.search(r'repos/.+/issues', notification['subject']['url'])[0]. \
                replace('repos/', '').replace('/issues', '')
            issues = re.search(r'/issues/.+', notification['subject']['url'])[0].replace('/issues/', '')
            try:
                repo = json.loads(api.get_repos_issues(repo, issues).text)
                user_login = "'{}'".format(repo['user']['login'])
                user_avatar_name = "'{}'".format(repo['user']['avatar_url'].replace("http://server300:1080/avatars/", ''))
                download_icon(repo['user']['avatar_url'], user_avatar_name)
            except (json.decoder.JSONDecodeError, AttributeError):
                user_login = 'null'
        full_name = "'{}'".format(notification.get('repository', {}).get('full_name', 'null'))
        created_time = "'{}'".format(formatting_the_date(notification.get('updated_at', 'null')))
        url = "'{}'".format(notification.get('subject', {}).get('url', 'null'))
        state = "'{}'".format(notification['subject']['state'])
        title = "'{}'".format(notification['subject']['title'])
        table.save(message, user_login, full_name, created_time, url, user_avatar_name, state, title)


def save_assigned_tasks(api, assigned_tasks, table):
    assigned_to_you_tasks = filter_assigned_you_task(assigned_tasks, json.loads(api.get_user().text))
    for assigned_to_you_task in assigned_to_you_tasks:
        title = "'{}'".format(assigned_to_you_task['title'])
        task_id = re.search(r'/issues/.+', assigned_to_you_task['url'])[0].replace("/issues/", '')
        full_name = "'{}'".format(assigned_to_you_task['repository']['full_name'])
        created_time = "'{}'".format(formatting_the_date(assigned_to_you_task['created_at']).strftime('%d-%m-%Y'))
        creator = "'{}'".format(assigned_to_you_task['user']['login'])
        url = "'{}'".format(assigned_to_you_task['html_url'])
        milestone_title = "''"
        if not (assigned_to_you_task['milestone'] is None):
            milestone_title = "'{}'".format(assigned_to_you_task['milestone']['title'])
        table.save(task_id, title, full_name, created_time, creator, url, milestone_title)


def update_user(api):
    user_json = json.loads(api.get_user().text)
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
        self.table_assigned_tasks = my_sql_lite.AssignedTasks()
        self.last_assigned_tasks = self.table_assigned_tasks.get_all()
        self.table_users = my_sql_lite.Users()
        self.last_user = self.table_users.get()
        self.api = Api(self, self.last_user['server'], self.last_user['token'])
        self.authorisation = False

    def run(self):
        while True:
            if self.authorisation:
                logging.debug("Проверка новых сообщений")
                self.table_notifications.clear()
                self.table_assigned_tasks.clear()
                if self.api is not None:
                    save_notifications(self.api, json.loads(self.api.get_notifications().text), self.table_notifications)
                    save_assigned_tasks(self.api, json.loads(self.api.get_issues().text), self.table_assigned_tasks)
                    self.last_notifications = self.table_notifications.get_all()
                    self.last_assigned_tasks = self.table_assigned_tasks.get_all()

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


class MainWindowTasks:

    def __init__(self, tray):
        self.tray = tray
        self.main_window = QMainWindow()
        self.scroll = QScrollArea(self.main_window)
        self.main_window.setFixedSize(830, 830)
        self.main_window.setWindowTitle('Gitart')
        self.window = QWidget()
        self.update_button = QPushButton()
        icon = QIcon('img/dart.png')
        self.main_window.setWindowIcon(icon)
        self.layout = QVBoxLayout()
        self.notifications_scroll_area = QScrollArea()
        self.tasks_scroll_area = QScrollArea()
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.notifications_scroll_area, "Новые задачи")
        self.tab_widget.addTab(self.tasks_scroll_area, "Назначено вам")
        self.tab_widget.tabBarClicked.connect(self.controller_tab_clicked)
        self.layout.addWidget(self.tab_widget)
        self.window.resize(825, 825)
        self.window.setLayout(self.layout)
        self.scroll.setWidget(self.window)
        self.scroll.resize(830, 830)

    def controller_tab_clicked(self, number_tab):
        controller = {
            0: self.create_window_notification(),
            1: self.create_window_tasks()
        }
        controller[number_tab]

    @staticmethod
    def get_assigned_to_you_tasks():
        assigned_tasks = data_base.get_assigned_tasks()
        for assigned_task in assigned_tasks:
            assigned_task['title'] = '{:.47}...'.format(assigned_tasks['title']) if len(assigned_tasks) > 50\
                else assigned_task['title']
            assigned_task['task_id'] = re.search(r'/issues/.+', assigned_task['url'])[0].replace('/issues/', '')
            assigned_task['body'] = '{}#{} открыта {} {}.'.format(assigned_task['full_name'], assigned_task['task_id'],
                                                                  assigned_task['created_at'], assigned_task['creator'])
            assigned_task['body'] = '{:.57}...'.format(assigned_task['body']) if len(assigned_task['body']) > 60\
                else assigned_task['body']
            if not (assigned_task['milestone_title'] is None):
                name_title = "Этап: {}".format(assigned_task['milestone_title'])
                name_title = '{:.47}...'.format(name_title) if len(name_title) > 50 else name_title
                assigned_task['milestone_title'] = name_title
        return assigned_tasks

    def create_window_tasks(self):
        widget = QWidget()
        main_layout = QVBoxLayout()
        layout = QHBoxLayout()
        assigned_to_you_tasks = self.get_assigned_to_you_tasks()
        label = QLabel('Вам назначен{} - {} задач{}.'.format(
            get_ending_by_number(len(assigned_to_you_tasks), ['а', 'ы', 'о']),
            len(assigned_to_you_tasks),
            get_ending_by_number(len(assigned_to_you_tasks), ['а', 'и', ''])))
        label.setStyleSheet('font-size:24px;')
        button = QPushButton('Обновить')
        button.clicked.connect(self.create_window_tasks)
        layout.addWidget(label)
        layout.addWidget(button)
        main_layout.addLayout(layout)
        number_of_messages_per_line = 2
        layout_message = QHBoxLayout()
        y = 0
        for assigned_to_you in assigned_to_you_tasks:
            label = QLabel(assigned_to_you['title'])
            label.setStyleSheet("font-size:18px;")
            div = QWidget()
            layout = QVBoxLayout(div)
            div.setStyleSheet("margin-left:15px; width:345px;")
            layout.addWidget(label)
            label = QLabel(assigned_to_you['body'])
            label.setStyleSheet("font-size:12px;")
            layout.addWidget(label)
            label = QLabel(assigned_to_you['milestone_title'])
            layout.addWidget(label)
            button = QPushButton("Перейти в {}".format(assigned_to_you['url'].replace('http://', '')))
            open_tasks = self.open_url(assigned_to_you['url'])
            button.clicked.connect(open_tasks)
            button.setStyleSheet("""font-size:12px; color: #23619e; background: rgba(255,255,255,0);
                                 "border-radius: .28571429rem; height: 20px; border-color: #dedede; text-align:left""")
            layout.addWidget(button)
            layout_message.addWidget(div)
            y += 1
            if y % number_of_messages_per_line == 0:
                main_layout.addLayout(layout_message)
                layout_message = QHBoxLayout()
        if not (y + 1 % number_of_messages_per_line == 0):
            main_layout.addLayout(layout_message)
        main_layout.addStretch()
        widget.setLayout(main_layout)
        self.tasks_scroll_area.setWidget(widget)
        self.tab_widget.update()

    @staticmethod
    def create_notification_title(notification):
        layout = QHBoxLayout()
        label = QLabel('Репозиторий:')
        label.setStyleSheet("color: #808080;")
        layout.addWidget(label)
        repo = notification['full_name']
        layout.addWidget(QLabel("{}, ".format(repo)))
        label = QLabel('дата создания:')
        label.setStyleSheet('color: #808080;')
        layout.addWidget(label)
        layout.addWidget(QLabel("{}, ".format(notification['created_time'])))
        if not (notification['user_login'] is None):
            label = QLabel('пользователь: ')
            label.setStyleSheet('color: #808080;')
            layout.addWidget(label)
            label = QLabel()
            pixmap = QtGui.QPixmap('img/{}.jpg'.format(notification['user_avatar_name']))
            label.setPixmap(pixmap.scaled(16, 16, QtCore.Qt.KeepAspectRatio))
            label.setStyleSheet('margin:0; padding:0;')
            layout.addWidget(label)
            layout.addWidget(label)
            layout.addWidget(QLabel('{}.'.format(notification['user_login'])))
        layout.addStretch()
        return layout

    def create_window_notification(self):
        group_box = QGroupBox()
        notifications = data_base.get_notifications()
        widget = QWidget()
        main_layout = QVBoxLayout()
        label = QLabel("Не прочитано - {} сообщен{}.".format(
            len(notifications),
            get_ending_by_number(len(notifications), ['ие', 'ия', 'ий'])))
        label.setStyleSheet('font-size:24px;')
        main_layout.addWidget(label)
        layout = QHBoxLayout()
        self.update_button = QPushButton('Обновить')
        self.update_button.setStyleSheet('max-width:75px; min-width:75px;')
        self.update_button.clicked.connect(self.update_notifications)
        layout.addWidget(self.update_button)
        label = QLabel("Последние обновление в {}.".format(datetime.datetime.today().strftime('%H:%M:%S')))
        layout.addWidget(label)
        main_layout.addLayout(layout)
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
                """font-size:12px; color: #23619e; background: rgba(255,255,255,0); border-radius:
                 .28571429rem; height: 20px; border-color: #dedede; text-align:right; margin:0, 0, 0, 20""")
            button.clicked.connect(open_notification)
            layout_notification.addWidget(button)
            layout_notification.setSpacing(10)
            layout.addLayout(layout_notification)
        layout.setSpacing(50)
        group_box.setLayout(layout)

        main_layout.addWidget(group_box)
        widget.setLayout(main_layout)
        self.notifications_scroll_area.setWidget(widget)
        self.tab_widget.update()

    def show(self):
        self.main_window.show()
        if self.main_window.isMinimized():
            self.main_window.showNormal()

    def update_notifications(self):
        self.create_window_notification()

    @staticmethod
    def open_url(url):
        logging.debug("Переход по ссылке - {}".format(url))
        return lambda: webbrowser.open_new(url)


class Api:

    def __init__(self, tray, server, token):
        logging.debug("Создание экземляра класса - Api")
        self.there_connection = True
        self.__server = server
        self.tray = tray
        self.__access_token = token
        self.first_connection = True

    def connection_server(self):
        try:
            requests.get("{}".format(self.__server), timeout=1)
            self.tray.tray.showMessage("Подключение к серверу", 'Установлено', QIcon('img/dart.png'))
            self.tray.set_icon('img/dart.png')
            self.tray.constructor_menu()
            self.there_connection = True
            self.__server = data_base.get_user()['server']
            self.tray.constructor_menu()
            self.timer_connection_server.stop()
        except(requests.exceptions.ConnectionError, requests.exceptions.InvalidURL,
               requests.exceptions.InvalidSchema, requests.exceptions.MissingSchema,
               requests.exceptions.ReadTimeout, requests.exceptions.MissingSchema):
            logging.debug("Попытка соединение с сервером.")

    def check_connection_server(self):
        try:
            requests.get('{}'.format(self.__server), verify=False, timeout=1)
            return True
        except(requests.exceptions.ConnectionError, requests.exceptions.InvalidURL,
               requests.exceptions.InvalidSchema, requests.exceptions.MissingSchema,
               requests.exceptions.ReadTimeout, requests.exceptions.MissingSchema):
            icon = QIcon('img/connection_lost.png')
            if not self.first_connection:
                self.tray.tray.showMessage("Подключение к серверу", 'Прервано', QIcon('img/connection_lost.png'))
            self.first_connection = False
            self.there_connection = False
            self.tray.tray.setIcon(icon)
            self.tray.constructor_menu()
            self.tray.window_notification.main_window.hide()
            if self.tray.timer_animation.isActive():
                self.tray.timer_animation.stop()
            self.timer_connection_server = QtCore.QTimer()
            self.timer_connection_server.timeout.connect(self.connection_server)
            self.timer_connection_server.start(2500)
            return False

    def get_notifications(self):
        if self.check_connection_server():
            response = requests.get("{}/api/v1/notifications?access_token={}".format(self.__server, self.__access_token))
            logging.debug("Получение новых сообщений")
            return response

    def get_issues(self):
        if self.check_connection_server():
            response = requests.get("{}/api/v1/repos/issues/search?access_token={}&limit=100".format(self.__server,
                                                                                                     self.__access_token))
            logging.debug("Получение задач")
            return response

    def get_repos_issues(self, repo, issues):
        if self.check_connection_server():
            response = requests.get("{}/api/v1/repos/{}/issues/{}".format(self.__server, repo, issues))
            logging.debug("Получение информации о задачи в репозитории")
            return response

    def get_comment(self, comment):
        if self.check_connection_server():
            response = requests.get("{}/api/v1/repos/VolodinMA/MyGitRepository/issues/comments/{}".format(self.__server,
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
        self.first_connection = True
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

    def my_show(self):
        self.setFixedSize(self.width(), self.height())
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
        logging.debug("Передача новых настроек в конфигурационный файл")
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
        logging.debug("Создание экземпляра класса - TrayIcon")
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
        self.update_date_time = datetime.datetime.time(datetime.datetime.today())
        self.tray.setVisible(True)
        self.menu = QMenu()
        self.timer_update_tool_tip = QtCore.QTimer()
        self.timer_update_tool_tip.timeout.connect(self.update_tool_tip)
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
                message = "репозиторий закрыт"
            elif not (notification['message'] == ''):
                message = "\n'Новое сообщение:{}'".format(notification['message'])
            else:
                message = "Репозиторий открыт"
            self.tray.showMessage(notification['title'], message, QIcon('img/notification.png'))

    def subscribe_notification(self):
        logging.debug("Проверка новых сообщений")
        notifications = data_base.get_notifications()
        change_notifications = []
        new_notifications = []
        for notification in notifications:
            if_exist = False
            new_notifications.append(notification)
            for exist_message in self.exist_messages:
                if exist_message['created_time'] == notification['created_time'] and \
                        exist_message['message'] == notification['message']:
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
            self.window_tasks.show()

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

    def update_tool_tip(self):
        now_delta = datetime.timedelta(minutes=datetime.datetime.today().minute, seconds=datetime.datetime.today().second)
        past_delta = datetime.timedelta(minutes=self.update_date_time.minute, seconds=self.update_date_time.second)
        difference = now_delta - past_delta
        minute_difference = difference.seconds // 60
        second_difference = difference.seconds % 60
        if not minute_difference == 0:
            minute = "{} минут{}".format(minute_difference, get_ending_by_number(minute_difference, ['а', 'ы', '']))
        else:
            minute = ''
        if not second_difference == 0:
            second = "{} секунд{}".format(second_difference, get_ending_by_number(second_difference, ['а', 'ы', '']))
        else:
            second = ''

        self.tray.setToolTip("Вам назначенно {} задач{}. Обновлено - {} {} назад"
                             .format(self.len_new_notification, get_ending_by_number(self.len_new_notification, ['а', 'и', '']),
                                     minute, second))

    def authentication_successful(self):
        data_base.set_authorisation(True)
        user = data_base.get_user()
        if self.user_logged:
            info_about_user = "Логин: {} \nФИО: {}".format(user['login'], user['full_name'])
            self.tray.showMessage('Авторизация', info_about_user, QIcon("img/{}.jpg".format(str(user['id']))))
        self.user_logged = False
        logging.debug("TrayIcon: Токен доступа действителен. Информация о пользователе: {}".format(user['full_name']))
        name_user = QAction("{}({})".format(user['full_name'], user["login"]))
        name_user.setEnabled(False)
        self.menu.addAction(name_user)
        self.menu_items.append(name_user)
        download_icon(user['avatar_url'], data_base.get_user()['id'])
        self.set_icon('img/{}.jpg'.format(str(user['id'])))
        logout = self.logout
        login = QAction('Выйти из {}'.format(user['login']))
        login.triggered.connect(logout)
        self.menu.addAction(login)
        self.menu_items.append(login)
        self.update_date_time = datetime.datetime.time(datetime.datetime.today())
        if not(self.timer_animation.isActive()):
            self.timer_update_tool_tip.start(1000)
        read_data = data_base.get_user()
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
        self.timer_update_tool_tip.stop()
        self.window_tasks.main_window.close()
        data_base.update_user({'token': 'null'})
        self.set_icon('img/dart.png')
        self.user_logged = True
        self.tray.showMessage('Авторизация', 'Снята', QIcon('img/dart.png'))
        self.constructor_menu()


data_base = DataBase()
data_base.start()


def main():
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    myappid = 'myproduct'
    QtWin.setCurrentProcessExplicitAppUserModelID(myappid)
    sys.excepthook = crash_script
    current_date = datetime.datetime.today().strftime('%d-%m-%Y')
    format_logging = '%(asctime)s   %(levelname)-10s   %(message)s'
    if not (os.path.exists('logs')):
        os.mkdir('logs')
    logging.basicConfig(filename="logs/Debug-{}.log".format(current_date),
                        level=logging.DEBUG, format=format_logging, datefmt='%H:%M:%S')
    logging.info("Запуск программы")
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('./img/dart.png'))
    app.setQuitOnLastWindowClosed(False)
    tray_icon = TrayIcon('img/dart.png', app)
    tray_icon.constructor_menu()
    app.exec_()


if __name__ == '__main__':
    main()
