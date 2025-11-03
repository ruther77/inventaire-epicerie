"""Helpers emulating a tiny subset of :mod:`pandas.testing`.

The real pandas library offers a comprehensive collection of assertion
utilities.  For the purposes of the unit tests in this kata we only need a
couple of light-weight helpers to compare the simplified :mod:`pandas` stub
objects defined in ``pandas.__init__``.  The implementations below focus on
clarity and delivering useful error messages when expectations are not met.
"""

from __future__ import annotations

from typing import Iterable

from . import DataFrame, Series


def _normalise_columns(columns: Iterable[str]) -> list[str]:
    return list(columns)


def _dataframe_to_records(df: DataFrame) -> list[dict]:
    return df.to_dict(orient="records")


def assert_frame_equal(left: DataFrame, right: DataFrame) -> None:
    """Validate that two ``DataFrame`` instances contain identical data."""

    if not isinstance(left, DataFrame) or not isinstance(right, DataFrame):
        raise AssertionError("assert_frame_equal expects DataFrame instances")

    left_columns = _normalise_columns(left.columns)
    right_columns = _normalise_columns(right.columns)
    if left_columns != right_columns:
        raise AssertionError(
            f"DataFrame columns differ: {left_columns!r} != {right_columns!r}"
        )

    left_records = _dataframe_to_records(left)
    right_records = _dataframe_to_records(right)
    if left_records != right_records:
        raise AssertionError(f"DataFrame rows differ: {left_records!r} != {right_records!r}")


def assert_series_equal(left: Series, right: Series) -> None:
    """Validate that two ``Series`` objects are identical."""

    if not isinstance(left, Series) or not isinstance(right, Series):
        raise AssertionError("assert_series_equal expects Series instances")

    if left.name != right.name:
        raise AssertionError(f"Series names differ: {left.name!r} != {right.name!r}")

    if left.tolist() != right.tolist():
        raise AssertionError(f"Series values differ: {left.tolist()!r} != {right.tolist()!r}")
