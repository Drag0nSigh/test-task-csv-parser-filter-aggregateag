from abc import ABC
import json
from typing import List

from scr.models.goods import Good


class Report(ABC):
    def __init__(self, data: List[Good]):
        self.data = data

class Filter(Report):
    pass

