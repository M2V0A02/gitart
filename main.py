import time
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
from PyQt5.QtWinExtras import QtWin


def crash_script(error_type, value, tb):
    traces = traceback.extract_tb(tb)
    critical_error = "{}: {},  \n".format(error_type, value)
    indent_format = 24
    for frame_summary in traces:
        critical_error += "{}File '{}', line {}, in {}, \n{} {} \n".format(" " * indent_format, frame_summary.filename,
                                                                           frame_summary.lineno,
                                                                           frame_summary.name, " " * indent_format,
                                                                           frame_summary.line)
    logging.critical(critical_error)
    sys.__excepthook__(error_type, value, tb)


def cut_the_string(string, length):
    if len(string) < 3:
        return string
    if len(string) > length:
        string = '{}...'.format(string[0:length - 3])
    return string


class Notification:
    def __init__(self, api, tray):
        self.tray = tray
        self.main_window = QMainWindow()
        self.scroll = QScrollArea(self.main_window)
        self.main_window.setFixedSize(830, 830)
        self.main_window.setWindowTitle("Новые сообщения")
        self.window = QWidget()
        self.timer_change_button_text = QtCore.QTimer()
        icon = QIcon('img/logo.svg')
        self.main_window.setWindowIcon(icon)
        self.layout = QVBoxLayout()
        self.ui = []
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
        if number_tab == 0:
            self.create_window_notification()
        if number_tab == 1:
            self.create_window_tasks()

    def create_window_tasks(self):
        widget = QWidget()
        main_layout = QVBoxLayout()
        layout = QHBoxLayout()
        issues = json.loads(self.api.get_issues().text)
        user = json.loads(self.api.get_user().text)
        i = 0
        while i < len(issues):
            is_delete = True
            if not (issues[i]['assignees'] is None):
                for j in range(len(issues[i]['assignees'])):
                    if issues[i]['assignees'][j]['login'] == user['login']:
                        is_delete = False
            if is_delete:
                issues.pop(i)
                i = i - 1
            i += 1
        label = QLabel('Вам назначено - {} задач.'.format(len(issues)))
        label.setStyleSheet("font-size:24px;")
        button = QPushButton("Обновить")
        button.clicked.connect(self.create_window_tasks)
        layout.addWidget(label)
        layout.addWidget(button)
        main_layout.addLayout(layout)
        number_of_messages_per_line = 2
        layout_message = QHBoxLayout()
        y = 1
        for i in range(len(issues)):
            label = QLabel(cut_the_string(issues[i]['title'], 50))
            label.setStyleSheet("font-size:18px;")
            div = QWidget()
            layout = QVBoxLayout(div)
            div.setStyleSheet("margin-left:15px; width:345px;")
            layout.addWidget(label)
            self.ui.append(label)
            task_id = re.search(r'/issues/.+', issues[i]['url'])[0].replace('/issues/', '')
            body = cut_the_string("{}#{} открыта {} {}.".format(issues[i]['repository']['full_name'],
                                                                task_id, self.formatting_the_date(issues[i]['created_at']).strftime('%d-%m-%Y'),
                                                                issues[i]['user']['login']), 60)
            label = QLabel(body)
            label.setStyleSheet("font-size:12px;")
            layout.addWidget(label)
            if not(issues[i]['milestone'] is None):
                label = QLabel(cut_the_string("Этап: {}".format(issues[i]['milestone']['title']), 50))
                layout.addWidget(label)
            button = QPushButton("Перейти в {}".format(issues[i]['html_url'].replace("http://", '')))
            open_tasks = self.open_url(issues[i]['html_url'])
            button.clicked.connect(open_tasks)
            button.setStyleSheet(
                "font-size:12px; color: #23619e; background: rgba(255,255,255,0);"
                "border-radius: .28571429rem; height: 20px; border-color: #dedede; text-align:left")
            self.ui.append(button)
            layout.addWidget(button)
            layout_message.addWidget(div)
            y = i
            if (i + 1) % number_of_messages_per_line == 0:
                main_layout.addLayout(layout_message)
                layout_message = QHBoxLayout()
        if not(y + 1 % number_of_messages_per_line == 0):
            main_layout.addLayout(layout_message)
        main_layout.addStretch()
        widget.setLayout(main_layout)
        self.tasks_scroll_area.setWidget(widget)
        self.tab_widget.update()

    def get_additional_information(self, notifications):
        addititonal_information = dict()
        if not (notifications['subject']['latest_comment_url'] == ''):
            id_comments = re.search(r'comments/\d+', format(notifications['subject']
                                                            ['latest_comment_url']))[0].replace('comments/', '')
            addititonal_information['body'] = (json.loads(self.api.get_comment(id_comments).text)['body'])
        if not(notifications['subject']['url'] == ''):
            repo = re.search(r'repos/.+/issues', notifications['subject']['url'])[0].replace('repos/', '').replace(
                '/issues', '')
            issues = re.search(r'/issues/.+', notifications['subject']['url'])[0].replace('/issues/', '')
            notification = json.loads(self.api.get_repos_issues(repo, issues).text)
            addititonal_information['user_login'] = (notification['user']['login'])
        return addititonal_information

    def formatting_the_date(self, date):
        date = datetime.datetime.strptime(date, '%Y-%m-%dT%H:%M:%SZ')
        timezone = str(datetime.datetime.now(datetime.timezone.utc).astimezone())
        timezone = int(timezone[len(timezone) - 5:len(timezone) - 3])
        date = date + datetime.timedelta(hours=timezone)
        return date

    def show_notifications(self, notifications, main_layout):
        for i in range(len(notifications)):
            additional_information = self.get_additional_information(notifications[i])
            repo = notifications[i]['repository']['full_name']
            created_time = str(self.formatting_the_date(notifications[i]['repository']['owner']['created']))
            text_title = 'Репозиторий: {}, время создания: {}'.format(repo, created_time)
            if 'user_login' in additional_information:
                text_title = cut_the_string("{}, пользователь - {}.".format(text_title,
                                                                            additional_information['user_login']), 130)
            label = QLabel(text_title)
            label.setStyleSheet("font-size:12px;")
            main_layout.addWidget(label)
            self.ui.append(label)
            if 'body' in additional_information:
                plain_text = QPlainTextEdit('Сообщение: {}.'.format(additional_information['body']))
                plain_text.setReadOnly(True)
                plain_text.setFixedSize(740, 75)
                main_layout.addWidget(plain_text)
                self.ui.append(plain_text)
            open_notification = self.open_url(notifications[i]['subject']['url'].replace('api/v1/repos/', ''))
            number_issues = re.search(r'issues/\d+', notifications[i]['subject']['url'])[0].replace('issues/', '')
            button = QPushButton("Перейти в - {}/issues/{} ".format(notifications[i]['repository']['full_name'],
                                                                    number_issues))
            button.setStyleSheet(
                "font-size:12px; color: #23619e; background: rgba(255,255,255,0); border-radius:"
                " .28571429rem; height: 20px; border-color: #dedede; text-align:right;")
            button.clicked.connect(open_notification)
            main_layout.addWidget(button)
            self.ui.append(button)

    def create_window_notification(self):
        notifications = json.loads(self.api.get_notifications().text)
        widget = QWidget()
        main_layout = QVBoxLayout()
        layout = QHBoxLayout()
        label = QLabel("Не прочитано - {} сообщений.".format(len(notifications)))
        label.setStyleSheet("font-size:24px;")
        layout.addWidget(label)
        self.update_button = QPushButton("Обновить")
        self.update_button.setStyleSheet("max-width:75px; min-width:75px;")
        self.update_button.clicked.connect(self.update_notifications)
        layout.addWidget(self.update_button)
        main_layout.addLayout(layout)
        self.ui.append(label)
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
        self.timer_change_button_text.timeout.connect(lambda: self.update_button.setText('Обновить'))
        self.create_window_notification()
        self.update_button.setText("Обновление")
        self.timer_change_button_text.start(500)

    def open_url(self, url):
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
        return requests.get('http://{}/api/v1/repos/issues/search?access_token={}&limit=100'.format(self.server,
                                                                                                    self.access_token))

    def get_repos_issues(self, repo, issues):
        logging.debug("Получение информации о задачи в репозитории.")
        return requests.get("http://{}/api/v1/repos/{}/issues/{}".format(self.server, repo, issues))

    def get_comment(self, comment):
        logging.debug("Получение  комментария")
        return requests.get("http://{}/api/v1/repos/VolodinMA/MyGitRepository/issues/comments/{}".format(self.server,
                                                                                                         comment))

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
            logging.error('Server - пустой, url - {}'.format("http://{}/api/v1/user?access_token={}"
                                                             .format(self.server, self.access_token)))
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
        self.window_notification = Notification(self.api, self)
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
            self.window_notification.create_window_notification()
            self.window_notification.show()

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


def main():
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
    tray_icon = TrayIcon('img/icon.png', app)
    app.exec_()


if __name__ == '__main__':
    main()
