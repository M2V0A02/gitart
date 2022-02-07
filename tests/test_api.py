import pytest
import sys
import json
sys.path.append('../')
import main


class TestApi:
    def test__init__creation_successfully(self):
        main.Api('server300:1080', '9e8eab4fad52b94c1f57217e2cdfeea5a99229d7')
        assert True

    def test_get_user_user_received(self):
        api = main.Api('server300:1080', '9e8eab4fad52b94c1f57217e2cdfeea5a99229d7')
        user = api.get_user()
        user_json = json.loads(user.text)
        assert user_json['id'] == 2

    def test_set_server_server_received(self):
        api = main.Api('server300:1080', '9e8eab4fad52b94c1f57217e2cdfeea5a99229d7')
        api.set_server('server300:1090')
        assert api.get_server() == 'server300:1090'

    def test_set_access_token_access_token_received(self):
        api = main.Api('server300:1080', '123')
        api.set_access_token('qwerty')
        assert api.get_access_token() == 'qwerty'
