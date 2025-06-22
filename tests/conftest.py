import pytest

from scr.models.goods import Good


@pytest.fixture
def valid_list_goods():
    return [
        Good(
            name='iphone',
            brand='apple',
            price=100,
            rating=4.9
        ),
        Good(
            name='samsung',
            brand='samsung',
            price=200,
            rating=4.6
        ),
        Good(
            name='xiaomi',
            brand='xiaomi',
            price=150,
            rating=4.8
        )
    ]


@pytest.fixture
def valid_good():
    return Good(
        name='iphone',
        brand='apple',
        price=100,
        rating=4.9
    )
