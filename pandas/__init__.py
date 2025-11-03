"""Lightweight test-focused stub of the :mod:`pandas` API.

This module provides a very small subset of the pandas interface required by
the unit tests that accompany this kata.  The goal is not to be feature
complete, but rather to offer just enough behaviour for the inventory service
helpers to work without pulling the real pandas dependency (which would be
overkill in this execution environment).

The implementation purposely favours clarity over raw performance.  Data are
stored as lists of dictionaries and the supported operations mimic the pandas
API closely enough for the tests to interact with them naturally.
"""

from __future__ import annotations

import csv
from collections import OrderedDict, namedtuple
from io import StringIO
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence


def _as_type_converter(dtype: Any):
    if dtype in (str, "str"):
        return lambda value: "" if value is None else str(value)
    if dtype in (int, "int"):
        return lambda value: 0 if value in (None, "") else int(value)
    if dtype in (float, "float"):
        return lambda value: 0.0 if value in (None, "") else float(value)
    if callable(dtype):
        return lambda value: dtype(value)
    raise TypeError(f"Unsupported dtype conversion: {dtype!r}")


class _StringMethods:
    def __init__(self, series: "Series") -> None:
        self._series = series

    def _apply(self, func) -> "Series":
        return Series([func(value) if value is not None else "" for value in self._series._data], name=self._series.name)

    def strip(self) -> "Series":
        return self._apply(lambda value: str(value).strip())

    def lower(self) -> "Series":
        return self._apply(lambda value: str(value).lower())

    def startswith(self, prefix: str) -> "Series":
        return Series([
            str(value).startswith(prefix) if value is not None else False
            for value in self._series._data
        ])


class _ILocAccessor:
    def __init__(self, series: "Series") -> None:
        self._series = series

    def __getitem__(self, index: int) -> Any:
        return self._series._data[index]


class _UniqueValues:
    def __init__(self, values: Iterable[Any]) -> None:
        seen = OrderedDict()
        for value in values:
            if value not in seen:
                seen[value] = None
        self._values = list(seen.keys())

    def tolist(self) -> list[Any]:
        return list(self._values)

    def __iter__(self) -> Iterator[Any]:
        return iter(self._values)


class Series:
    def __init__(self, data: Iterable[Any] | None = None, *, name: str | None = None) -> None:
        self._data = list(data or [])
        self.name = name

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._data)

    def __iter__(self) -> Iterator[Any]:
        return iter(self._data)

    def __getitem__(self, key: int | slice | "Series" | list[bool]):
        if isinstance(key, slice):
            return Series(self._data[key], name=self.name)
        if isinstance(key, Series):
            mask = [bool(item) for item in key._data]
            return Series([value for value, keep in zip(self._data, mask) if keep], name=self.name)
        if isinstance(key, list):
            return Series([value for value, keep in zip(self._data, key) if keep], name=self.name)
        return self._data[key]

    def __gt__(self, other: Any) -> "Series":
        return Series([(value or 0) > other if value is not None else False for value in self._data])

    def __ge__(self, other: Any) -> "Series":
        return Series([(value or 0) >= other if value is not None else False for value in self._data])

    def __lt__(self, other: Any) -> "Series":
        return Series([(value or 0) < other if value is not None else False for value in self._data])

    def __le__(self, other: Any) -> "Series":
        return Series([(value or 0) <= other if value is not None else False for value in self._data])

    def __eq__(self, other: Any) -> "Series":  # pragma: no cover - defensive
        return Series([(value == other) for value in self._data])

    def __ne__(self, other: Any) -> "Series":  # pragma: no cover - defensive
        return Series([(value != other) for value in self._data])

    @property
    def empty(self) -> bool:
        return not self._data

    @property
    def iloc(self) -> _ILocAccessor:
        return _ILocAccessor(self)

    @property
    def str(self) -> _StringMethods:
        return _StringMethods(self)

    def any(self) -> bool:
        for value in self._data:
            if isinstance(value, bool):
                if value:
                    return True
            elif value not in (None, 0, 0.0, "", False):
                return True
        return False

    def sum(self) -> float:
        total = 0.0
        for value in self._data:
            if value is None:
                continue
            total += float(value)
        return total

    def mean(self) -> float:
        values = [float(value) for value in self._data if value is not None]
        if not values:
            return 0.0
        return sum(values) / len(values)

    def tolist(self) -> list[Any]:
        return list(self._data)

    def fillna(self, value: Any) -> "Series":
        return Series([self._coalesce(item, value) for item in self._data], name=self.name)

    def astype(self, dtype: Any) -> "Series":
        converter = _as_type_converter(dtype)
        return Series([converter(item) for item in self._data], name=self.name)

    def notna(self) -> "Series":
        return Series([item is not None for item in self._data])

    def dropna(self) -> "Series":
        return Series([item for item in self._data if item is not None], name=self.name)

    def unique(self) -> _UniqueValues:
        return _UniqueValues(self._data)

    def copy(self) -> "Series":  # pragma: no cover - simple helper
        return Series(self._data[:], name=self.name)

    def _coalesce(self, value: Any, fallback: Any) -> Any:
        return fallback if value is None else value


