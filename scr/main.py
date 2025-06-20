import argparse
import sys
from pathlib import Path
from typing import List

import json
from tabulate import tabulate

sys.path.append(str(Path(__file__).parent.parent))

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
    return parser.parse_args()

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

    # Фильтрация данных, если указано условие
    if args.where and args.where.strip():
        try:
            filter_report = Filter(goods)
            goods = filter_report.filter_goods(args.where)
        except ValueError as e:
            print(f'Ошибка в условии фильтрации: {e}')
            exit(1)

    # Вывод отчёта
    if args.report == 'terminal':
        data = [good.__dict__ for good in goods]
        print(f'Отфильтрованные товары (условие: {args.where or "без фильтра"}):')
        print(tabulate(data, headers='keys', tablefmt='grid', floatfmt='.1f'))
    elif args.report == 'json':
        output_dir = Path('export')
        output_dir.mkdir(exist_ok=True)  # Создаём папку export, если не существует
        output_file = output_dir / f'{args.output}.json' if not args.output.endswith(
            '.json') else output_dir / args.output
        data = [good.__dict__ for good in goods]
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f'Отчёт сохранён в файл: {output_file}')
        except Exception as e:
            print(f'Ошибка при сохранении JSON: {e}')
            sys.exit(1)


if __name__ == '__main__':
    main()
