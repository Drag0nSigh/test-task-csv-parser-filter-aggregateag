import io
import re
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

from scr.main import (ValidateFilesAction, main, print_table, save_json,
                      validate_aggregate, validate_order_by)


class MockGood:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


@pytest.fixture
def mock_parser():
    """
    Создаёт мок-объект парсера.

    Мок-объект парсера с настроенным методом error, вызывающим SystemExit.
    """
    parser = Mock()
    parser.error.side_effect = SystemExit
    return parser


@pytest.fixture
def mock_namespace():
    """Создаёт мок-объект пространства имён."""
    return Mock()


@pytest.fixture
def mock_field_types():
    """Типы данных для класса Good."""
    return {
        'name': str,
        'brand': str,
        'price': float,
        'rating': float,
        'stock': float
    }


@pytest.fixture
def mock_goods():
    """Объекты для отчёта."""
    return [
        MockGood(
            name='iphone',
            brand='apple',
            price=100.0,
            rating=4.9,
            stock=10.0
        ),
        MockGood(
            name='samsung',
            brand='samsung',
            price=200.0,
            rating=4.6,
            stock=5.0
        ),
        MockGood(
            name='xiaomi',
            brand='xiaomi',
            price=150.0,
            rating=4.8,
            stock=8.0
        )
    ]


@pytest.mark.parametrize(
    'aggregate, field_types, expected_message',
    [
        (
            '',
            {'price': float},
            'Аргумент --aggregate не может быть пустым'
        ),
        (
            'gh=gh',
            {'price': float},
            'Неверный формат агрегации: должен быть "field=operation", '
            'где operation в ["avg", "min", "max"]'),
        (
            'unknown=avg',
            {'price': float},
            'Поле "unknown" отсутствует в данных'),
        (
            'brand=avg',
            {'brand': str, 'price': float},
            'Агрегация возможна только для числовых полей, "brand" '
            'имеет тип <class \'str\'>'),
    ]
)
def test_not_valid_validate_aggregate(
        aggregate,
        field_types,
        expected_message
):
    """Тест не валидных данных для агрегации."""
    with pytest.raises(ValueError, match=re.escape(expected_message)):
        validate_aggregate(aggregate, field_types)


@pytest.mark.parametrize(
    'order_by, field_types, expected_message',
    [
        ('', {'price': float}, 'Аргумент --order-by не может быть пустым'),
        ('gh=gh',
         {'price': float},
         'Неверный формат сортировки: должен быть "field=order", где order в'
         ' ["asc", "desc"]'),
        ('unknown=asc',
         {'price': float},
         'Поле "unknown" отсутствует в данных'),
    ]
)
def test_not_valid_validate_order_by(order_by, field_types, expected_message):
    """Тест не валидных данных для сортировки."""
    with pytest.raises(ValueError, match=re.escape(expected_message)):
        validate_order_by(order_by, field_types)


@pytest.mark.parametrize(
    'data_selector, headers, floatfmt, where, aggregate, expected_description',
    [
        (
            lambda goods: [goods[0].__dict__],
            'keys',
            '.1f',
            'brand=apple',
            None,
            'Отфильтрованные товары (условие: brand=apple):',
        ),
        (
            lambda goods: [[150.0]],
            ['avg'],
            '.2f',
            'price>50',
            'price=avg',
            'Агрегация товаров (условие: price>50, агрегация: price=avg):',
        ),
        (
            lambda goods: [good.__dict__ for good in goods],
            'keys',
            '.1f',
            '',
            None,
            'Отфильтрованные товары (условие: без фильтра):',
        ),
        (
            lambda goods: [goods[2].__dict__],
            ['name', 'brand', 'price', 'rating', 'stock'],
            '.1f',
            'brand=xiaomi',
            None,
            'Отфильтрованные товары (условие: brand=xiaomi):',
        ),
    ]
)
@patch('scr.main.tabulate')
def test_print_table(
        mock_tabulate,
        mock_goods,
        data_selector,
        headers,
        floatfmt,
        where,
        aggregate,
        expected_description
):
    """Тест вывода отчёта в терминал."""
    data = data_selector(mock_goods)
    mock_tabulate.return_value = 'mocked_table_output'

    captured_output = io.StringIO()
    sys.stdout = captured_output

    try:
        print_table(data, headers, floatfmt, where, aggregate)
        output = captured_output.getvalue().strip()
        assert output.startswith(expected_description)
        mock_tabulate.assert_called_once_with(
            data,
            headers=headers,
            tablefmt='grid',
            floatfmt=floatfmt
        )
        assert 'mocked_table_output' in output
    finally:
        sys.stdout = sys.__stdout__


