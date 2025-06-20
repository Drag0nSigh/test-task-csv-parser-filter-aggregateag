from typing import Final, List

# Константы для фильтрации данных
FIELDS_FOR_FILTER: Final[List[str]] = ['name', 'brand', 'price', 'rating']
OPERATORS_FOR_FILTER: Final[List[str]] = ['=', '!=', '>', '<', '>=', '<=']

# Регулярное выражение для парсинга одного условия: поле, оператор, значение
WHERE_PATTERN: Final[str] = r'^(\w+)(=|!=|>|<|>=|<=)(.+)$'
