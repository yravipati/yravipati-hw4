# CS1060 Homework 4 — Part 1: CSV → SQLite Loader

This repo contains a Python 3 script that converts CSV files (with a header row) into tables inside a SQLite database, plus an automated test.

## Overview
- `csv_to_sqlite.py` reads a CSV and writes it into a specified SQLite DB (`data.db` in examples).
- Table name is derived from the CSV filename (basename without extension), sanitized and lowercased.
- All columns are created as `TEXT`, matching the assignment’s example schema.
- Existing table with the same name is dropped and recreated on each run (idempotent).
- Inserts are parameterized and batched inside a single transaction for performance.

## Data sources (Feb 2025)
- RowZero Zip Code to County — zip_county.csv
  - Blog: https://rowzero.io/blog/zip-code-to-state-county-metro
  - CSV: https://rowzero.io/blog/zip_code_to_county_csv (see blog page for latest)
- County Health Rankings & Roadmaps Analytic Data — county_health_rankings.csv
  - Overview: https://www.countyhealthrankings.org/health-data
  - Documentation: https://www.countyhealthrankings.org/health-data/methodology-and-sources/data-documentation

Place both CSVs in the repo root (same folder as this README) to match examples below.

## Requirements
- Python 3.8+
- SQLite3 CLI (optional, for manual inspection)

## Usage
```bash
# Create or overwrite data.db and load each CSV
python3 csv_to_sqlite.py data.db zip_county.csv
python3 csv_to_sqlite.py data.db county_health_rankings.csv
```

Tables created:
- `zip_county`
- `county_health_rankings`

## Manual verification (as in assignment example)
```bash
sqlite3 data.db
```
Then in the SQLite shell:
```sql
.schema zip_county
select count(*) from zip_county;

.schema county_health_rankings
select count(*) from county_health_rankings;
.q
```
Expected (Feb 2025 dataset versions):
- `zip_county` row count: `54553`
- `county_health_rankings` row count: `303864`

## Automated test
Run the provided test script to recreate the DB, load both CSVs, and verify schema and counts programmatically via PRAGMA and queries:
```bash
python3 test_csv_to_sqlite.py
```
Expected output ends with:
```
All tests passed.
```

## Behavior and assumptions
- CSV must include a header row with valid column names (letters, numbers, underscores). Non-alphanumeric chars are converted to `_`, and names are lowercased.
- Table name is derived from the CSV filename (e.g., `zip_county.csv` → `zip_county`).
- All columns are created as `TEXT`.
- On each run, the table is dropped and recreated (idempotent import).
- Row lengths are normalized to the header length (pad with `NULL` or truncate if needed).

## File structure
- `csv_to_sqlite.py` — CSV → SQLite loader (Part 1)
- `test_csv_to_sqlite.py` — Automated test for loader
- `.gitignore` — excludes `*.db`, caches, venvs

## Attribution
This assignment permits the use of generative AI. This repository includes code authored with assistance from a generative AI coding assistant (Cascade) and reviewed/edited by the author. Please include attribution in any additional files that incorporate external sources.
