import csv
from typing import Dict, List, TextIO

from scr.models.goods import Good


class ParserCsv(object):
    def __init__(self, csv_file: TextIO):
        self.csv_file = csv_file

    def parse_data(self) -> List[Good]:
        goods = []
        reader = csv.DictReader(self.csv_file)
        for row in reader:  # type: Dict[str, str]
            good = Good(
                name=row['name'],
                brand=row['brand'],
                price=int(row['price']),
                rating=float(row['rating'])
            )
            goods.append(good)
        return goods
