import io
import re
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

from scr.main import (ValidateFilesAction, main, print_table, process_files,
                      save_json, validate_aggregate, validate_order_by)
from scr.models.goods import Good
from tests.conftest import valid_good, valid_list_goods


@pytest.fixture
def mock_parser():
    parser = Mock()
    parser.error.side_effect = SystemExit  # Эмулируем поведение parser.error
    return parser


@pytest.fixture
def mock_namespace():
    return Mock()


@pytest.mark.parametrize(
    'aggregate, expected_message',
    [
        ('', 'Аргумент --aggregate не может быть пустым'),
        ('gh=gh', re.escape('Неверный формат агрегации: должен быть '
                            '"field=operation", где field в '
                            '["price", "rating"], operation в '
                            '["avg", "min", "max"]')),
    ]
)
def test_not_valid_validate_aggregate(aggregate, expected_message):
    with pytest.raises(ValueError, match=expected_message):
        validate_aggregate(aggregate)


@pytest.mark.parametrize(
    'order_by, expected_message',
    [
        ('', 'Аргумент --order-by не может быть пустым'),
        ('gh=gh',
         re.escape('Неверный формат сортировки: должен быть "field=order"'
                   ', где field в ["name", "brand", "price", '
                   '"rating"], order в ["asc", "desc"]')),
    ]
)
def test_not_valid_validate_order_by(order_by, expected_message):
    with pytest.raises(ValueError, match=expected_message):
        validate_order_by(order_by)


@pytest.mark.parametrize(
    'data_selector, headers, floatfmt, where, aggregate, expected_description',
    [
        # Случай с фильтром и без агрегации, headers='keys'
        (
                lambda goods: [goods[0].__dict__],  # Выбираем iphone
                'keys',
                '.1f',
                'brand=apple',
                None,
                'Отфильтрованные товары (условие: brand=apple):',
        ),
        # Случай с фильтром и агрегацией, headers=['avg']
        (
                lambda goods: [[150.0]],  # Средняя цена из фикстуры
                ['avg'],
                '.2f',
                'price>50',
                'price=avg',
                'Агрегация товаров (условие: price>50, агрегация: price=avg):',
        ),
        # Случай без фильтра и без агрегации
        (
                lambda goods: [good.__dict__ for good in goods],  # Все товары
                'keys',
                '.1f',
                '',
                None,
                'Отфильтрованные товары (условие: без фильтра):',
        ),
        # Случай с фильтром и списком headers
        (
                lambda goods: [goods[2].__dict__],  # Выбираем xiaomi
                ['name', 'brand', 'price', 'rating'],
                '.1f',
                'brand=xiaomi',
                None,
                'Отфильтрованные товары (условие: brand=xiaomi):',
        ),
    ]
)
@patch('scr.main.tabulate')  # Мокируем tabulate из scr.main
def test_print_table(mock_tabulate, valid_list_goods, data_selector, headers,
                     floatfmt, where, aggregate, expected_description):
    # Формируем данные из фикстуры
    data = data_selector(valid_list_goods)

    # Настраиваем мокирование tabulate
    mock_tabulate.return_value = 'mocked_table_output'

    # Перехватываем вывод в stdout
    captured_output = io.StringIO()
    sys.stdout = captured_output

    try:
        # Вызываем функцию
        print_table(data, headers, floatfmt, where, aggregate)

        # Получаем выведенный текст
        output = captured_output.getvalue().strip()

        # Проверяем, что описание корректно
        assert output.startswith(expected_description)

        # Проверяем, что tabulate вызван с правильными параметрами
        mock_tabulate.assert_called_once_with(
            data,
            headers=headers,
            tablefmt='grid',
            floatfmt=floatfmt
        )

        # Проверяем, что в выводе есть результат tabulate
        assert 'mocked_table_output' in output

    finally:
        # Восстанавливаем sys.stdout
        sys.stdout = sys.__stdout__


