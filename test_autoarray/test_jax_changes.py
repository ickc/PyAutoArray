import autoarray as aa
import pytest

from autoarray import Grid2D, Mask2D
from autofit.jax_wrapper import numpy as np


@pytest.fixture(name="array")
def make_array():
    return aa.Array2D.no_mask(
        [[1.0, 2.0], [3.0, 4.0]],
        pixel_scales=1.0,
    )


def test_copy(array):
    copied_array = array.copy()

    array[0] = 5.0

    assert array[0] == 5.0
    assert copied_array[0] == 1.0


def test_in_place_multiply(array):
    array[0] *= 2.0

    assert array[0] == 2.0


def test_boolean_issue():
    grid = Grid2D.from_mask(
        mask=Mask2D.all_false((10, 10), pixel_scales=1.0),
    )
    print(np.array(grid))
