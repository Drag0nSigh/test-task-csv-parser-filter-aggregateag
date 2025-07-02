import csv
from dataclasses import make_dataclass
from typing import Any, Dict, List, TextIO

from scr.exceptions import InvalidCsvFormatError


class ParserCsv:
    """Класс для парсинга CSV."""

    def __init__(self, csv_file: TextIO):
        self.csv_file = csv_file

    def parse_data(self) -> tuple[List[Any], Dict[str, type]]:
        """
        Парсит CSV-файл и возвращает список объектов и словарь типов полей.

        Читает CSV-файл, используя `csv.DictReader`, определяет типы данных
        полей на основе первой строки (строка или число с плавающей точкой),
        создаёт динамический класс `Good` с помощью
        `dataclasses.make_dataclass` и преобразует строки CSV в объекты
        этого класса.
        """
        reader = csv.DictReader(self.csv_file)

        # Проверка наличия заголовков
        if not reader.fieldnames:
            raise InvalidCsvFormatError('CSV-файл не содержит заголовков')

        # Получаем первую строку для анализа типов
        try:
            first_row = next(reader, None)
            if first_row is None:
                return [], {}
        except StopIteration:
            return [], {}

        # Определяем типы полей по первой строке
        field_types = {}
        for field in reader.fieldnames:
            value = first_row.get(field, '').strip()
            try:
                float(value)
                field_types[field] = float
            except ValueError:
                field_types[field] = str

        # Создаём динамический класс Good
        fields = [(field, field_types[field]) for field in reader.fieldnames]
        Good = make_dataclass('Good', fields, repr=True)

        # Перематываем файл на начало для повторного чтения
        self.csv_file.seek(0)
        reader = csv.DictReader(self.csv_file)

        goods = []
        for row in reader:
            try:
                kwargs = {}
                for field in reader.fieldnames:
                    value = row.get(field, '').strip()
                    if field_types[field] == float:
                        # Пустое значение как 0.0 для float
                        value = float(value) if value else 0.0
                    else:
                        # Пустое значение как '' для str
                        value = value if value else ''
                    kwargs[field] = value
                good = Good(**kwargs)
                goods.append(good)
            except InvalidCsvFormatError as e:
                print(f'Пропущена строка {reader.line_num}: {e}')
        return goods, field_types