class DataFrame:
    def __init__(
        self,
        data: Sequence[dict[str, Any] | Sequence[Any]] | None = None,
        columns: Sequence[str] | None = None,
    ) -> None:
        self._rows: list[dict[str, Any]] = []
        self._columns: list[str] = list(columns or [])

        if data:
            for row in data:
                if isinstance(row, dict):
                    copied = dict(row)
                else:
                    if columns is None:
                        raise TypeError(
                            "columns must be provided when initialising from non-mapping rows"
                        )
                    copied = {column: value for column, value in zip(columns, row)}
                self._rows.append(copied)
                for key in copied:
                    if key not in self._columns:
                        self._columns.append(key)

        for column in list(self._columns):
            if column not in self._columns:
                self._columns.append(column)

        for row in self._rows:
            for column in self._columns:
                row.setdefault(column, None)

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._rows)

    def __getitem__(self, key):
        if isinstance(key, str):
            return Series([row.get(key) for row in self._rows], name=key)
        if isinstance(key, list):
            return DataFrame([{column: row.get(column) for column in key} for row in self._rows], columns=key)
        if isinstance(key, bool):
            return self.copy() if key else DataFrame(columns=self._columns)
        if isinstance(key, Series):
            mask = [bool(value) for value in key._data]
            return DataFrame([row for row, keep in zip(self._rows, mask) if keep], columns=self._columns)
        raise TypeError(f"Unsupported key type for DataFrame.__getitem__: {type(key)!r}")

    def __setitem__(self, key: str, value: Series | Iterable[Any]) -> None:
        if isinstance(value, Series):
            data = value._data
        else:
            data = list(value)

        if len(data) != len(self._rows):
            raise ValueError("Length of values does not match DataFrame length")

        if key not in self._columns:
            self._columns.append(key)

        for row, item in zip(self._rows, data):
            row[key] = item

    def __iter__(self) -> Iterator[str]:  # pragma: no cover - iteration helper
        return iter(self._columns)

    @property
    def loc(self) -> "_LocIndexer":
        return _LocIndexer(self)

    @property
    def columns(self) -> list[str]:
        return list(self._columns)

    @property
    def empty(self) -> bool:
        return not self._rows

    def copy(self) -> "DataFrame":
        return DataFrame([dict(row) for row in self._rows], columns=self._columns)

    def iterrows(self) -> Iterator[tuple[int, dict[str, Any]]]:
        for index, row in enumerate(self._rows):
            yield index, dict(row)

    def to_dict(self, orient: str = "records") -> list[dict[str, Any]]:
        if orient != "records":  # pragma: no cover - defensive
            raise ValueError("Only orient='records' is supported")
        return [dict(row) for row in self._rows]

    @classmethod
    def from_records(
        cls,
        records: Iterable[dict[str, Any] | Sequence[Any]],
        columns: Sequence[str] | None = None,
    ) -> "DataFrame":
        if records is None:
            records = []

        rows: list[dict[str, Any]] = []
        for record in records:
            if isinstance(record, dict):
                rows.append(dict(record))
                continue
            if columns is None:
                raise TypeError("columns must be provided when records are not mappings")
            row = {column: value for column, value in zip(columns, record)}
            rows.append(row)

        return cls(rows, columns=columns)

    def where(self, condition_df: "DataFrame", other: Any = None) -> "DataFrame":
        if len(condition_df._rows) != len(self._rows):
            raise ValueError("Condition DataFrame must be the same shape")

        result_rows: list[dict[str, Any]] = []
        for row, cond_row in zip(self._rows, condition_df._rows):
            new_row: dict[str, Any] = {}
            for column in self._columns:
                keep = bool(cond_row.get(column, False))
                if keep:
                    new_row[column] = row.get(column)
                else:
                    new_row[column] = None if other is None else other
            result_rows.append(new_row)
        return DataFrame(result_rows, columns=self._columns)

    def notnull(self) -> "DataFrame":
        return DataFrame(
            [
                {column: row.get(column) is not None for column in self._columns}
                for row in self._rows
            ],
            columns=self._columns,
        )

    def itertuples(self) -> Iterator[Any]:
        column_names = [column if column.isidentifier() else column.replace(" ", "_") for column in self._columns]
        tuple_type = namedtuple("DataFrameRow", ["Index", *column_names])
        for index, row in enumerate(self._rows):
            values = [row.get(column) for column in self._columns]
            yield tuple_type(index, *values)

    def get(self, key: str, default: Any = None) -> Series | Any:
        if key in self._columns:
            return self[key]
        return default

    def merge(self, other: "DataFrame", *, left_on: str, right_on: str, how: str = "left", suffixes: tuple[str, str] = ("", "_y")) -> "DataFrame":
        right_suffix = suffixes[1] if len(suffixes) > 1 else "_y"
        result_rows: list[dict[str, Any]] = []

        other_rows = other._rows
        other_columns = other.columns

        for left_row in self._rows:
            left_key = left_row.get(left_on)
            matches = [row for row in other_rows if row.get(right_on) == left_key]
            if matches:
                for match in matches:
                    combined = dict(left_row)
                    for column in other_columns:
                        value = match.get(column)
                        target_column = column
                        if column in combined and column != right_on:
                            target_column = f"{column}{right_suffix}"
                        if column == right_on and right_on != left_on:
                            target_column = column
                            if column in combined:
                                target_column = f"{column}{right_suffix}"
                        combined[target_column] = value
                    result_rows.append(combined)
            elif how == "left":
                combined = dict(left_row)
                for column in other_columns:
                    target_column = column
                    if column in combined and column != right_on:
                        target_column = f"{column}{right_suffix}"
                    if column == right_on and right_on != left_on:
                        target_column = column
                        if column in combined:
                            target_column = f"{column}{right_suffix}"
                    if target_column not in combined:
                        combined[target_column] = None
                result_rows.append(combined)

        merged_columns = list(self._columns)
        for column in other_columns:
            target = column
            if column in merged_columns and column != right_on:
                target = f"{column}{right_suffix}"
            if column == right_on and right_on != left_on:
                target = column
                if target in merged_columns:
                    target = f"{column}{right_suffix}"
            if target not in merged_columns:
                merged_columns.append(target)

        return DataFrame(result_rows, columns=merged_columns)

    def groupby(self, column: str, *, sort: bool = True) -> "GroupBy":
        groups: OrderedDict[Any, list[dict[str, Any]]] = OrderedDict()
        for row in self._rows:
            key = row.get(column)
            groups.setdefault(key, []).append(row)
        keys = sorted(groups.keys()) if sort else list(groups.keys())
        grouped_items = []
        for key in keys:
            grouped_items.append((key, DataFrame(groups[key], columns=self._columns)))
        return GroupBy(grouped_items)


