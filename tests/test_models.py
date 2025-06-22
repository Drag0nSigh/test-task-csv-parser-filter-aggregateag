import pytest

from scr.models.goods import Good


@pytest.fixture
def sample_good() -> Good:
    return Good(
        name='phone',
        brand='xiaomi',
        price=100,
        rating=4.9,
    )


def test_good_initialization(sample_good):
    assert vars(sample_good) == {
        'name': 'phone',
        'brand': 'xiaomi',
        'price': 100,
        'rating': 4.9
    }


def test_good_attributes(sample_good):
    assert sample_good.name == 'phone'
    assert sample_good.brand == 'xiaomi'
    assert sample_good.price == 100
    assert sample_good.rating == 4.9

def test_good_types(sample_good):
    assert isinstance(sample_good.name, str)
    assert isinstance(sample_good.brand, str)
    assert isinstance(sample_good.price, int)
    assert isinstance(sample_good.rating, float)

def test_good_str(sample_good):
    assert (sample_good.__str__() ==
            f'Good(name=phone, brand=xiaomi, price=100, rating=4.9)')
