import io

import pytest

from scr.models.goods import Good
from scr.parsers.parsers import ParserCsv


@pytest.fixture
def valid_csv_file():
    return io.StringIO(
        'name,brand,price,rating\n'
        'iphone 15 pro,apple,999,4.9\n'
        'galaxy s23 ultra,samsung,1199,4.8\n'

    )


def test_parser_valid_data(valid_csv_file):
    parser = ParserCsv(valid_csv_file)
    assert parser.parse_data() == [
        Good(
            name='iphone 15 pro',
            brand='apple',
            price=999,
            rating=4.9
        ),
        Good(
            name='galaxy s23 ultra',
            brand='samsung',
            price=1199,
            rating=4.8
        ),
    ]


@pytest.mark.parametrize(
    "csv_content, expected_result, expected_message",
    [
        (
            "name,brand,cost,rating\niphone 15 pro,apple,999,4.9\n",
            None,  # Для проверки исключения
            "Отсутствуют обязательные поля в CSV: {'price'}"
        ),
        (
            "name,brand,price,rating\niphone 15 pro,apple,,4.9\n",
            [],  # Пустой список, так как строка пропущена
            "Пропущена строка 2: Одно или несколько обязательных полей пусты"
        ),
        (
            "name,brand,price,rating\niphone 15 pro,apple,invalid,4.9\n",
            [],  # Пустой список, так как строка пропущена
            "Пропущена строка 2: invalid literal for int() with base 10: "
            "'invalid'"
        ),
    ]
)
def test_parse_data_errors(
        csv_content,
        expected_result,
        expected_message,
        capsys):
    csv_file = io.StringIO(csv_content)
    parser = ParserCsv(csv_file)
    if expected_result is None:  # Проверка исключения
        with pytest.raises(ValueError, match=expected_message):
            parser.parse_data()
    else:  # Проверка результата и вывода
        result = parser.parse_data()
        captured = capsys.readouterr()
        assert result == expected_result
        assert expected_message in captured.out
