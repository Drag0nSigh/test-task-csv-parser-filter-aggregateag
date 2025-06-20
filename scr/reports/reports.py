from abc import ABC
import re
from typing import List, Optional, Union, Tuple

from scr.constants import FIELDS_FOR_FILTER, OPERATORS_FOR_FILTER, WHERE_PATTERN
from scr.models.goods import Good


class Report(ABC):
    def __init__(self, data: List[Good]):
        self.data = data


class Filter(Report):
    def _parse_condition(self, condition: str) -> List[List[Tuple[str, str, Union[str, float]]]]:
        """
        Парсит строку с несколькими условиями, разделёнными ';' (AND) или '|' (OR).
        Возвращает список групп условий, где каждая группа — список кортежей (поле, оператор, значение).
        Пример: "brand=xiaomi;rating>=4.8|price<=500" -> [[("brand", "=", "xiaomi"), ("rating", ">=", 4.8)],
        [("price", "<=", 500)]]
        """
        or_groups = []

        # Проверяем, что строка не пустая после очистки
        if not condition.strip():
            raise ValueError("Условие не может быть пустым")

        # Разделяем строку на группы условий (OR)
        condition_groups = condition.strip().split('|')

        for group in condition_groups:
            group_conditions = []
            # Разделяем группу на отдельные условия (AND)
            condition_list = group.strip().split(';')
            if not condition_list:
                continue  # Пропускаем пустые группы

            for cond in condition_list:
                cond = cond.strip()
                if not cond:
                    continue  # Пропускаем пустые условия

                match: re.Match | None = re.match(WHERE_PATTERN, cond)
                if not match:
                    raise ValueError(f'Неверный формат условия: {cond}')

                field, operator, value = match.groups()
                value = value.strip()

                if not value:
                    raise ValueError(f'Значение для поля {field} не может быть пустым')

                if field not in FIELDS_FOR_FILTER:
                    raise ValueError(f'Недопустимое поле: {field}. Допустимые поля: {FIELDS_FOR_FILTER}')
                if operator not in OPERATORS_FOR_FILTER:
                    raise ValueError(f'Недопустимый оператор: {operator}. Допустимые операторы: {OPERATORS_FOR_FILTER}')

                # Преобразуем значение в зависимости от поля
                if field in ['price', 'rating']:
                    try:
                        value = float(value)
                    except ValueError:
                        raise ValueError(f'Для поля {field} ожидается числовое значение, получено: {value}')

                # Для name и brand значение остаётся строкой
                group_conditions.append((field, operator, value))

            if group_conditions:
                or_groups.append(group_conditions)

        if not or_groups:
            raise ValueError('Не найдено ни одного валидного условия')
        return or_groups

    def _compare(self, good: Good, field: str, operator: str, value: Union[str, float]) -> bool:
        """
        Проверяет, удовлетворяет ли объект Good одному условию.
        """
        # Получаем значение поля из объекта
        good_value = getattr(good, field)

        # Обработка пропущенных значений
        if good_value is None:
            return False

        # Для строк (name, brand) используем только = и !=
        if field in ['name', 'brand']:
            if operator not in ['=', '!=']:
                raise ValueError(f'Для поля {field} поддерживаются только операторы = и !=')
            if operator == '=':
                return good_value.lower() == value.lower()
            return good_value.lower() != value.lower()

        # Для чисел (price, rating)
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

    def filter_goods(self, condition: str) -> List[Good]:
        """
        Фильтрует список объектов Good на основе условий, объединённых через AND и OR.
        """
        or_groups = self._parse_condition(condition)

        # Фильтруем: объект должен удовлетворять хотя бы одной группе условий (OR)
        filtered = []
        for good in self.data:
            for group in or_groups:
                # Проверяем, удовлетворяет ли объект всем условиям в группе (AND)
                satisfies_group = all(self._compare(good, field, operator, value) for field, operator, value in group)
                if satisfies_group:
                    filtered.append(good)
                    break  # Если группа удовлетворена, переходим к следующему объекту

        return filtered

    def calculate_aggregation(self, field: str, operation: str) -> Optional[float]:
        """
        Вычисляет агрегацию (avg, min, max) для указанного поля (price, rating).
        Возвращает результат или None, если список товаров пуст.
        """
        if not self.data:
            return None

        values = [getattr(good, field) for good in self.data]

        if operation == 'avg':
            return sum(values) / len(values)
        elif operation == 'min':
            return min(values)
        elif operation == 'max':
            return max(values)
        return None
