import csv
from typing import Any, Dict, List


def write_csv(path: str, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    """Write rows to a CSV file, overwriting any existing content.

    Parameters
    ----------
    path: str
        Destination file path.
    rows: List[Dict[str, Any]]
        Rows to write, each mapping field names to values.
    fieldnames: List[str]
        Ordered list of column names.

    Returns
    -------
    None

    Raises
    ------
    OSError
        If the file cannot be written.
    """

    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def append_csv(path: str, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    """Append rows to a CSV file, creating the file if needed.

    Parameters
    ----------
    path: str
        Destination file path.
    rows: List[Dict[str, Any]]
        Rows to append.
    fieldnames: List[str]
        Ordered list of column names.

    Returns
    -------
    None

    Raises
    ------
    OSError
        If the file cannot be written.
    """

    import os

    exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            w.writeheader()
        for r in rows:
            w.writerow(r)
