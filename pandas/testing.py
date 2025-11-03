"""Test helper utilities for the lightweight :mod:`pandas` stub.

This module provides a very small subset of the real ``pandas.testing``
helpers.  Only the bits that are needed by the unit tests are implemented
here, namely :func:`assert_frame_equal`.  The goal is to offer informative
assertion failures while keeping the implementation compact and dependency
free.
"""

from __future__ import annotations

import math
from typing import Any

from . import DataFrame


def _is_null(value: Any) -> bool:
    """Return ``True`` when *value* should be considered missing."""

    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return False


def assert_frame_equal(left: DataFrame, right: DataFrame, **_: Any) -> None:
    """Assert that two :class:`~pandas.DataFrame` objects are equal.

    Parameters mirror the real pandas helper loosely.  Only the objects to
    compare are honoured; any additional keyword arguments are accepted for
    compatibility but ignored.
    """

    if not isinstance(left, DataFrame) or not isinstance(right, DataFrame):
        raise AssertionError("assert_frame_equal expects DataFrame instances")

    left_columns = left.columns
    right_columns = right.columns
    if left_columns != right_columns:
        raise AssertionError(
            "DataFrame columns differ:\n"
            f"left:  {left_columns}\nright: {right_columns}"
        )

    if len(left._rows) != len(right._rows):  # type: ignore[attr-defined]
        raise AssertionError(
            "DataFrame row counts differ:\n"
            f"left:  {len(left._rows)}\nright: {len(right._rows)}"
        )

    for index, (left_row, right_row) in enumerate(zip(left._rows, right._rows)):  # type: ignore[attr-defined]
        for column in left_columns:
            left_value = left_row.get(column)
            right_value = right_row.get(column)

            if _is_null(left_value) and _is_null(right_value):
                continue
            if left_value != right_value:
                raise AssertionError(
                    "DataFrame values differ at "
                    f"(row {index}, column '{column}'):\n"
                    f"left:  {left_value!r}\nright: {right_value!r}"
                )

__all__ = ["assert_frame_equal"]
