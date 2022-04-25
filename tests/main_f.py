import pytest
import sys
import json
sys.path.append('../')
import main
import my_sql_lite


class Response:
    def __init__(self, text):
        self.text = text


# Передаю токен пользователя имеющий id - 2 и сервер, ожидаю что вернется  пользователь имеющий id - 2.
def test_formatting_the_date_correct_input():
    my_date = '2022-01-21T08:03:40Z'

    my_date = main.formatting_the_date(my_date)

    assert str(my_date) == '2022-01-21 13:03:40'


def test_formatting_the_date_incorrect_input():
    my_date = 'null'

    my_date = main.formatting_the_date(my_date)

    assert str(my_date) == ''


def test_get_assigned_to_you():
    all_tasks = json.loads('[{"assignees": [{"login": "qwerty"}]}, {"id": 3, "assignees":null}]')
    login = json.loads('{"login": "qwerty"}')

    result = main.filter_assigned_you_task(all_tasks, login)

    assert result == json.loads('[{"assignees": [{"login": "qwerty"}]}]')


def test_save_notifications():
    api = main.Api(None, '', '')
    api.get_comment = lambda comment_id: Response('{"body": "test"}')
    api.get_repos_issues = lambda repo, issues: Response('{"user": {"login": "qwerty"}}')
    notifications = json.loads('[{"repository": {"full_name": "my_repo", "owner": {"created": "2022-01-21T08:03:40Z"}},'
                               ' "subject": {"latest_comment_url": "http://test.ru/comments/1",'
                               ' "url": "http://server300:1080/api/v1/repos/VolodinMA/MyGitRepositor/issues/39"}}]')

    table = my_sql_lite.Notifications()
    table.clear()

    main.save_notifications(api, notifications, table)
    assert table.get_all()[0]['message'] == 'test'
    assert table.get_all()[0]['user_login'] == 'qwerty'
    assert table.get_all()[0]['full_name'] == 'my_repo'
    assert table.get_all()[0]['created_time'] == '2022-01-21 13:03:40'
    assert table.get_all()[0]['url'] == 'http://server300:1080/api/v1/repos/VolodinMA/MyGitRepositor/issues/39'
    table.clear()
