from dataclasses import dataclass


@dataclass
class Good:
    name: str
    brand: str
    price: int
    rating: float

    def __str__(self) -> str:
        return (f'Good(name={self.name}, brand={self.brand}, '
                f'price={self.price}, rating={self.rating})')
