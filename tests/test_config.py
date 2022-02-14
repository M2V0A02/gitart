import pytest
import os
import sys
import yaml
sys.path.append('../')
import main


# Проверяю что создается конфиг файл
def test_init_create_config_config_create_successful():
    name = 'test.yaml'
    if os.path.exists(name):
        os.remove(name)
    config = main.Config(name)
    assert os.path.exists(name)
    os.remove(name)


# Проверяю что данные полученные с помощью функции get_settings() у класса конфиг выдает все параметры правильно
def test_get_settings_settings_received():
    name = 'test.yaml'
    config = main.Config(name)
    from_yaml_test = config.get_settings()
    with open(name) as f_obj:
        from_yaml = yaml.load(f_obj, Loader=yaml.FullLoader)
    os.remove(name)
    assert from_yaml_test == from_yaml


# Проверяю что данные сохраняются в конфиг файл
def test_save_setting_setting_saved():
    name = 'test.yaml'
    config = main.Config(name)
    config.save_settings({"server": 'server300:1090', "token": 'qwerty'})
    with open(name) as f_obj:
        from_yaml = yaml.load(f_obj, Loader=yaml.FullLoader)
    os.remove(name)
    assert [from_yaml['server'], from_yaml['token']] == ['server300:1090', 'qwerty']


# Проверяю что файл не перезаписывается, если существует
def test_init_file_overwrite_file_is_not_overwritten():
    name = 'test.yaml'
    with open(name, 'w') as f_obj:
        yaml.dump({"server": 'server300:1090', "token": 'qwerty'}, f_obj)
    config = main.Config(name)
    with open(name) as f_obj:
        from_yaml = yaml.load(f_obj, Loader=yaml.FullLoader)
    os.remove(name)
    assert [from_yaml['server'], from_yaml['token']] == ['server300:1090', 'qwerty']