@pytest.mark.parametrize(
    'file_paths, path_mocks, expected_files, expected_error',
    [
        (
            ['data1.csv', 'data2.csv'],
            [
                {'exists': True, 'is_file': True, 'suffix': '.csv'},
                {'exists': True, 'is_file': True, 'suffix': '.csv'},
            ],
            ['data1.csv', 'data2.csv'],
            None,
        ),
        (
            ['data1.csv', 'missing.csv'],
            [
                {'exists': True, 'is_file': True, 'suffix': '.csv'},
                {'exists': False, 'is_file': False, 'suffix': '.csv'},
            ],
            None,
            'Файл "missing.csv" не существует',
        ),
        (
            ['data1.csv', 'directory.csv'],
            [
                {'exists': True, 'is_file': True, 'suffix': '.csv'},
                {'exists': True, 'is_file': False, 'suffix': '.csv'},
            ],
            None,
            '"directory.csv" не является файлом',
        ),
        (
            ['data1.csv', 'data2.txt'],
            [
                {'exists': True, 'is_file': True, 'suffix': '.csv'},
                {'exists': True, 'is_file': True, 'suffix': '.txt'},
            ],
            None,
            'Файл "data2.txt" должен иметь расширение .csv',
        ),
        (
            [],
            [],
            [],
            None,
        ),
    ]
)
@patch('scr.main.Path')
def test_validate_files_action(
        mock_path,
        mock_parser,
        mock_namespace,
        file_paths,
        path_mocks,
        expected_files,
        expected_error
):
    """Тест валидации файлов."""
    mock_instances = []
    for pm in path_mocks:
        mock_instance = Mock()
        mock_instance.exists.return_value = pm['exists']
        mock_instance.is_file.return_value = pm['is_file']
        mock_instance.suffix.lower.return_value = pm['suffix']
        mock_instances.append(mock_instance)
    mock_path.side_effect = mock_instances

    action = ValidateFilesAction(option_strings=None, dest='files')

    if expected_error:
        with pytest.raises(SystemExit):
            action(mock_parser, mock_namespace, file_paths)
        mock_parser.error.assert_called_once_with(expected_error)
    else:
        action(mock_parser, mock_namespace, file_paths)
        mock_parser.error.assert_not_called()
        mock_namespace.files = expected_files
        assert mock_namespace.files == expected_files


@pytest.mark.parametrize(
    'data, output, output_dir, expected_filename, expected_output',
    [
        (
            [{'name': 'item1'}],
            'test1',
            'export',
            'export/test1.json',
            'Отчёт сохранён в файл: export/test1.json',
        ),
        (
            {'value': 42},
            'test2.json',
            'custom_dir',
            'custom_dir/test2.json',
            'Отчёт сохранён в файл: custom_dir/test2.json',
        ),
        (
            [],
            'test4',
            'export',
            'export/test4.json',
            'Отчёт сохранён в файл: export/test4.json',
        ),
    ]
)
@patch('scr.main.Path')
@patch('scr.main.json.dump')
@patch('scr.main.open')
def test_save_json(
        mock_open,
        mock_json_dump,
        mock_path,
        data,
        output,
        output_dir,
        expected_filename,
        expected_output
):
    """Тест сохранение данных в JSON-файл с различными входными параметрами."""
    mock_output_path = MagicMock()
    mock_output_file = MagicMock()
    mock_output_file.__str__.return_value = expected_filename
    mock_path.return_value = mock_output_path
    mock_output_path.__truediv__.return_value = mock_output_file
    mock_output_path.mkdir = MagicMock()

    captured_output = io.StringIO()
    sys.stdout = captured_output

    try:
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        save_json(data, output, output_dir)
        mock_path.assert_called_once_with(output_dir)
        mock_output_path.mkdir.assert_called_once_with(exist_ok=True)
        mock_open.assert_called_once_with(
            mock_output_file, 'w', encoding='utf-8'
        )
        mock_json_dump.assert_called_once_with(
            data, mock_file, ensure_ascii=False, indent=2
        )
        assert captured_output.getvalue().strip() == expected_output
    finally:
        sys.stdout = sys.__stdout__


@pytest.fixture
def mock_args():
    """Аргументы отчёта без функций."""
    args = MagicMock()
    args.files = ['data1.csv']
    args.where = ''
    args.order_by = None
    args.aggregate = None
    args.report = 'terminal'
    args.output = 'output'
    return args


@patch('scr.main.parse_arguments')
@patch('scr.main.process_files')
@patch('scr.main.print_table')
@patch('scr.main.save_json')
def test_main_no_filter_sort_aggregate_terminal(
        mock_save_json,
        mock_print_table,
        mock_process_files,
        mock_parse_arguments,
        mock_args,
        mock_goods,
        mock_field_types
):
    """Тест main вывод в терминал без функций."""
    mock_args.report = 'terminal'
    mock_parse_arguments.return_value = mock_args
    mock_process_files.return_value = (mock_goods, mock_field_types)

    captured_output = io.StringIO()
    sys.stdout = captured_output

    try:
        main()
        mock_print_table.assert_called_once_with(
            [good.__dict__ for good in mock_goods],
            headers='keys',
            floatfmt='.1f',
            where=''
        )
        mock_save_json.assert_not_called()
    finally:
        sys.stdout = sys.__stdout__