class GroupBy:
    def __init__(self, items: Iterable[tuple[Any, DataFrame]]):
        self._items = list(items)

    def __iter__(self) -> Iterator[tuple[Any, DataFrame]]:
        return iter(self._items)


class _LocIndexer:
    def __init__(self, dataframe: DataFrame) -> None:
        self._dataframe = dataframe

    def __getitem__(self, key):
        if not isinstance(key, tuple):
            raise TypeError("loc indexer requires row and column selectors")
        row_selector, column_selector = key

        single_row = False

        if isinstance(row_selector, slice) and row_selector == slice(None, None, None):
            base_rows = list(self._dataframe._rows)
        elif isinstance(row_selector, Series):
            mask = [bool(value) for value in row_selector._data]
            base_rows = [row for row, keep in zip(self._dataframe._rows, mask) if keep]
        elif isinstance(row_selector, list):
            base_rows = [self._dataframe._rows[index] for index in row_selector]
        elif isinstance(row_selector, int):
            base_rows = [self._dataframe._rows[row_selector]]
            single_row = True
        elif row_selector in (None, True):
            base_rows = list(self._dataframe._rows)
        else:
            raise TypeError(f"Unsupported row selector for loc: {type(row_selector)!r}")

        base_df = DataFrame([dict(row) for row in base_rows], columns=self._dataframe._columns)

        if column_selector is None or (isinstance(column_selector, slice) and column_selector == slice(None, None, None)):
            return base_df
        if isinstance(column_selector, str):
            column_series = base_df[column_selector]
            if len(column_series) == 1:
                return column_series[0]
            return column_series
        if isinstance(column_selector, list):
            return base_df[column_selector]

        raise TypeError(f"Unsupported column selector for loc: {type(column_selector)!r}")


