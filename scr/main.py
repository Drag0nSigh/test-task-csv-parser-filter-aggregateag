import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Union

from tabulate import tabulate

sys.path.append(str(Path(__file__).parent.parent))

from scr.constants import AGGR_PATTERN, ORDER_PATTERN
from scr.parsers.parsers import ParserCsv
from scr.reports.reports import Aggregator, Filter, Sorter


class ValidateFilesAction(argparse.Action):
    """
    Валидация параметра файла для обработки.

    Проверяет, является ли путь файлом, существует ли он и имеет ли правильное расширение.
    """

    def __call__(self, parser, namespace, values, option_string=None):
        """Проверка пути к файлу."""
        valid_files = []
        for file_path in values:
            path = Path(file_path)
            if not path.exists():
                parser.error(f'Файл "{file_path}" не существует')
            if not path.is_file():
                parser.error(f'"{file_path}" не является файлом')
            if path.suffix.lower() != '.csv':
                parser.error(f'Файл "{file_path}" должен иметь расширение .csv')
            valid_files.append(file_path)
        setattr(namespace, 'files', valid_files)


def parse_arguments() -> argparse.Namespace:
    """Парсит аргументы выполнения скрипта."""
    parser = argparse.ArgumentParser(
        description='Обработка CSV-файлов и создание отчётов.'
    )
    parser.add_argument(
        'files',
        nargs='+',
        action=ValidateFilesAction,
        help='Пути к CSV-файлам для обработки (например, data1.csv data2.csv)'
    )
    parser.add_argument(
        '--report',
        choices=['terminal', 'json'],
        default='terminal',
        help='Тип отчёта: "terminal" для вывода в терминал, "json" для JSON'
    )
    parser.add_argument(
        '--output',
        default='output',
        help='Имя выходного файла для отчёта (по умолчанию: output)'
    )
    parser.add_argument(
        '--where',
        help='Условия для фильтрации данных. Можно использовать несколько '
             'условий, разделяя ";" (AND) или "|" (OR), '
             'например: --where "brand=xiaomi;rating>=4.8|price<=500"'
    )
    parser.add_argument(
        '--aggregate',
        help='Агрегация данных в формате "field=operation", например, '
             '"rating=avg" или "price=min"'
    )
    parser.add_argument(
        '--order-by',
        help='Сортировка данных в формате "field=order", например, "brand=asc" '
             'или "price=desc"'
    )
    return parser.parse_args()


def validate_aggregate(aggregate: str, field_types: Dict[str, type]) -> tuple[str, str]:
    """Валидирует аргумент --aggregate, возвращает (field, operation)."""
    if not aggregate:
        raise ValueError('Аргумент --aggregate не может быть пустым')
    match = re.match(AGGR_PATTERN, aggregate)
    if not match:
        raise ValueError('Неверный формат агрегации: должен быть "field=operation", '
                         'где operation в ["avg", "min", "max"]')
    field, operation = match.groups()
    if field not in field_types:
        raise ValueError(f'Поле "{field}" отсутствует в данных')
    if field_types[field] != float:
        raise ValueError(f'Агрегация возможна только для числовых полей, "{field}" имеет тип {field_types[field]}')
    return field, operation


def validate_order_by(order_by: str, field_types: Dict[str, type]) -> tuple[str, str]:
    """Валидирует аргумент --order-by, возвращает (field, order)."""
    if not order_by:
        raise ValueError('Аргумент --order-by не может быть пустым')
    match = re.match(ORDER_PATTERN, order_by)
    if not match:
        raise ValueError('Неверный формат сортировки: должен быть "field=order", '
                         'где order в ["asc", "desc"]')
    field, order = match.groups()
    if field not in field_types:
        raise ValueError(f'Поле "{field}" отсутствует в данных')
    return field, order


def print_table(
        data: List[Any],
        headers: Union[List[str], str],
        floatfmt: str,
        where: str,
        aggregate: str = None
) -> None:
    """Выводит таблицу в Таблица в терминал с описанием отчёта."""
    description = (f'Агрегация товаров (условие: {where or "без фильтра"}, '
                   f'агрегация: {aggregate})') \
        if aggregate else (f'Отфильтрованные товары (условие: '
                           f'{where or "без фильтра"})')
    print(description + ':')
    print(tabulate(data, headers=headers, tablefmt='grid', floatfmt=floatfmt))


def save_json(data: Any, output: str, output_dir: str = 'export') -> None:
    """Сохраняет данные в JSON-файл в указанной папке."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    output_file = output_path / f'{output}.json' if not output.endswith('.json') else output_path / output
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f'Отчёт сохранён в файл: {output_file}')
    except Exception as e:
        print(f'Ошибка при сохранении JSON: {e}')
        sys.exit(1)


def process_files(file_paths: List[str]) -> tuple[List[Any], Dict[str, type]]:
    """Читает и парсит CSV-файлы, возвращает список объектов и словарь типов полей."""
    combined_goods = []
    field_types = {}
    for file_path in file_paths:
        try:
            with open(file_path, 'r', encoding='utf-8', newline='') as file:
                try:
                    goods, types = ParserCsv(file).parse_data()
                    combined_goods += goods
                    if not field_types:
                        field_types = types
                    elif field_types != types:
                        print(f'Предупреждение: файл "{file_path}" имеет разные типы полей')
                except ValueError as e:
                    print(f'Ошибка данных в файле "{file_path}": {e}')
                    continue
                except Exception as e:
                    print(f'Ошибка при парсинге файла "{file_path}": {e}')
                    continue
        except Exception as e:
            print(f'Ошибка при чтении файла "{file_path}": {e}')
            continue
    if not combined_goods:
        print('Ошибка: ни один файл не был успешно обработан.')
        sys.exit(1)
    return combined_goods, field_types


def main():
    """Основная функция для обработки данных, фильтрации, агрегации и сортировки."""
    args = parse_arguments()

    # Чтение и парсинг данных
    goods, field_types = process_files(args.files)

    # Фильтрация данных, если указано условие
    if args.where and args.where.strip():
        try:
            filter_report = Filter(goods, field_types)
            goods = filter_report.filter_goods(args.where)
        except ValueError as e:
            print(f'Ошибка в условии фильтрации: {e}')
            sys.exit(1)

    # Сортировка данных, если указано
    if args.order_by:
        try:
            field, order = validate_order_by(args.order_by, field_types)
            sorter = Sorter(goods, field_types)
            goods = sorter.sort_goods(field, order)
        except ValueError as e:
            print(f'Ошибка в сортировке: {e}')
            sys.exit(1)

    # Обработка агрегации
    if args.aggregate:
        try:
            field, operation = validate_aggregate(args.aggregate, field_types)
            aggregator = Aggregator(goods, field_types)
            result = aggregator.calculate_aggregation(field, operation)
            if args.report == 'terminal':
                print_table(
                    [[result]],
                    headers=[operation],
                    floatfmt='.2f',
                    where=args.where,
                    aggregate=args.aggregate
                )
            elif args.report == 'json':
                save_json({operation: result}, args.output)
        except ValueError as e:
            print(f'Ошибка в агрегации: {e}')
            sys.exit(1)
    else:
        # Вывод отчёта без агрегации
        if args.report == 'terminal':
            data = [good.__dict__ for good in goods]
            print_table(data, headers='keys', floatfmt='.1f', where=args.where)
        elif args.report == 'json':
            data = [good.__dict__ for good in goods]
            save_json(data, args.output)


if __name__ == '__main__':
    main()