@patch('scr.main.parse_arguments')
@patch('scr.main.process_files')
@patch('scr.main.print_table')
@patch('scr.main.save_json')
def test_main_no_filter_sort_aggregate_json(
        mock_save_json,
        mock_print_table,
        mock_process_files,
        mock_parse_arguments,
        mock_args,
        mock_goods,
        mock_field_types
):
    """Тест main сохранение json без функций."""
    mock_args.report = 'json'
    mock_parse_arguments.return_value = mock_args
    mock_process_files.return_value = (mock_goods, mock_field_types)

    captured_output = io.StringIO()
    sys.stdout = captured_output

    try:
        main()
        mock_save_json.assert_called_once_with(
            [good.__dict__ for good in mock_goods],
            'output'
        )
        mock_print_table.assert_not_called()
    finally:
        sys.stdout = sys.__stdout__


@patch('scr.main.parse_arguments')
@patch('scr.main.process_files')
@patch('scr.main.Filter')
@patch('scr.main.print_table')
@patch('scr.main.save_json')
def test_main_with_filter(
        mock_save_json,
        mock_print_table,
        mock_filter,
        mock_process_files,
        mock_parse_arguments,
        mock_args,
        mock_goods,
        mock_field_types
):
    """Тест main с фильтрацией."""
    mock_args.where = 'brand=apple'
    mock_args.report = 'json'
    mock_parse_arguments.return_value = mock_args
    mock_process_files.return_value = (mock_goods, mock_field_types)

    mock_filter_instance = MagicMock()
    mock_filter.return_value = mock_filter_instance
    mock_filter_instance.filter_goods.return_value = mock_goods

    captured_output = io.StringIO()
    sys.stdout = captured_output

    try:
        main()
        mock_filter_instance.filter_goods.assert_called_once_with(
            'brand=apple'
        )
        mock_save_json.assert_called_once_with(
            [good.__dict__ for good in mock_goods],
            'output'
        )
        mock_print_table.assert_not_called()
    finally:
        sys.stdout = sys.__stdout__


@patch('scr.main.parse_arguments')
@patch('scr.main.process_files')
@patch('scr.main.Sorter')
@patch('scr.main.validate_order_by')
@patch('scr.main.print_table')
@patch('scr.main.save_json')
def test_main_with_sort(
        mock_save_json,
        mock_print_table,
        mock_validate_order_by,
        mock_sorter,
        mock_process_files,
        mock_parse_arguments,
        mock_args,
        mock_goods,
        mock_field_types
):
    """Тест main с сортировкой."""
    mock_args.order_by = 'price=asc'
    mock_args.report = 'terminal'
    mock_parse_arguments.return_value = mock_args
    mock_process_files.return_value = (mock_goods, mock_field_types)

    mock_sorter_instance = MagicMock()
    mock_sorter.return_value = mock_sorter_instance
    mock_sorter_instance.sort_goods.return_value = mock_goods
    mock_validate_order_by.return_value = ('price', 'asc')

    captured_output = io.StringIO()
    sys.stdout = captured_output

    try:
        main()
        mock_validate_order_by.assert_called_once_with(
            'price=asc', mock_field_types
        )
        mock_sorter_instance.sort_goods.assert_called_once_with('price', 'asc')
        mock_print_table.assert_called_once_with(
            [good.__dict__ for good in mock_goods],
            headers='keys',
            floatfmt='.1f',
            where=''
        )
        mock_save_json.assert_not_called()
    finally:
        sys.stdout = sys.__stdout__


@patch('scr.main.parse_arguments')
@patch('scr.main.process_files')
@patch('scr.main.Aggregator')
@patch('scr.main.validate_aggregate')
@patch('scr.main.print_table')
@patch('scr.main.save_json')
def test_main_with_aggregate(
        mock_save_json,
        mock_print_table,
        mock_validate_aggregate,
        mock_aggregator,
        mock_process_files,
        mock_parse_arguments,
        mock_args,
        mock_goods,
        mock_field_types
):
    """Тест main с агрегацией."""
    mock_args.aggregate = 'price=avg'
    mock_args.report = 'terminal'
    mock_parse_arguments.return_value = mock_args
    mock_process_files.return_value = (mock_goods, mock_field_types)

    mock_aggregator_instance = MagicMock()
    mock_aggregator.return_value = mock_aggregator_instance
    mock_aggregator_instance.calculate_aggregation.return_value = 150.0
    mock_validate_aggregate.return_value = ('price', 'avg')

    captured_output = io.StringIO()
    sys.stdout = captured_output

    try:
        main()
        mock_validate_aggregate.assert_called_once_with(
            'price=avg', mock_field_types
        )
        (mock_aggregator_instance.calculate_aggregation
         .assert_called_once_with('price', 'avg'))
        mock_print_table.assert_called_once_with(
            [[150.0]],
            headers=['avg'],
            floatfmt='.2f',
            where='',
            aggregate='price=avg'
        )
        mock_save_json.assert_not_called()
    finally:
        sys.stdout = sys.__stdout__
