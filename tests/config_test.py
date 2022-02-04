import pytest
import os
import sys
import yaml
sys.path.append('../')
import main


class TestConfig:
    def test_init_create_config_config_create_successful(self):
        self.name = 'test.yaml'
        config = main.Config(self.name)
        assert os.path.exists(self.name) == True
        os.remove(self.name)

    def test_get_settings_settings_received(self):
        self.name = 'test.yaml'
        config = main.Config(self.name)
        from_yaml_test = config.get_settings()
        with open(self.name) as f_obj:
            from_yaml = yaml.load(f_obj, Loader=yaml.FullLoader)
        os.remove(self.name)
        assert from_yaml_test == from_yaml

    def test_save_setting_setting_saved(self):
        self.name = 'test.yaml'
        config = main.Config(self.name)
        config.save_settings({"server": 'server300:1090', "token": 'qwerty'})
        with open(self.name) as f_obj:
            from_yaml = yaml.load(f_obj, Loader=yaml.FullLoader)
        os.remove(self.name)
        assert [from_yaml['server'], from_yaml['token']] == ['server300:1090', 'qwerty']

    def test_init_file_overwrite_file_is_not_overwritten(self):
        self.name = 'test.yaml'
        with open(self.name, 'w') as f_obj:
            yaml.dump({"server": 'server300:1090', "token": 'qwerty'}, f_obj)
        config = main.Config(self.name)
        with open(self.name) as f_obj:
            from_yaml = yaml.load(f_obj, Loader=yaml.FullLoader)
        os.remove(self.name)
        assert [from_yaml['server'], from_yaml['token']] == ['server300:1090', 'qwerty']
