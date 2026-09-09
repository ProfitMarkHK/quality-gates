import pytest
from pyservice.core import total_price


def test_total_price_basic():
    assert total_price(10.0, 2, 0.1) == 22.0


def test_total_price_rejects_negative_quantity():
    with pytest.raises(ValueError):
        total_price(10.0, -1, 0.1)
