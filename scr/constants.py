from typing import Final

# Регулярное выражение для парсинга одного условия: поле, оператор, значение
WHERE_PATTERN: Final[str] = r'^(\w+)(=|!=|>=|<=|>|<)(.+)$'

# Регулярное выражение для парсинга aggregation
AGGR_PATTERN: Final[str] = r'^(\w+)=(avg|min|max)$'

# Регулярное выражение для парсинга order-by
ORDER_PATTERN: Final[str] = r'^(\w+)=(asc|desc)$'
