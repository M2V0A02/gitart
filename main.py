import traceback
import PyQt5.QtSvg
from PyQt5 import QtCore, QtWidgets
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
import mySQLlite
from PyQt5.QtWinExtras import QtWin
# Когда лог, больше несколько строк indent_format показывает сколько должно быть отступов у новой строки.
indent_format = 24


def crash_script(error_type, value, tb):
    traces = traceback.extract_tb(tb)
    critical_error = "{}: {},  \n".format(error_type, value)

    for frame_summary in traces:
        critical_error += "{:indent_format}File '{}', line {}, in {}, \n{:indent_format} {} \n".format('', frame_summary.filename,
                                                                           frame_summary.lineno,
                                                                           frame_summary.name, '',
                                                                           frame_summary.line)
    logging.critical(critical_error)
    sys.__excepthook__(error_type, value, tb)


class Notification:

    def __init__(self, api, tray):
        self.tray = tray
        self.main_window = QMainWindow()
        self.scroll = QScrollArea(self.main_window)
        self.main_window.setFixedSize(830, 830)
        self.main_window.setWindowTitle("Gitart")
        self.window = QWidget()
        self.update_button = QPushButton()
        icon = QIcon('img/logo.svg')
        self.main_window.setWindowIcon(icon)
        self.layout = QVBoxLayout()
        self.api = api
        self.notifications_scroll_area = QScrollArea()
        self.tasks_scroll_area = QScrollArea()
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.notifications_scroll_area, 'Новые задачи')
        self.tab_widget.addTab(self.tasks_scroll_area, 'Назначено вам')
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
    def formatting_the_date(string_date):
        string_date = datetime.datetime.strptime(string_date, '%Y-%m-%dT%H:%M:%SZ')
        timezone = str(datetime.datetime.now(datetime.timezone.utc).astimezone())
        timezone = int(timezone[len(timezone) - 5:len(timezone) - 3])
        string_date = string_date + datetime.timedelta(hours=timezone)
        return string_date

    def get_assigned_to_you(self):
        user = json.loads(self.api.get_user().text)
        # убираю из списка задач мои, чтобы остались только назначенные.

        def filter_tasks(assigned_to_you_tasks):
            if not (assigned_to_you_tasks['assignees'] is None):
                for assigned_to_you_task in (assigned_to_you_tasks['assignees']):
                    if assigned_to_you_task['login'] == user['login']:
                        return True
            return False
        assigned_to_you = json.loads(self.api.get_issues().text)
        return list(filter(filter_tasks, assigned_to_you))

    def show_assigned_to_you(self, assigned_to_you_tasks, main_layout):
        number_of_messages_per_line = 2
        layout_message = QHBoxLayout()
        y = 0
        for assigned_to_you_task in assigned_to_you_tasks:
            name_label = '{:.47}...'.format(assigned_to_you_task['title']) if len(assigned_to_you_task) > 50\
                else assigned_to_you_task['title']
            label = QLabel(name_label)
            label.setStyleSheet("font-size:18px;")
            div = QWidget()
            layout = QVBoxLayout(div)
            div.setStyleSheet("margin-left:15px; width:345px;")
            layout.addWidget(label)
            task_id = re.search(r'/issues/.+', assigned_to_you_task['url'])[0].replace('/issues/', '')
            body = "{}#{} открыта {} {}.".format(assigned_to_you_task['repository']['full_name'],
                                                                task_id, self.formatting_the_date(
                    assigned_to_you_task['created_at']).strftime('%d-%m-%Y'),
                                                                assigned_to_you_task['user']['login'])
            body = '{:.57}...'.format(body) if len(body) > 60 else body
            label = QLabel(body)
            label.setStyleSheet("font-size:12px;")
            layout.addWidget(label)
            if not (assigned_to_you_task['milestone'] is None):
                name_title = "Этап: {}".format(assigned_to_you_task['milestone']['title'])
                name_title = '{:.47}...'.format(name_title) if len(name_title) > 50 else name_title
                label = QLabel(name_title)
                layout.addWidget(label)
            button = QPushButton("Перейти в {}".format(assigned_to_you_task['html_url'].replace("http://", '')))
            open_tasks = self.open_url(assigned_to_you_task['html_url'])
            button.clicked.connect(open_tasks)
            button.setStyleSheet(
                "font-size:12px; color: #23619e; background: rgba(255,255,255,0);"
                "border-radius: .28571429rem; height: 20px; border-color: #dedede; text-align:left")
            layout.addWidget(button)
            layout_message.addWidget(div)
            y += 1
            if y % number_of_messages_per_line == 0:
                main_layout.addLayout(layout_message)
                layout_message = QHBoxLayout()
        if not (y + 1 % number_of_messages_per_line == 0):
            main_layout.addLayout(layout_message)
        main_layout.addStretch()

    def create_window_tasks(self):
        widget = QWidget()
        main_layout = QVBoxLayout()
        layout = QHBoxLayout()
        assigned_to_you = self.get_assigned_to_you()
        if len(assigned_to_you) == 1:
            ending_task = "а"
            ending_assign = "а"
        elif 1 < len(assigned_to_you) < 5:
            ending_assign = "ы"
            ending_task = "и"
        else:
            ending_assign = "о"
            ending_task = ''
        label = QLabel('Вам назначен{} - {} задач{}.'.format(ending_assign, len(assigned_to_you), ending_task))
        label.setStyleSheet("font-size:24px;")
        button = QPushButton("Обновить")
        button.clicked.connect(self.create_window_tasks)
        layout.addWidget(label)
        layout.addWidget(button)
        main_layout.addLayout(layout)
        self.show_assigned_to_you(assigned_to_you, main_layout)
        widget.setLayout(main_layout)
        self.tasks_scroll_area.setWidget(widget)
        self.tab_widget.update()

    def get_additional_information(self, notifications):
        addititonal_information = dict()
        if not (notifications['subject']['latest_comment_url'] == ''):
            try:
                id_comments = re.search(r'comments/\d+', format(notifications['subject']
                                                                ['latest_comment_url']))[0].replace('comments/', '')
                addititonal_information['body'] = (json.loads(self.api.get_comment(id_comments).text)['body'])
            except json.decoder.JSONDecodeError:
                logging.error("Не получилось получить комментарий, url - {}".
                              format(notifications['subject']['latest_comment_url']))
        if not(notifications['subject']['url'] == ''):
            try:
                repo = re.search(r'repos/.+/issues', notifications['subject']['url'])[0].replace('repos/', '').replace(
                    '/issues', '')
                issues = re.search(r'/issues/.+', notifications['subject']['url'])[0].replace('/issues/', '')
                notification = json.loads(self.api.get_repos_issues(repo, issues).text)
                addititonal_information['user_login'] = (notification['user']['login'])
            except json.decoder.JSONDecodeError:
                logging.error("Не получилось получить задачи, url - {}".format(notifications['subject']['url']))
        return addititonal_information

    def show_notifications(self, notifications, main_layout):
        for notification in notifications:
            additional_information = self.get_additional_information(notification)
            repo = notification['repository']['full_name']
            created_time = str(self.formatting_the_date(notification['repository']['owner']['created']))
            text_title = 'Репозиторий: {}, дата создания: {}'.format(repo, created_time)
            if 'user_login' in additional_information:
                text_title = "{}, пользователь - {}.".format(text_title, additional_information['user_login'])
                text_title = '{:.127}...'.format(text_title) if len(text_title) > 130 else text_title
            label = QLabel(text_title)
            label.setStyleSheet("font-size:12px;")
            main_layout.addWidget(label)
            if 'body' in additional_information:
                plain_text = QPlainTextEdit('Сообщение: {}.'.format(additional_information['body']))
                plain_text.setReadOnly(True)
                plain_text.setFixedSize(740, 75)
                main_layout.addWidget(plain_text)
            open_notification = self.open_url(notification['subject']['url'].replace('api/v1/repos/', ''))
            number_issues = re.search(r'issues/\d+', notification['subject']['url'])[0].replace('issues/', '')
            button = QPushButton("Перейти в - {}/issues/{} ".format(notification['repository']['full_name'],
                                                                    number_issues))
            button.setStyleSheet(
                "font-size:12px; color: #23619e; background: rgba(255,255,255,0); border-radius:"
                " .28571429rem; height: 20px; border-color: #dedede; text-align:right;")
            button.clicked.connect(open_notification)
            main_layout.addWidget(button)

    def create_window_notification(self):
        notifications = json.loads(self.api.get_notifications().text)
        widget = QWidget()
        main_layout = QVBoxLayout()
        if len(notifications) == 1:
            ending = "ие"
        elif 1 < len(notifications) < 5:
            ending = "ия"
        else:
            ending = "ий"
        label = QLabel("Не прочитано - {} сообщен{}.".format(len(notifications), ending))
        label.setStyleSheet("font-size:24px;")
        main_layout.addWidget(label)
        layout = QHBoxLayout()
        self.update_button = QPushButton("Обновить")
        self.update_button.setStyleSheet("max-width:75px; min-width:75px;")
        self.update_button.clicked.connect(self.update_notifications)
        layout.addWidget(self.update_button)
        label = QLabel("Последние обновление в {}.".format(datetime.datetime.today().strftime('%H:%M:%S')))
        layout.addWidget(label)
        main_layout.addLayout(layout)
        self.show_notifications(notifications, main_layout)
        main_layout.addStretch()
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


