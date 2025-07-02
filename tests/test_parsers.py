import io
from unittest.mock import MagicMock

import pytest

from scr.parsers.parsers import ParserCsv


@pytest.fixture
def valid_csv_file():
    return io.StringIO(
        'name,brand,price,rating,stock\n'
        'iphone 15 pro,apple,999.0,4.9,10.0\n'
        'galaxy s23 ultra,samsung,1199.0,4.8,5.0\n'
    )


def test_parser_valid_data(valid_csv_file):
    parser = ParserCsv(valid_csv_file)
    goods, field_types = parser.parse_data()
    assert len(goods) == 2
    assert goods[0].__dict__ == {
        'name': 'iphone 15 pro',
        'brand': 'apple',
        'price': 999.0,
        'rating': 4.9,
        'stock': 10.0
    }
    assert goods[1].__dict__ == {
        'name': 'galaxy s23 ultra',
        'brand': 'samsung',
        'price': 1199.0,
        'rating': 4.8,
        'stock': 5.0
    }
    assert field_types == {
        'name': str,
        'brand': str,
        'price': float,
        'rating': float,
        'stock': float
    }


@pytest.mark.parametrize(
    'csv_content, expected_result, expected_message',
    [
        (
                'name,brand,price,rating,stock\n,,999.0,4.9,10.0\n',
                (
                        [MagicMock()],
                        {'name': str, 'brand': str, 'price': float, 'rating': float, 'stock': float}
                ),
                '',
        ),
        (
                'name,brand,price,rating,stock\niphone 15 pro,apple,invalid,4.9,10.0\n',
                (
                        [MagicMock()],
                        {'name': str, 'brand': str, 'price': str, 'rating': float, 'stock': float}
                ),
                '',
        ),
        (
                '\n',
                None,  # Ожидаем исключение
                'CSV-файл не содержит заголовков',
        ),
    ]
)
def test_parse_data_errors(csv_content, expected_result, expected_message, capsys):
    csv_file = io.StringIO(csv_content)
    parser = ParserCsv(csv_file)

    # Настраиваем MagicMock для каждого случая
    if expected_result is not None:
        if csv_content.startswith('name,brand,price,rating,stock\n,,999.0'):
            expected_result[0][0].configure_mock(
                __dict__={'name': '', 'brand': '', 'price': 999.0, 'rating': 4.9, 'stock': 10.0})
        elif csv_content.startswith('name,brand,price,rating,stock\niphone 15 pro'):
            expected_result[0][0].configure_mock(
                __dict__={'name': 'iphone 15 pro', 'brand': 'apple', 'price': 'invalid', 'rating': 4.9, 'stock': 10.0})

    if expected_result is None:
        with pytest.raises(ValueError, match=expected_message):
            parser.parse_data()
    else:
        result = parser.parse_data()
        captured = capsys.readouterr()
        assert [item.__dict__ for item in result[0]] == [item.__dict__ for item in expected_result[0]]
        assert result[1] == expected_result[1]
        assert captured.out.strip() == expected_message
