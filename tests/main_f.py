import pytest
import sys
import json
sys.path.append('../')
import main
import my_sql_lite


# Передаю токен пользователя имеющий id - 2 и сервер, ожидаю что вернется  пользователь имеющий id - 2.
def test_formatting_the_date_correct_input():
    my_date = main.formatting_the_date('2022-01-21T08:03:40Z')
    assert str(my_date) == '2022-01-21 13:03:40'


def test_formatting_the_date_incorrect_input():
    my_date = main.formatting_the_date('null')
    assert str(my_date) == ''


def test_get_assigned_to_you():
    all_tasks = json.loads('[{"assignees": [{"login": "qwerty"}]}, {"id": 3, "assignees":null}]')
    login = json.loads('{"login": "qwerty"}')
    result = main.filter_assigned_you_task(all_tasks, login)
    assert result == json.loads('[{"assignees": [{"login": "qwerty"}]}]')


def test_save_notifications():
    api = main.Api(None, 'http://server300:1080', 'd9661f3c1780c0fe5ffbf07a17b945ce07486b7e')
    notifications = json.loads(api.get_notifications().text)
    table = my_sql_lite.Notifications('test.db')
    table.clear()

    main.save_notifications(api, notifications, table)
    assert table.get_all()[0]['message'] == 'fasfasfa'
