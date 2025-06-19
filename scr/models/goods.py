from dataclasses import dataclass


@dataclass
class Good:
    name: str
    brand: str
    price: int
    rating: float
