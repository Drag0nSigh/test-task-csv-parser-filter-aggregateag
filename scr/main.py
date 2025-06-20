import argparse
import sys
from pathlib import Path
from typing import Any, List, Union

import json
import re
from tabulate import tabulate

sys.path.append(str(Path(__file__).parent.parent))

from scr.constants import AGGR_PATTERN
from scr.models.goods import Good
from scr.reports.reports import Filter
from scr.parsers.parsers import ParserCsv


class ValidateFilesAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        valid_files = []
        for file_path in values:
            path = Path(file_path)
            # Проверяем существование файла
            if not path.exists():
                parser.error(f'Файл "{file_path}" не существует')
            # Проверяем, что это файл, а не директория
            if not path.is_file():
                parser.error(f'"{file_path}" не является файлом')
            # Проверяем расширение
            if path.suffix.lower() != '.csv':
                parser.error(f'Файл "{file_path}" должен иметь расширение '
                             f'.csv')
            valid_files.append(file_path)
        setattr(namespace, 'files', valid_files)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Обработка файлов и создание отчётов.'
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
        help='Тип отчёта: "terminal" для вывода в терминал, '
             '"json" для JSON'
    )
    parser.add_argument(
        '--output',
        default='output',
        help='Имя выходного файла для отчёта (по умолчанию: output)'
    )
    parser.add_argument(
        '--where',
        help='Условия для фильтрации данных. Можно использовать несколько условий, разделяя ";" (AND) или "|" (OR), '
             'например: --where "brand=xiaomi;rating>=4.8|price<=500"'
    )
    parser.add_argument(
        '--aggregate',
        help='Агрегация данных в формате "field=operation", например, "rating=avg" или "price=min"'
    )
    return parser.parse_args()


def validate_aggregate(aggregate: str) -> tuple[str, str]:
    """Валидирует аргумент --aggregate, возвращает (field, operation)."""
    if not aggregate:
        raise ValueError("Аргумент --aggregate не может быть пустым")
    match = re.match(AGGR_PATTERN, aggregate)
    if not match:
        raise ValueError('Неверный формат агрегации: должен быть "field=operation", где field в ["price", "rating"],'
                         ' operation в ["avg", "min", "max"]')
    field, operation = match.groups()
    return field, operation


def print_table(
        data: List[Any],
        headers: Union[List[str], str],
        floatfmt: str,
        where: str,
        aggregate: str = None
) -> None:
    """Выводит таблицу в терминал с описанием отчёта."""
    description = f'Агрегация товаров (условие: {where or "без фильтра"}, агрегация: {aggregate})'\
        if aggregate else f'Отфильтрованные товары (условие: {where or "без фильтра"})'
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


def process_files(file_paths: List[str]) -> List[Good]:
    combined_result = []
    for file_path in file_paths:
        try:
            with open(file_path, 'r', encoding='utf-8', newline='') as file:
                try:
                    result = ParserCsv(file).parse_data()
                    combined_result += result
                except ValueError as e:
                    print(f'Ошибка данных в файле "{file_path}": {e}')
                    continue
                except Exception as e:
                    print(f'Ошибка при парсинге файла "{file_path}": {e}')
                    continue
        except Exception as e:
            print(f'Ошибка при чтении файла "{file_path}": {e}')
            continue
    if not combined_result:
        print('Ошибка: ни один файл не был успешно обработан.')
        sys.exit(1)
    return combined_result


def main():
    args = parse_arguments()

    # Чтение и парсинг данных
    goods = process_files(args.files)

    # Фильтрация данных, если указано непустое условие
    if args.where and args.where.strip():
        try:
            filter_report = Filter(goods)
            goods = filter_report.filter_goods(args.where)
        except ValueError as e:
            print(f'Ошибка в условии фильтрации: {e}')
            sys.exit(1)

    # Обработка агрегации
    if args.aggregate:
        try:
            field, operation = validate_aggregate(args.aggregate)
            filter_report = Filter(goods)
            result = filter_report.calculate_aggregation(field, operation)
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
