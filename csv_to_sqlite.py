#!/usr/bin/env python3
"""
csv_to_sqlite.py

Converts a CSV file (with a header row) to a SQLite table in a specified database.

Usage:
    python3 csv_to_sqlite.py <db_path> <csv_path>

Notes:
- Table name is derived from the CSV filename (basename without extension), lowercased and sanitized to [A-Za-z_][A-Za-z0-9_]*.
- Column names are taken from the CSV header and sanitized similarly.
- All columns are created as TEXT to match the assignment's example schema.
- Existing table with the same name will be dropped and recreated.
- Inserts are batched inside a single transaction using parameterized queries.

Attribution:
- This file was created with assistance from a generative AI coding assistant (Cascade), and then reviewed/edited by the author to meet assignment requirements.
"""

import csv
import os
import re
import sqlite3
import sys
from typing import List, Tuple


IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def sanitize_identifier(name: str) -> str:
    """Sanitize to a safe SQL identifier without quoting.

    - Lowercase
    - Replace invalid characters with underscore
    - Ensure it starts with a letter or underscore
    """
    if name is None:
        name = ""
    # Lowercase and replace non-alnum/underscore with underscore
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", name.strip().lower())
    # Ensure starts with a letter or underscore
    if not cleaned or not re.match(r"^[A-Za-z_]", cleaned):
        cleaned = f"_{cleaned}" if cleaned else "_col"
    # Collapse multiple underscores
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned


def derive_table_name(csv_path: str) -> str:
    base = os.path.basename(csv_path)
    stem, _ = os.path.splitext(base)
    return sanitize_identifier(stem)


def read_csv_header_and_rows(csv_path: str) -> Tuple[List[str], List[List[str]]]:
    # Use utf-8-sig to handle optional BOM
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            raise ValueError("CSV appears to be empty (no header row)")
        if not header:
            raise ValueError("CSV header row is empty")
        rows: List[List[str]] = [row for row in reader]
    return header, rows


def build_create_table_sql(table: str, columns: List[str]) -> str:
    # All columns as TEXT, unquoted identifiers (sanitized)
    parts = [f"{col} TEXT" for col in columns]
    cols_sql = ", ".join(parts)
    return f"CREATE TABLE {table} ({cols_sql});"


def main(argv: List[str]) -> int:
    if len(argv) != 3:
        print("Usage: python3 csv_to_sqlite.py <db_path> <csv_path>", file=sys.stderr)
        return 2

    db_path = argv[1]
    csv_path = argv[2]

    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found: {csv_path}", file=sys.stderr)
        return 1

    # Derive table name
    table_name = derive_table_name(csv_path)

    # Read CSV
    header, rows = read_csv_header_and_rows(csv_path)

    # Sanitize column names
    sanitized_cols = [sanitize_identifier(col) for col in header]

    # Build SQL
    create_sql = build_create_table_sql(table_name, sanitized_cols)
    placeholders = ", ".join(["?"] * len(sanitized_cols))
    insert_sql = f"INSERT INTO {table_name} ({', '.join(sanitized_cols)}) VALUES ({placeholders});"

    # Connect and write
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        # Drop and recreate table for idempotency
        cur.execute(f"DROP TABLE IF EXISTS {table_name};")
        cur.execute(create_sql)

        # Insert in a transaction
        conn.execute("BEGIN")
        if rows:
            # Normalize row lengths: pad/truncate to header length
            normalized = [
                (row + [None] * (len(sanitized_cols) - len(row)))[: len(sanitized_cols)]
                for row in rows
            ]
            cur.executemany(insert_sql, normalized)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
