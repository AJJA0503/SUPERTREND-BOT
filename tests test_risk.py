import pytest
from src.risk import validate_leverage, position_size

def test_leverage_bounds():
    for v in (1, 5, 10, 40):
        assert validate_leverage(v) == v
    for v in (0, 41, -1):
        with pytest.raises(ValueError):
            validate_leverage(v)

def test_position_size_basic():
    qty = position_size(10_000, 5, 50_000, 500, 0.01)
    assert qty > 0
    # risk = qty * stop = 100 USD
    assert abs(qty * 500 - 100) < 1e-3 or abs(qty * 50_000 - 10_000*5) < 1e-3

def test_position_size_zero_stop():
    assert position_size(10_000, 5, 50_000, 0, 0.01) == 0.0