class DB:
    def __init__(self, api):
        self.api = api

    @staticmethod
    def formatting_the_date(string_date):
        string_date = datetime.datetime.strptime(string_date, '%Y-%m-%dT%H:%M:%SZ')
        timezone = str(datetime.datetime.now(datetime.timezone.utc).astimezone())
        timezone = int(timezone[len(timezone) - 5:len(timezone) - 3])
        string_date = string_date + datetime.timedelta(hours=timezone)
        return string_date

    def get_assigned_to_you(self, all_tasks):
        user = json.loads(self.api.get_user().text)
        # убираю из списка задач мои, чтобы остались только назначенные.

        def filter_tasks(assigned_to_you_tasks):
            if not (assigned_to_you_tasks['assignees'] is None):
                for assigned_to_you_task in (assigned_to_you_tasks['assignees']):
                    if assigned_to_you_task['login'] == user['login']:
                        return True
            return False
        return list(filter(filter_tasks, all_tasks))

    def save_notifications(self):
        notifications = mySQLlite.Notifications()
        response = json.loads(self.api.get_notifications().text)
        message = ""
        if not (response['subject']['latest_comment_url'] == ''):
                id_comments = re.search(r'comments/\d+', format(notifications['subject']
                                                                ['latest_comment_url']))[0].replace('comments/', '')
                message = json.loads(self.api.get_comment(id_comments).text)['body']
        user_login = response['user']['login']
        full_name = response['repository']['full_name']
        created_time = self.formatting_the_date(response['repository']['owner']['created'])
        url = response['subject']['url']
        notifications.save(message, user_login, full_name, created_time, url)

    def save_assigned_tasks(self):
        tasks = mySQLlite.AssignedTasks()
        all_tasks = json.loads(self.api.get_issues().text)
        assigned_tasks = self.get_assigned_to_you(all_tasks)
        for assigned_task in assigned_tasks:
            title = assigned_task['title']
            task_id = re.search(r'/issues/.+', assigned_task['url'])[0].replace('/issues/', '')
            full_name = assigned_task['repository']['full_name']
            created_time = self.formatting_the_date(assigned_task['created_at']).strftime('%d-%m-%Y')
            creator = assigned_task['user']['login']
            url = assigned_task['html_url']
            tasks.save(task_id, title, full_name, created_time, creator, url)

    def save_user(self):
        user = mySQLlite.Users()
        user_json = json.loads(self.api.get_user())
        full_name = user_json['full_name']
        login = user_json['login']
        token = self.api.get_access_token()
        avatar_url = user_json['avatar_url']
        user.save(full_name, login, token, avatar_url)

