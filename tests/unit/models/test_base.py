import pytest
import numpy as np
from pydantic import ValidationError

from fairvalue.models.base import NonNegFloats, NonNegInts, Floats, Ints

# =============================================================================
# Test floats
# =============================================================================


def test_floats_valid_initialization():
    obj = Floats(data=[1.2, 2.3, 3.4])
    assert obj.data == [1.2, 2.3, 3.4]

    # check ints are correctly converted to float
    obj = Floats(data=[1, 2.3, 3.4])
    assert obj.data == [1.0, 2.3, 3.4]


def test_floats_invalid_initialization():
    with pytest.raises(ValidationError):
        Floats(data=["fairvalue", 2.3, 3.4])

    with pytest.raises(ValidationError):
        Floats(data=[True, 2.3, 3.4])

    with pytest.raises(ValidationError):
        Floats(data=[b"hello", 2.3, 3.4])

    with pytest.raises(ValidationError):
        Floats(data=[None, 2.3, 3.4])


def test_floats_getitem():
    obj = Floats(data=[1.2, 2.3, 3.4])
    assert obj[1] == 2.3


def test_floats_iteration():
    obj = Floats(data=[1.2, 2.3, 3.4])
    assert list(iter(obj)) == [1.2, 2.3, 3.4]


def test_floats_length():
    obj = Floats(data=[1.2, 2.3, 3.4])
    assert len(obj) == 3


def test_floats_addition():
    obj1 = Floats(data=[1.0, 2.0])
    obj2 = Floats(data=[3.0, 4.0])
    result = obj1 + obj2
    assert result.data == [1.0, 2.0, 3.0, 4.0]


def test_floats_addition_list():
    obj = Floats(data=[1.0, 2.0])
    result = obj + [3.0, 4.0]
    assert result.data == [1.0, 2.0, 3.0, 4.0]


def test_floats_addition_invalid():
    obj = Floats(data=[1.0, 2.0])
    with pytest.raises(TypeError):
        _ = obj + 5


def test_floats_sum():
    obj = Floats(data=[1.0, 2.0, 3.0])
    assert obj.sum() == 6.0


# =============================================================================
# Test Non neg floats
# =============================================================================


def test_nonnegfloats_initialization_valid():
    obj = NonNegFloats(data=[0.0, 2.3, 4.5])
    assert obj.data == [0.0, 2.3, 4.5]


def test_nonnegfloats_initialization_invalid():
    with pytest.raises(ValidationError):
        NonNegFloats(data=[-1.0, 2.3, 4.5])


# =============================================================================
# Test Non neg Int
# =============================================================================


def test_ints_initialization():
    obj = Ints(data=[1, 2, 3])
    assert obj.data == [1, 2, 3]


def test_ints_invalid_initialization():
    with pytest.raises(ValidationError):
        Ints(data=["hello", 2, 3])
    with pytest.raises(ValidationError):
        Ints(data=[1.5, 2, 3])


def test_ints_getitem():
    obj = Ints(data=[1, 2, 3])
    assert obj[1] == 2


def test_ints_iteration():
    obj = Ints(data=[1, 2, 3])
    assert list(iter(obj)) == [1, 2, 3]


def test_ints_length():
    obj = Ints(data=[1, 2, 3])
    assert len(obj) == 3


def test_ints_addition():
    obj1 = Ints(data=[1, 2])
    obj2 = Ints(data=[3, 4])
    result = obj1 + obj2
    assert result.data == [1, 2, 3, 4]


def test_ints_addition_list():
    obj = Ints(data=[1, 2])
    result = obj + [3, 4]
    assert result.data == [1, 2, 3, 4]


def test_ints_addition_invalid():
    obj = Ints(data=[1, 2])
    with pytest.raises(TypeError):
        _ = obj + 5


def test_ints_sum():
    obj = Ints(data=[1, 2, 3])
    assert obj.sum() == 6


# =============================================================================
# Test Non neg ints
# =============================================================================


def test_nonnegfloats_initialization_valid():
    obj = NonNegInts(data=[0, 1, 3, 5])
    assert obj.data == [0, 1, 3, 5]


def test_nonnegfloats_initialization_invalid():
    with pytest.raises(ValidationError):
        NonNegInts(data=[-1, 2])