@pytest.mark.parametrize(
    'file_paths, path_mocks, expected_files, expected_error',
    [
        # Сценарий 1: Все файлы валидны
        (
                ['data1.csv', 'data2.csv'],
                [
                    {'exists': True, 'is_file': True, 'suffix': '.csv'},
                    {'exists': True, 'is_file': True, 'suffix': '.csv'},
                ],
                ['data1.csv', 'data2.csv'],
                None,
        ),
        # Сценарий 2: Несуществующий файл
        (
                ['data1.csv', 'missing.csv'],
                [
                    {'exists': True, 'is_file': True, 'suffix': '.csv'},
                    {'exists': False, 'is_file': False, 'suffix': '.csv'},
                ],
                None,
                'Файл "missing.csv" не существует',
        ),
        # Сценарий 3: Не файл (директория)
        (
                ['data1.csv', 'directory.csv'],
                [
                    {'exists': True, 'is_file': True, 'suffix': '.csv'},
                    {'exists': True, 'is_file': False, 'suffix': '.csv'},
                ],
                None,
                '"directory.csv" не является файлом',
        ),
        # Сценарий 4: Неверное расширение
        (
                ['data1.csv', 'data2.txt'],
                [
                    {'exists': True, 'is_file': True, 'suffix': '.csv'},
                    {'exists': True, 'is_file': True, 'suffix': '.txt'},
                ],
                None,
                'Файл "data2.txt" должен иметь расширение .csv',
        ),
        # Сценарий 5: Пустой список файлов
        (
                [],
                [],
                [],
                None,
        ),
    ]
)
@patch('scr.main.Path')
def test_validate_files_action(mock_path, mock_parser, mock_namespace,
                               file_paths, path_mocks, expected_files,
                               expected_error):
    # Настраиваем поведение mock_path
    mock_instances = []
    for pm in path_mocks:
        mock_instance = Mock()
        mock_instance.exists.return_value = pm['exists']
        mock_instance.is_file.return_value = pm['is_file']
        mock_instance.suffix.lower.return_value = pm['suffix']
        mock_instances.append(mock_instance)
    mock_path.side_effect = mock_instances

    # Создаём экземпляр ValidateFilesAction
    action = ValidateFilesAction(option_strings=None, dest='files')

    if expected_error:
        # Проверяем, что вызывается parser.error с правильным сообщением
        with pytest.raises(SystemExit):
            action(mock_parser, mock_namespace, file_paths)
        mock_parser.error.assert_called_once_with(expected_error)
    else:
        # Проверяем, что ошибки не возникает и namespace.files устанавливается
        action(mock_parser, mock_namespace, file_paths)
        mock_parser.error.assert_not_called()
        mock_namespace.files = expected_files
        assert mock_namespace.files == expected_files