def read_csv(path: str | Path, *, sep: str = ",", delimiter: str | None = None, encoding: str = "utf-8", **_: Any) -> DataFrame:
    """Read a CSV file into a :class:`DataFrame`.

    Only the minimal behaviour required by the tests is implemented.  Keyword
    arguments beyond *sep*, *delimiter* and *encoding* are accepted for
    compatibility but ignored.
    """

    csv_path = Path(path)
    actual_delimiter = delimiter if delimiter is not None else sep

    with csv_path.open(encoding=encoding, newline="") as handle:
        reader = csv.reader(handle, delimiter=actual_delimiter)
        try:
            header = next(reader)
        except StopIteration:
            return DataFrame(columns=[])

        rows = [{column: value for column, value in zip(header, values)} for values in reader]
        return DataFrame(rows, columns=header)


def to_numeric(values: Series | Iterable[Any], *, errors: str = "raise") -> Series:
    if isinstance(values, Series):
        raw = values._data
    else:
        raw = list(values)

    result: list[Any] = []
    for item in raw:
        if item in (None, ""):
            result.append(None)
            continue
        try:
            result.append(float(item))
        except (TypeError, ValueError):
            if errors == "coerce":
                result.append(None)
            else:  # pragma: no cover - defensive path
                raise
    return Series(result)


def read_csv(path_or_buffer, sep: str = ",") -> DataFrame:
    if hasattr(path_or_buffer, "read"):
        contents = path_or_buffer.read()
    else:
        file_path = Path(path_or_buffer)
        if not file_path.exists():
            raise FileNotFoundError(f"No such file or directory: '{path_or_buffer}'")
        contents = file_path.read_text(encoding="utf-8")

    if isinstance(contents, bytes):
        contents = contents.decode("utf-8")

    if not contents.strip():
        return DataFrame(columns=[])

    reader = csv.reader(StringIO(contents), delimiter=sep)
    try:
        header = next(reader)
    except StopIteration:
        return DataFrame(columns=[])

    rows = []
    for raw_row in reader:
        row = {column: value for column, value in zip(header, raw_row)}
        rows.append(row)

    return DataFrame(rows, columns=header)


from . import testing  # noqa: E402  # placed at end to avoid circular import


__all__ = ["DataFrame", "Series", "to_numeric", "read_csv", "testing"]
