class InvalidAggregationError(ValueError):
    """Исключение для ошибок валидации или выполнения агрегации."""

    pass


class InvalidSortError(ValueError):
    """Исключение для ошибок валидации или выполнения сортировки."""

    pass


class InvalidFilterConditionError(ValueError):
    """Исключение для ошибок в условиях фильтрации."""

    pass


class UnsupportedOperatorError(ValueError):
    """Исключение для неподдерживаемых операторов в фильтрации."""

    pass


class UnsupportedFieldTypeError(ValueError):
    """Исключение для попыток работы с полем неподдерживаемого типа."""

    pass


class InvalidCsvFormatError(ValueError):
    """Исключение для ошибок формата CSV-файла."""

    pass
