import csv
from typing import Any, Dict, List, TextIO

from scr.constants import FIELDS_FOR_FILTER
from scr.models.goods import Good


class ParserCsv:
    def __init__(self, csv_file: TextIO):
        self.csv_file = csv_file

    def parse_data(self) -> List[Good]:
        """Парсит файл csv по условиям и создаёт список объектов Good."""
        goods = []
        reader = csv.DictReader(self.csv_file)

        # Проверка заголовков
        if not set(FIELDS_FOR_FILTER).issubset(reader.fieldnames or []):
            missing = set(FIELDS_FOR_FILTER) - set(reader.fieldnames or [])
            raise ValueError(f"Отсутствуют обязательные поля в CSV: {missing}")

        for row in reader:  # type: Dict[str, Any]
            try:
                name = row.get('name', '').strip()
                brand = row.get('brand', '').strip()
                price_str = row.get('price', '').strip()
                rating_str = row.get('rating', '').strip()

                if not all([name, brand, price_str, rating_str]):
                    raise ValueError("Одно или несколько обязательных полей "
                                     "пусты")

                price = int(price_str)
                rating = float(rating_str)

                good = Good(
                    name=name,
                    brand=brand,
                    price=price,
                    rating=rating
                )
                goods.append(good)
            except ValueError as e:
                print(f'Пропущена строка {reader.line_num}: {e}')
        return goods
