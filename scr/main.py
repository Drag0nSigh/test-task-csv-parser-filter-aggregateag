import argparse
import sys
from pathlib import Path
from typing import Dict, List, Union

sys.path.append(str(Path(__file__).parent.parent))

from scr.models.goods import Good
from scr.parsers.parsers import ParserCsv

class ValidateFilesAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        valid_files = []
        for file_path in values:
            path = Path(file_path)
            # Проверяем существование файла
            if not path.exists():
                parser.error(f"Файл '{file_path}' не существует")
            # Проверяем, что это файл, а не директория
            if not path.is_file():
                parser.error(f"'{file_path}' не является файлом")
            # Проверяем расширение
            if path.suffix.lower() != '.csv':
                parser.error(f"Файл '{file_path}' должен иметь расширение "
                             f".csv")
            valid_files.append(file_path)
        setattr(namespace, self.dest, valid_files)



def process_files(file_paths: List[str]) -> List[Good]:
    combined_result = []
    for file_path in file_paths:
        try:
            with open(file_path, 'r', encoding='utf-8', newline='') as file:
                try:
                    result = ParserCsv(file).parse_data()
                    combined_result += result
                except Exception as e:
                    print(f'Ошибка при парсинге файла "{file_path}": {e}')
                    continue
        except Exception as e:
            print(f'Ошибка при чтении файла "{file_path}": {e}')
            continue
    if not combined_result:
        print('Ошибка: ни один файл не был успешно обработан.')
        exit(1)
    return combined_result
