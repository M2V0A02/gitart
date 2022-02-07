import pytest
import sys
import json
import yaml
from PyQt5.QtWidgets import *
sys.path.append('../')
import main


# провер€ю что функци€ logout очищает токен
def test__logout_logout_successful():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    tray_icon = main.TrayIcon('../img/icon.png', app)
    with open('conf.yaml') as f_obj:
        return_data = yaml.load(f_obj, Loader=yaml.FullLoader)
    return_data['token'] = '12345'
    with open('conf.yaml', 'w') as f_obj:
        yaml.dump(return_data, f_obj)
    tray_icon.logout()
    with open('conf.yaml') as f_obj:
        return_data = yaml.load(f_obj, Loader=yaml.FullLoader)
    assert return_data['token'] == ''
