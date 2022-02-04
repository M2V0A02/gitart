import pytest
import sys
import json
sys.path.append('../')
import main


class TestApi:

    def test_get_user_user_received(self):
        api = main.Api('server300:1080', '9e8eab4fad52b94c1f57217e2cdfeea5a99229d7')
        user = api.get_user()
        user_json = json.loads(user.text)
        assert user_json['id'] == 2

    