class Api:

    def __init__(self, server, access_token, tray):
        logging.debug("Создание экземляра класса - Api")
        self.__server = server
        self.tray = tray
        self.__access_token = access_token

    def window_change_server(self):
        dlg = QDialog()
        dlg.setWindowTitle("Изменение сервера")
        dlg.resize(250, 25)
        layout = QVBoxLayout(dlg)
        label = QLabel("Адрес сервера:")
        layout.addWidget(label)
        edit_server = QtWidgets.QTextEdit()
        layout.addWidget(edit_server)
        button = QPushButton("Изменить сервер")
        layout.addWidget(button)

        def change_server(dialog_window):

            def func():
                dialog_window.close()
                self.tray.config.save_settings({'server': edit_server.toPlainText()})
                self.__server = edit_server.toPlainText()
            return func
        button.clicked.connect(change_server(dlg))
        dlg.exec()

    def check_connection_server(self):
        i = 0
        while True:
            try:
                requests.get("{}".format(self.__server))
                if i > 0:
                    msg = QMessageBox(QMessageBox.NoIcon, 'Соединение восстановлено', 'Соединение с сервером восстановлено')
                    msg.exec()
                break
            except (requests.exceptions.ConnectionError, requests.exceptions.InvalidURL,
                    requests.exceptions.InvalidSchema, requests.exceptions.MissingSchema):
                if i == 0:
                    msg = QMessageBox(QMessageBox.NoIcon, 'Соединение с сервером не установлено', 'Сервер не отвечает')
                    msg.exec()
                    icon = QIcon('img/connection_lost.png')
                    self.tray.tray.setIcon(icon)
                    self.tray.window_notification.main_window.hide()
                    self.tray.setting.hide()
                    dlg = QDialog()
                    dlg.setStyleSheet('width:150px; height:15px;')
                    dlg.setWindowTitle("Нужно поменять сервер?")
                    button_accept = QPushButton("Да")

                    def func():
                        dlg.close()
                        self.window_change_server()
                    button_accept.clicked.connect(func)
                    button_reject = QPushButton("Нет")
                    button_reject.clicked.connect(lambda: dlg.close())
                    layout = QVBoxLayout(dlg)
                    content = QHBoxLayout()
                    content.addWidget(button_accept)
                    content.addWidget(button_reject)
                    layout.addLayout(content)
                    dlg.exec()
                i += 1

    def get_notifications(self):
        self.check_connection_server()
        response = requests.get("{}/api/v1/notifications?access_token={}".format(self.__server, self.__access_token))
        logging.debug("Получение новых сообщений")
        return response

    def get_issues(self):
        self.check_connection_server()
        response = requests.get('{}/api/v1/repos/issues/search?access_token={}&limit=100'.format(self.__server,
                                                                                                    self.__access_token))
        logging.debug("Получение задач")
        return response

    def get_repos_issues(self, repo, issues):
        self.check_connection_server()
        response = requests.get("{}/api/v1/repos/{}/issues/{}".format(self.__server, repo, issues))
        logging.debug("Получение информации о задачи в репозитории")
        return response

    def get_comment(self, comment):
        self.check_connection_server()
        response = requests.get("{}/api/v1/repos/VolodinMA/MyGitRepository/issues/comments/{}".format(self.__server,
                                                                                                            comment))
        logging.debug("Получение комментария")
        return response

    def get_user(self):
        self.check_connection_server()
        response = requests.get("{}/api/v1/user?access_token={}".format(self.__server, self.__access_token))
        logging.debug("Обращение к Api для получение информацию о своей учетной записи")
        return response

    def set_access_token(self, access_token):
        logging.debug("Перезапись токена доступа")
        self.__access_token = access_token

    @property
    def get_access_token(self):
        return self.__access_token

    @property
    def get_server(self):
        return self.__server

    def set_server(self, server):
        logging.debug("Перезапись адреса сервера: {}".format(server))
        self.__server = server


