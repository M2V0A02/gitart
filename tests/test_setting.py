import pytest
import sys
import yaml
from PyQt5.QtWidgets import *
sys.path.append('../')
import main


def test__init__creation_successfully():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    tray_icon = main.TrayIcon('../img/icon.png', app)
    setting = main.Setting(tray_icon)
    assert True


def test_save_settings_settings_saved():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    tray_icon = main.TrayIcon('../img/icon.png', app)
    with open('conf.yaml') as f_obj:
        read_data = yaml.load(f_obj, Loader=yaml.FullLoader)
    read_data['server'] = 'server300:1090'
    read_data['token'] = ''
    with open('conf.yaml', 'w') as f_obj:
        yaml.dump(read_data, f_obj)
    setting = main.Setting(tray_icon)
    setting.edit_token.setText('12345')
    setting.edit_server.setText('server300:1080')
    setting.save_settings()
    with open('conf.yaml') as f_obj:
        read_data = yaml.load(f_obj, Loader=yaml.FullLoader)
    assert ((read_data['server'] == 'server300:1080') and (read_data['token'] == '12345'))
