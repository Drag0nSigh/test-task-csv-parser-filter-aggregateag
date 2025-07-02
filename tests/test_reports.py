import re
from unittest.mock import MagicMock

import pytest

from scr.reports.reports import Aggregator, Filter, Report, Sorter


@pytest.fixture
def mock_field_types():
    return {
        'name': str,
        'brand': str,
        'price': float,
        'rating': float,
        'stock': float
    }


@pytest.fixture
def mock_goods():
    good1 = MagicMock()
    good1.__dict__ = {'name': 'iphone', 'brand': 'apple', 'price': 100.0, 'rating': 4.9, 'stock': 10.0}
    good2 = MagicMock()
    good2.__dict__ = {'name': 'samsung', 'brand': 'samsung', 'price': 200.0, 'rating': 4.6, 'stock': 5.0}
    good3 = MagicMock()
    good3.__dict__ = {'name': 'xiaomi', 'brand': 'xiaomi', 'price': 150.0, 'rating': 4.8, 'stock': 8.0}
    return [good1, good2, good3]


@pytest.mark.parametrize(
    'condition, expected_result',
    [
        (
            'brand=xiaomi',
            [{'name': 'xiaomi', 'brand': 'xiaomi', 'price': 150.0, 'rating': 4.8, 'stock': 8.0}]
        ),
        (
            'price>170',
            [{'name': 'samsung', 'brand': 'samsung', 'price': 200.0, 'rating': 4.6, 'stock': 5.0}]
        ),
        (
            'rating<4.7',
            [{'name': 'samsung', 'brand': 'samsung', 'price': 200.0, 'rating': 4.6, 'stock': 5.0}]
        ),
    ]
)
def test_filter_goods(condition, expected_result, mock_goods, mock_field_types):
    filter_instance = Filter(mock_goods, mock_field_types)
    result = filter_instance.filter_goods(condition)

    # Настраиваем MagicMock для ожидаемого результата
    expected_mocks = [MagicMock() for _ in expected_result]
    for mock, attrs in zip(expected_mocks, expected_result):
        mock.configure_mock(__dict__=attrs)
    assert [item.__dict__ for item in result] == [item.__dict__ for item in expected_mocks]


@pytest.mark.parametrize(
    'field, operation, expected_result',
    [
        (
            'price', 'min',
            100.0
        ),
        (
            'rating', 'max',
            4.9
        ),
        (
            'price', 'avg',
            150.0
        ),
    ]
)
def test_calculate_aggregation(field, operation, expected_result, mock_goods, mock_field_types):
    aggregator = Aggregator(mock_goods, mock_field_types)
    result = aggregator.calculate_aggregation(field, operation)
    assert result == expected_result


@pytest.mark.parametrize(
    'field, order, expected_result',
    [
        (
            'price', 'asc',
            [
                {'name': 'iphone', 'brand': 'apple', 'price': 100.0, 'rating': 4.9, 'stock': 10.0},
                {'name': 'xiaomi', 'brand': 'xiaomi', 'price': 150.0, 'rating': 4.8, 'stock': 8.0},
                {'name': 'samsung', 'brand': 'samsung', 'price': 200.0, 'rating': 4.6, 'stock': 5.0},
            ]
        ),
        (
            'brand', 'desc',
            [
                {'name': 'xiaomi', 'brand': 'xiaomi', 'price': 150.0, 'rating': 4.8, 'stock': 8.0},
                {'name': 'samsung', 'brand': 'samsung', 'price': 200.0, 'rating': 4.6, 'stock': 5.0},
                {'name': 'iphone', 'brand': 'apple', 'price': 100.0, 'rating': 4.9, 'stock': 10.0},
            ]
        ),
    ]
)
def test_sort_goods(field, order, expected_result, mock_goods, mock_field_types):
    sorter = Sorter(mock_goods, mock_field_types)
    result = sorter.sort_goods(field, order)

    # Настраиваем MagicMock для ожидаемого результата
    expected_mocks = [MagicMock() for _ in expected_result]
    for mock, attrs in zip(expected_mocks, expected_result):
        mock.configure_mock(__dict__=attrs)
    assert [item.__dict__ for item in result] == [item.__dict__ for item in expected_mocks]

@pytest.mark.parametrize(
    'condition, expected_result, expected_message',
    [
        (
            'brand=xiaomi;rating>=4.8|price<=500',
            [[('brand', '=', 'xiaomi'), ('rating', '>=', 4.8)], [('price', '<=', 500.0)]],
            ''
        ),
        (
            'brand=xiaomi|price<=500',
            [[('brand', '=', 'xiaomi')], [('price', '<=', 500.0)]],
            ''
        ),
        (
            'rating>=4.8;price<=500',
            [[('rating', '>=', 4.8), ('price', '<=', 500.0)]],
            ''
        ),
        (
            '',
            [[]],
            'Условие не может быть пустым'
        ),
        (
            'brand+iphone',
            [[]],
            re.escape('Неверный формат условия: brand+iphone')
        ),
        (
            'goods=iphone',
            [[]],
            re.escape('Поле "goods" отсутствует в данных')
        ),
        (
            'brand>iphone',
            [[]],
            re.escape('Для строкового поля "brand" поддерживаются только операторы = и !=')
        ),
        (
            'price>iphone',
            [[]],
            re.escape('Для числового поля "price" ожидается числовое значение, получено: iphone')
        ),
        (
            ' ; | ;',
            [[]],
            re.escape('Не найдено ни одного валидного условия')
        ),

    ]

)
def test_valid_filter_parse_condition(condition, expected_result, expected_message, mock_field_types):
    if expected_result == [[]]:
        with pytest.raises(ValueError, match=expected_message):
            Report._parse_condition(condition, mock_field_types)
    else:
        result = Report._parse_condition(condition, mock_field_types)
        assert result == expected_result


@pytest.mark.parametrize(
    'field, operator, value, result',
    [
        ('name', '=', 'iphone', True),
        ('brand', '!=', 'xiaomi', True),
        ('price', '=', 100, True),
        ('rating', '!=', 4.8, True),
        ('price', '>', 10, True),
        ('price', '>=', 100, True),
        ('rating', '<', 4.99, True),
        ('rating', '<=', 4.9, True),
        ('name', '=', '1iphone', False),
        ('brand', '!=', 'apple', False),
        ('price', '=', 1000, False),
        ('rating', '!=', 4.9, False),
        ('price', '>', 100, False),
        ('price', '>=', 1000, False),
        ('rating', '<', 4.7, False),
        ('rating', '<=', 4.7, False),

    ]
)
def test_valid_filter_compare(field, operator, value, result, mock_goods):
    good = mock_goods[0]  # Берем первый товар (iphone)
    assert Report._compare(good, field, operator, value) is result


# def test_not_valid_method_aggregation(valid_list_goods):
#     aggregation = Filter(valid_list_goods)
#     assert (aggregation.calculate_aggregation('price', 'maxx') is
#             None)
