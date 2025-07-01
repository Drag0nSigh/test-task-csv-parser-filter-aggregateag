import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union

from scr.constants import WHERE_PATTERN


class Report(ABC):
    """Базовый класс для работы с отчётами."""

    def __init__(self, data: List[Any], field_types: Dict[str, type]):
        self.data = data
        self.field_types = field_types

    @staticmethod
    def _parse_condition(
            condition: str,
            field_types: Dict[str, type]
    ) -> List[List[Tuple[str, str, Union[str, float]]]]:
        """Парсит строку с условиями фильтрации, разделёнными ';' (AND) или '|' (OR)."""

        if not condition.strip():
            raise ValueError('Условие не может быть пустым')

        or_groups = []
        condition_groups = condition.strip().split('|')

        for group in condition_groups:
            group_conditions = []
            condition_list = group.strip().split(';')
            if not condition_list:
                continue

            for cond in condition_list:
                cond = cond.strip()
                if not cond:
                    continue

                match = re.match(WHERE_PATTERN, cond)
                if not match:
                    raise ValueError(f'Неверный формат условия: {cond}')

                field, operator, value = match.groups()
                value = value.strip()

                if field not in field_types:
                    raise ValueError(f'Поле "{field}" отсутствует в данных')

                # Проверка операторов для строковых полей
                if field_types[field] == str and operator not in ['=', '!=']:
                    raise ValueError(
                        f'Для строкового поля "{field}" поддерживаются только операторы = и !='
                    )

                # Преобразование значения для числовых полей
                if field_types[field] == float:
                    try:
                        value = float(value)
                    except ValueError:
                        raise ValueError(
                            f'Для числового поля "{field}" ожидается числовое значение, получено: {value}'
                        )

                group_conditions.append((field, operator, value))

            if group_conditions:
                or_groups.append(group_conditions)

        if not or_groups:
            raise ValueError('Не найдено ни одного валидного условия')
        return or_groups

    @staticmethod
    def _compare(
            good: Any,
            field: str,
            operator: str,
            value: Union[str, float]
    ) -> bool:
        """Проверяет, удовлетворяет ли объект одному условию."""
        good_value = getattr(good, field)

        if good_value is None:
            return False

        if isinstance(value, str):
            good_value = str(good_value).lower()
            value = value.lower()
            if operator == '=':
                return good_value == value
            return good_value != value

        if operator == '=':
            return good_value == value
        elif operator == '!=':
            return good_value != value
        elif operator == '>':
            return good_value > value
        elif operator == '<':
            return good_value < value
        elif operator == '>=':
            return good_value >= value
        elif operator == '<=':
            return good_value <= value
        return False


class Filter(Report):
    """Класс для фильтрации данных."""

    def filter_goods(self, condition: str) -> List[Any]:
        """ Фильтрует список объектов на основе условий."""

        or_groups = self._parse_condition(condition, self.field_types)
        filtered = []

        for good in self.data:
            for group in or_groups:
                satisfies_group = all(
                    self._compare(good, field, operator, value)
                    for field, operator, value in group
                )
                if satisfies_group:
                    filtered.append(good)
                    break

        return filtered


class Aggregator(Report):
    """Класс для агрегации данных."""

    def calculate_aggregation(self, field: str, operation: str) -> Optional[float]:
        """Вычисляет агрегацию (avg, min, max) для указанного поля."""

        if field not in self.field_types:
            raise ValueError(f'Поле "{field}" отсутствует в данных')
        if self.field_types[field] != float:
            raise ValueError(f'Агрегация возможна только для числовых полей, '
                             f'"{field}" имеет тип {self.field_types[field]}')
        if operation not in ['avg', 'min', 'max']:
            raise ValueError(f'Недопустимая операция агрегации: {operation}')

        values = [getattr(good, field) for good in self.data if getattr(good, field) is not None]
        if not values:
            return None

        if operation == 'avg':
            return sum(values) / len(values)
        elif operation == 'min':
            return min(values)
        elif operation == 'max':
            return max(values)
        return None


class Sorter(Report):
    """Класс для сортировки данных."""

    def sort_goods(self, field: str, order: str) -> List[Any]:
        """Сортирует список объектов по указанному полю и порядку."""

        if field not in self.field_types:
            raise ValueError(f'Поле "{field}" отсутствует в данных')
        if order not in ['asc', 'desc']:
            raise ValueError(f'Недопустимый порядок сортировки: {order}')

        reverse = order == 'desc'
        return sorted(self.data, key=lambda good: getattr(good, field) or '', reverse=reverse)