class Config:

    def __init__(self, name):
        logging.debug("Создание экземпляра класса - Config, имя конфига: {}".format(name))
        self.name = name
        if not (os.path.exists(name)):
            to_yaml = {"server": '', "token": '', "delay_notification": "45"}
            with open(name, 'w') as f_obj:
                yaml.dump(to_yaml, f_obj)

    def save_settings(self, dict_setting):
        logging.debug("Перезапись  настроек в конфигурационном файле, новые настройки: {}".format(str(dict_setting)))
        with open(self.name) as f_obj:
            to_yaml = yaml.load(f_obj, Loader=yaml.FullLoader)
        for key, value in dict_setting.items():
            to_yaml[key] = value
        with open(self.name, 'w') as f_obj:
            yaml.dump(to_yaml, f_obj)

    def get_settings(self):
        logging.debug("Получение данных из конфигурационого файла")
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
        to_yaml = self.tray_icon.config.get_settings()
        to_yaml['token'] = self.edit_token.toPlainText()
        self.tray_icon.api.set_access_token(to_yaml['token'])
        to_yaml['server'] = self.edit_server.toPlainText()
        if not(self.edit_delay_notification.toPlainText().isdigit()):
            self.edit_delay_notification.setText('45')
        if float(self.edit_delay_notification.toPlainText()) > 0:
            to_yaml['delay_notification'] = self.edit_delay_notification.toPlainText()
        self.tray_icon.api.set_server(to_yaml['server'])
        self.tray_icon.config.save_settings(to_yaml)
        self.tray_icon.constructor_menu()
        self.hide()


