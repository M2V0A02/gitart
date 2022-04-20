import pytest
import sys
import json
sys.path.append('../')
import main


# Передаю токен пользователя имеющий id - 2 и сервер, ожидаю что вернется  пользователь имеющий id - 2.
def test_formatting_the_date_correct_input():
    my_date = main.DB().formatting_the_date('2022-01-21T08:03:40Z')
    assert str(my_date) == '2022-01-21 13:03:40'


def test_formatting_the_date_incorrect_input():
    my_date = main.DB().formatting_the_date('null')
    assert str(my_date) == ''
