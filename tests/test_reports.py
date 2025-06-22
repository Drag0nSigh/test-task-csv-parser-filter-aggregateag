import re

import pytest

from scr.models.goods import Good
from scr.reports.reports import Filter
from tests.conftest import valid_good, valid_list_goods


@pytest.mark.parametrize(
    'method, param_method, expected_result',
    [
        (
                Filter.filter_goods,
                'brand=xiaomi',
                [
                    Good(
                        name='xiaomi',
                        brand='xiaomi',
                        price=150,
                        rating=4.8
                    ),
                ]

        ),
        (
                Filter.filter_goods,
                'price>170',
                [
                    Good(
                        name='samsung',
                        brand='samsung',
                        price=200,
                        rating=4.6
                    ),
                ]

        ),
        (
                Filter.filter_goods,
                'rating<4.7',
                [
                    Good(
                        name='samsung',
                        brand='samsung',
                        price=200,
                        rating=4.6
                    ),
                ]

        ),
        (
                Filter.calculate_aggregation,
                ('price', 'min'),
                100
        ),
        (
                Filter.calculate_aggregation,
                ('rating', 'max'),
                4.9
        ),
        (
                Filter.calculate_aggregation,
                ('price', 'avg'),
                150
        ),
        (
                Filter.sort_goods,
                ('price', 'asc'),
                [
                    Good(
                        name='iphone',
                        brand='apple',
                        price=100,
                        rating=4.9
                    ),
                    Good(
                        name='xiaomi',
                        brand='xiaomi',
                        price=150,
                        rating=4.8
                    ),
                    Good(
                        name='samsung',
                        brand='samsung',
                        price=200,
                        rating=4.6
                    ),
                ]
        ),
        (
                Filter.sort_goods,
                ('brand', 'desc'),
                [
                    Good(
                        name='xiaomi',
                        brand='xiaomi',
                        price=150,
                        rating=4.8
                    ),
                    Good(
                        name='samsung',
                        brand='samsung',
                        price=200,
                        rating=4.6
                    ),
                    Good(
                        name='iphone',
                        brand='apple',
                        price=100,
                        rating=4.9
                    ),
                ]
        )
    ]
)
def test_filter_valid_method_filter_aggr(
        valid_list_goods,
        method,
        param_method,
        expected_result):
    report = Filter(valid_list_goods)
    if method == Filter.filter_goods:
        assert method(report, param_method) == expected_result
    else:
        assert method(report, *param_method) == expected_result


def test_valid_filter_parse_condition():
    assert (Filter._parse_condition('brand=xiaomi;rating>=4.8|price<=500') ==
            [[("brand", "=", "xiaomi"), ("rating", ">=", 4.8)],
             [("price", "<=", 500)]]
            )


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
def test_valid_filter_compare(
        valid_good,
        field,
        operator,
        value,
        result
):
    assert Filter._compare(valid_good, field, operator, value) is result


def test_not_valid_filter_compare(valid_good):
    with pytest.raises(
            ValueError,
            match='Для поля name поддерживаются только операторы = и !='
    ):
        Filter._compare(valid_good, 'name', '>', 'iphone')


def test_not_valid_method_aggregation(valid_list_goods):
    aggregation = Filter(valid_list_goods)
    assert (aggregation.calculate_aggregation('price', 'maxx') is
            None)


@pytest.mark.parametrize(
    'conditions, expected_message',
    [
        ('', 'Условие не может быть пустым'),
        ('name+iphone', re.escape('Неверный формат условия: name+iphone')),
        ('cost=100',
         re.escape("Недопустимое поле: cost. Допустимые поля: "
                   "['name', 'brand', 'price', 'rating']")),
        ('price=big', 'Для поля price ожидается числовое значение, '
                      'получено: big'),
        (' ; | ; ', 'Не найдено ни одного валидного условия')

    ]
)
def test_not_valid_parse_condition(conditions, expected_message):
    with pytest.raises(ValueError, match=expected_message):
        Filter._parse_condition(conditions)