class TrayIcon:

    def __init__(self, icon, app):
        logging.debug("Создание экземпляра класса - TrayIcon")
        self.app = app
        self.tray = QSystemTrayIcon()
        self.tray.authorization = False
        self.tray.activated.connect(self.controller_tray_icon)
        self.name_icon = icon
        self.menu_items = []
        self.icon = QIcon(icon)
        self.tray.setIcon(self.icon)
        self.tray.setVisible(True)
        self.menu = QMenu()
        self.hint = ''
        self.notifications = []
        self.timer_constructor_menu = threading.Timer(3, self.constructor_menu)
        self.config = Config('conf.yaml')
        self.setting = Setting(self)
        read_data = self.config.get_settings()
        self.api = Api(read_data.get('server', ''), read_data.get('token', ''), self)
        self.window_notification = Notification(self.api, self)
        self.timer_animation = QtCore.QTimer()
        self.timer_animation.timeout.connect(self.animation)
        self.timer_subscribe_notifications = QtCore.QTimer()
        self.timer_subscribe_notifications.timeout.connect(self.subscribe_notification)

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
        logging.debug("Скачивание аватара пользователя.")
        response = self.api.get_user()
        resource = requests.get(json.loads(response.text)['avatar_url'])
        if not(os.path.exists('img')):
            os.mkdir('img')
        with open("img/{}.jpg".format(str(json.loads(response.text)['id'])), "wb") as out:
            out.write(resource.content)

    def animation(self):
        response = self.api.get_user()
        user = json.loads(response.text)
        if len(self.notifications) == 0:
            logging.debug("Закончить анимацию оповещения о новых сообщениях")
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
            self.window_notification.create_window_notification()
            self.window_notification.show()

    def controller_tray_icon(self, trigger):
        if trigger == 3 and self.tray.authorization:  # Левая кнопка мыши
            self.show_notification()
        if trigger == 1:  # Правая кнопка мыши
            self.tray.show()

    def set_icon(self, icon):
        logging.debug("Установление изображение для TrayIcon, путь до картинки: {}".format(icon))
        self.name_icon = icon
        self.icon = QIcon(icon)
        self.tray.setIcon(self.icon)

    def authentication_successful(self, response):
        self.tray.authorization = True
        logging.debug("TrayIcon: Токен доступа действителен. Информация о пользователе: {}".format(response))
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
        logging.debug("TrayIcon: Создание контекстного меню для TrayIcon")
        response = self.api.get_user()
        name_aplication = QAction("Gitart")
        name_aplication.setEnabled(False)
        self.menu.addAction(name_aplication)
        self.menu_items.append(name_aplication)
        if response is None:
            logging.debug("response - пустой")
        else:
            if response.status_code == 200:
                self.authentication_successful(response)
            else:
                logging.debug("TrayIcon: Токена доступа нет или он недействителен")
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
        self.tray.authorization = False
        self.api.set_access_token(to_yaml['token'])
        self.config.save_settings(to_yaml)
        self.set_icon('img/dart.png')
        self.constructor_menu()


def main():
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    myappid = 'myproduct'
    QtWin.setCurrentProcessExplicitAppUserModelID(myappid)
    sys.excepthook = crash_script
    current_date = datetime.datetime.today().strftime('%d-%m-%Y')
    format_logging = '%(asctime)s   %(levelname)-10s   %(message)s'
    logging.basicConfig(filename="logs/Debug-{}.log".format(current_date),
                        level=logging.DEBUG, format=format_logging, datefmt='%H:%M:%S')
    if not (os.path.exists('logs')):
        os.mkdir('logs')
    logging.info("Запуск программы")
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('./img/logo.svg'))
    app.setQuitOnLastWindowClosed(False)
    tray_icon = TrayIcon('img/dart.png', app)
    tray_icon.constructor_menu()
    app.exec_()


if __name__ == '__main__':
    main()
