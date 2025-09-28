#!/usr/bin/env python3
"""
Basic automated test for csv_to_sqlite.py

- Removes data.db
- Loads zip_county.csv and county_health_rankings.csv into data.db
- Verifies expected schemas (column names and order)
- Verifies row counts

Note: Row counts are based on the Feb 2025 datasets referenced in the assignment.
If you use different dataset versions, counts may differ.

Attribution:
- This file was created with assistance from a generative AI coding assistant (Cascade), and then reviewed/edited by the author to meet assignment requirements.
"""
import os
import sqlite3
import subprocess
import sys

EXPECTED_ZIP_COUNTY_COLS = [
    "zip",
    "default_state",
    "county",
    "county_state",
    "state_abbreviation",
    "county_code",
    "zip_pop",
    "zip_pop_in_county",
    "n_counties",
    "default_city",
]

EXPECTED_CHR_COLS = [
    "state",
    "county",
    "state_code",
    "county_code",
    "year_span",
    "measure_name",
    "measure_id",
    "numerator",
    "denominator",
    "raw_value",
    "confidence_interval_lower_bound",
    "confidence_interval_upper_bound",
    "data_release_year",
    "fipscode",
]

EXPECTED_ZIP_COUNT = 54553
EXPECTED_CHR_COUNT = 303864


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)


def get_cols(conn: sqlite3.Connection, table: str) -> list[str]:
    cur = conn.execute(f"PRAGMA table_info({table});")
    # pragma columns: cid, name, type, notnull, dflt_value, pk
    return [row[1] for row in cur.fetchall()]


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(here, "data.db")

    # 1) Remove db if exists
    if os.path.exists(db_path):
        os.remove(db_path)
        print("Removed existing data.db")

    # 2) Load CSVs
    run([sys.executable, os.path.join(here, "csv_to_sqlite.py"), db_path, os.path.join(here, "zip_county.csv")])
    run([sys.executable, os.path.join(here, "csv_to_sqlite.py"), db_path, os.path.join(here, "county_health_rankings.csv")])

    # 3) Open DB and validate
    conn = sqlite3.connect(db_path)
    try:
        # Schema checks
        zip_cols = get_cols(conn, "zip_county")
        chr_cols = get_cols(conn, "county_health_rankings")
        assert zip_cols == EXPECTED_ZIP_COUNTY_COLS, f"zip_county columns mismatch:\n{zip_cols}"
        assert chr_cols == EXPECTED_CHR_COLS, f"county_health_rankings columns mismatch:\n{chr_cols}"

        # Count checks
        zip_count = conn.execute("select count(*) from zip_county;").fetchone()[0]
        chr_count = conn.execute("select count(*) from county_health_rankings;").fetchone()[0]
        assert zip_count == EXPECTED_ZIP_COUNT, f"zip_county count {zip_count} != {EXPECTED_ZIP_COUNT}"
        assert chr_count == EXPECTED_CHR_COUNT, f"county_health_rankings count {chr_count} != {EXPECTED_CHR_COUNT}"

        print("All tests passed.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