@pytest.mark.parametrize(
    'data, output, output_dir, expected_filename, expected_output',
    [
        # Сценарий 1: Успешное сохранение, output без .json
        (
            [{'name': 'item1'}],
            'test1',
            'export',
            'export/test1.json',
            'Отчёт сохранён в файл: export/test1.json',
        ),
        # Сценарий 2: Успешное сохранение, output с .json
        (
            {'value': 42},
            'test2.json',
            'custom_dir',
            'custom_dir/test2.json',
            'Отчёт сохранён в файл: custom_dir/test2.json',
        ),
        # Сценарий 3: Пустые данные
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
def test_save_json(mock_open, mock_json_dump, mock_path, data, output, output_dir, expected_filename, expected_output):
    # Настраиваем мокирование Path
    mock_output_path = MagicMock()
    mock_output_file = MagicMock()
    mock_output_file.__str__.return_value = expected_filename
    mock_path.return_value = mock_output_path
    mock_output_path.__truediv__.return_value = mock_output_file
    mock_output_path.mkdir = MagicMock()

    # Настраиваем перехват вывода
    captured_output = io.StringIO()
    sys.stdout = captured_output

    try:
        # Настраиваем успешное открытие файла
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Вызываем функцию
        save_json(data, output, output_dir)

        # Проверяем вызовы
        mock_path.assert_called_once_with(output_dir)
        mock_output_path.mkdir.assert_called_once_with(exist_ok=True)
        mock_open.assert_called_once_with(mock_output_file, 'w', encoding='utf-8')
        mock_json_dump.assert_called_once_with(data, mock_file, ensure_ascii=False, indent=2)
        assert captured_output.getvalue().strip() == expected_output

    finally:
        sys.stdout = sys.__stdout__

@pytest.mark.parametrize(
    'file_paths, open_side_effects, parse_side_effects, expected_result, expected_output, expect_exit',
    [
        # Сценарий 1: Успешная обработка одного файла
        (
            ['data1.csv'],
            [MagicMock()],  # Успешное открытие файла
            [[Good(name='iphone', brand='apple', price=100, rating=4.9)]],  # Результат parse_data
            [Good(name='iphone', brand='apple', price=100, rating=4.9)],
            '',
            False,
        ),
        # Сценарий 2: Успешная обработка двух файлов
        (
            ['data1.csv', 'data2.csv'],
            [MagicMock(), MagicMock()],
            [
                [Good(name='iphone', brand='apple', price=100, rating=4.9)],
                [Good(name='samsung', brand='samsung', price=200, rating=4.6)],
            ],
            [
                Good(name='iphone', brand='apple', price=100, rating=4.9),
                Good(name='samsung', brand='samsung', price=200, rating=4.6),
            ],
            '',
            False,
        ),
        # Сценарий 3: Ошибка открытия файла
        (
            ['data1.csv', 'data2.csv'],
            [Exception('File not found'), MagicMock()],
            [[Good(name='iphone', brand='apple', price=100, rating=4.9)]],
            [Good(name='iphone', brand='apple', price=100, rating=4.9)],
            'Ошибка при чтении файла \"data1.csv\": File not found',
            False,
        ),
        # Сценарий 4: Ошибка данных в файле
        (
            ['data1.csv', 'data2.csv'],
            [MagicMock(), MagicMock()],
            [ValueError('Missing fields'), [Good(name='iphone', brand='apple', price=100, rating=4.9)]],
            [Good(name='iphone', brand='apple', price=100, rating=4.9)],
            'Ошибка данных в файле \"data1.csv\": Missing fields',
            False,
        ),
        # Сценарий 5: Другая ошибка парсинга
        (
            ['data1.csv', 'data2.csv'],
            [MagicMock(), MagicMock()],
            [Exception('Invalid format'), [Good(name='iphone', brand='apple', price=100, rating=4.9)]],
            [Good(name='iphone', brand='apple', price=100, rating=4.9)],
            'Ошибка при парсинге файла \"data1.csv\": Invalid format',
            False,
        ),
        # Сценарий 6: Все файлы не обработаны
        (
            ['data1.csv', 'data2.csv'],
            [Exception('File not found'), Exception('File not found')],
            [],
            None,
            'Ошибка при чтении файла \"data1.csv\": File not found\n'
            'Ошибка при чтении файла \"data2.csv\": File not found\n'
            'Ошибка: ни один файл не был успешно обработан.',
            True,
        ),
        # Сценарий 7: Пустой список файлов
        (
            [],
            [],
            [],
            None,
            'Ошибка: ни один файл не был успешно обработан.',
            True,
        ),
    ]
)
@patch('scr.main.open')
@patch('scr.main.ParserCsv')
@patch('scr.main.sys.exit')
def test_process_files(mock_sys_exit, mock_parser_csv, mock_open, file_paths, open_side_effects, parse_side_effects, expected_result, expected_output, expect_exit):
    # Настраиваем мокирование open
    mock_open.side_effect = open_side_effects

    # Настраиваем мокирование ParserCsv.parse_data
    mock_parser_instance = MagicMock()
    mock_parser_csv.return_value = mock_parser_instance
    mock_parser_instance.parse_data.side_effect = parse_side_effects

    # Настраиваем перехват вывода
    captured_output = io.StringIO()
    sys.stdout = captured_output

    try:
        if expect_exit:
            with pytest.raises(SystemExit):
                process_files(file_paths)
            mock_sys_exit.assert_called_once_with(1)
            assert captured_output.getvalue().strip() == expected_output
        else:
            result = process_files(file_paths)
            mock_sys_exit.assert_not_called()
            assert result == expected_result
            assert captured_output.getvalue().strip() == expected_output

    finally:
        sys.stdout = sys.__stdout__

@pytest.mark.parametrize(
    'file_paths, open_side_effects, parse_side_effects, expected_result, expected_output',
    [
        # Сценарий 1: Успешная обработка одного файла
        (
            ['data1.csv'],
            [MagicMock()],  # Успешное открытие файла
            [[Good(name='iphone', brand='apple', price=100, rating=4.9)]],  # Результат parse_data
            [Good(name='iphone', brand='apple', price=100, rating=4.9)],
            '',
        ),
        # Сценарий 2: Успешная обработка двух файлов
        (
            ['data1.csv', 'data2.csv'],
            [MagicMock(), MagicMock()],
            [
                [Good(name='iphone', brand='apple', price=100, rating=4.9)],
                [Good(name='samsung', brand='samsung', price=200, rating=4.6)],
            ],
            [
                Good(name='iphone', brand='apple', price=100, rating=4.9),
                Good(name='samsung', brand='samsung', price=200, rating=4.6),
            ],
            '',
        ),
        # Сценарий 3: Ошибка открытия файла
        (
            ['data1.csv', 'data2.csv'],
            [Exception('File not found'), MagicMock()],
            [[Good(name='iphone', brand='apple', price=100, rating=4.9)]],
            [Good(name='iphone', brand='apple', price=100, rating=4.9)],
            'Ошибка при чтении файла \"data1.csv\": File not found',
        ),
        # Сценарий 4: Ошибка данных в файле
        (
            ['data1.csv', 'data2.csv'],
            [MagicMock(), MagicMock()],
            [ValueError('Missing fields'), [Good(name='iphone', brand='apple', price=100, rating=4.9)]],
            [Good(name='iphone', brand='apple', price=100, rating=4.9)],
            'Ошибка данных в файле \"data1.csv\": Missing fields',
        ),
        # Сценарий 5: Другая ошибка парсинга
        (
            ['data1.csv', 'data2.csv'],
            [MagicMock(), MagicMock()],
            [Exception('Invalid format'), [Good(name='iphone', brand='apple', price=100, rating=4.9)]],
            [Good(name='iphone', brand='apple', price=100, rating=4.9)],
            'Ошибка при парсинге файла \"data1.csv\": Invalid format',
        ),
    ]
)
@patch('scr.main.open')
@patch('scr.main.ParserCsv')
def test_process_files(mock_parser_csv, mock_open, file_paths, open_side_effects, parse_side_effects, expected_result, expected_output):
    # Настраиваем мокирование open
    def open_side_effect(*args, **kwargs):
        side_effect = open_side_effects.pop(0)
        if isinstance(side_effect, Exception):
            mock_file = MagicMock()
            mock_file.__enter__.side_effect = side_effect
            return mock_file
        mock_file = MagicMock()
        mock_file.__enter__.return_value = side_effect
        return mock_file

    mock_open.side_effect = [open_side_effect(path) for path in file_paths]

    # Настраиваем мокирование ParserCsv.parse_data
    mock_parser_instance = MagicMock()
    mock_parser_csv.return_value = mock_parser_instance
    mock_parser_instance.parse_data.side_effect = parse_side_effects

    # Настраиваем перехват вывода
    captured_output = io.StringIO()
    sys.stdout = captured_output

    try:
        result = process_files(file_paths)
        assert result == expected_result
        assert captured_output.getvalue().strip() == expected_output
        mock_parser_instance.parse_data.assert_called()

    finally:
        sys.stdout = sys.__stdout__

@pytest.fixture
def mock_args():
    args = MagicMock()
    args.files = ['data1.csv']
    args.where = ''
    args.order_by = None
    args.aggregate = None
    args.report = 'terminal'
    args.output = 'output'
    return args

@pytest.fixture
def mock_goods():
    return [Good(name='iphone', brand='apple', price=100, rating=4.9)]

@patch('scr.main.parse_arguments')
@patch('scr.main.process_files')
@patch('scr.main.print_table')
@patch('scr.main.save_json')
def test_main_no_filter_sort_aggregate_terminal(mock_save_json, mock_print_table, mock_process_files, mock_parse_arguments, mock_args, mock_goods):
    # Настраиваем аргументы для терминала без фильтрации/сортировки/агрегации
    mock_args.report = 'terminal'
    mock_parse_arguments.return_value = mock_args
    mock_process_files.return_value = mock_goods

    # Настраиваем перехват вывода
    captured_output = io.StringIO()
    sys.stdout = captured_output

    try:
        main()
        assert captured_output.getvalue().strip() == ''
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
def test_main_no_filter_sort_aggregate_json(mock_save_json, mock_print_table, mock_process_files, mock_parse_arguments, mock_args, mock_goods):
    # Настраиваем аргументы для JSON без фильтрации/сортировки/агрегации
    mock_args.report = 'json'
    mock_parse_arguments.return_value = mock_args
    mock_process_files.return_value = mock_goods

    # Настраиваем перехват вывода
    captured_output = io.StringIO()
    sys.stdout = captured_output

    try:
        main()
        assert captured_output.getvalue().strip() == ''
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
def test_main_with_filter(mock_save_json, mock_print_table, mock_filter, mock_process_files, mock_parse_arguments, mock_args, mock_goods):
    # Настраиваем аргументы с фильтрацией, вывод в JSON
    mock_args.where = 'brand=apple'
    mock_args.report = 'json'
    mock_parse_arguments.return_value = mock_args
    mock_process_files.return_value = mock_goods

    # Настраиваем Filter
    mock_filter_instance = MagicMock()
    mock_filter.return_value = mock_filter_instance
    mock_filter_instance.filter_goods.return_value = mock_goods

    # Настраиваем перехват вывода
    captured_output = io.StringIO()
    sys.stdout = captured_output

    try:
        main()
        assert captured_output.getvalue().strip() == ''
        mock_filter_instance.filter_goods.assert_called_once_with('brand=apple')
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
@patch('scr.main.validate_order_by')
@patch('scr.main.print_table')
@patch('scr.main.save_json')
def test_main_with_sort(mock_save_json, mock_print_table, mock_validate_order_by, mock_filter, mock_process_files, mock_parse_arguments, mock_args, mock_goods):
    # Настраиваем аргументы с сортировкой, вывод в терминал
    mock_args.order_by = 'price,asc'
    mock_args.report = 'terminal'
    mock_parse_arguments.return_value = mock_args
    mock_process_files.return_value = mock_goods

    # Настраиваем Filter и validate_order_by
    mock_filter_instance = MagicMock()
    mock_filter.return_value = mock_filter_instance
    mock_filter_instance.sort_goods.return_value = mock_goods
    mock_validate_order_by.return_value = ('price', 'asc')

    # Настраиваем перехват вывода
    captured_output = io.StringIO()
    sys.stdout = captured_output

    try:
        main()
        assert captured_output.getvalue().strip() == ''
        mock_validate_order_by.assert_called_once_with('price,asc')
        mock_filter_instance.sort_goods.assert_called_once_with('price', 'asc')
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
@patch('scr.main.Filter')
@patch('scr.main.validate_aggregate')
@patch('scr.main.print_table')
@patch('scr.main.save_json')
def test_main_with_aggregate(mock_save_json, mock_print_table, mock_validate_aggregate, mock_filter, mock_process_files, mock_parse_arguments, mock_args, mock_goods):
    # Настраиваем аргументы с агрегацией, вывод в терминал
    mock_args.aggregate = 'price=avg'
    mock_args.report = 'terminal'
    mock_parse_arguments.return_value = mock_args
    mock_process_files.return_value = mock_goods

    # Настраиваем Filter и validate_aggregate
    mock_filter_instance = MagicMock()
    mock_filter.return_value = mock_filter_instance
    mock_filter_instance.calculate_aggregation.return_value = 100.0
    mock_validate_aggregate.return_value = ('price', 'avg')

    # Настраиваем перехват вывода
    captured_output = io.StringIO()
    sys.stdout = captured_output

    try:
        main()
        assert captured_output.getvalue().strip() == ''
        mock_validate_aggregate.assert_called_once_with('price=avg')
        mock_filter_instance.calculate_aggregation.assert_called_once_with('price', 'avg')
        mock_print_table.assert_called_once_with(
            [[100.0]],
            headers=['avg'],
            floatfmt='.2f',
            where='',
            aggregate='price=avg'
        )
        mock_save_json.assert_not_called()

    finally:
        sys.stdout = sys.__stdout__

