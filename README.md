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

---

# Part 2: API Prototype (Vercel)

This repo uses a Vercel Serverless Function to serve `POST /api/county_data` backed by `data.db` with `sql.js` (WASM). No server needed.

## Endpoint
- Path: `POST /api/county_data`
- Body (JSON, `content-type: application/json`):
  - `zip` (required): 5-digit ZIP, e.g. `"02138"`
  - `measure_name` (required): one of
    - Violent crime rate
    - Unemployment
    - Children in poverty
    - Diabetic screening
    - Mammography screening
    - Preventable hospital stays
    - Uninsured
    - Sexually transmitted infections
    - Physical inactivity
    - Adult obesity
    - Premature Death
    - Daily fine particulate matter
  - `coffee` (optional): if `"teapot"`, returns HTTP 418

## Test with curl (after deploy or with `vercel dev`)
```bash
# Success (200)
curl -s -H 'content-type: application/json' \
  -d '{"zip":"02138","measure_name":"Adult obesity"}' \
  https://<your-vercel-app>.vercel.app/api/county_data | head

# Teapot (418)
curl -i -H 'content-type: application/json' \
  -d '{"zip":"02138","measure_name":"Adult obesity","coffee":"teapot"}' \
  https://<your-vercel-app>.vercel.app/api/county_data

# Missing inputs (400)
curl -i -H 'content-type: application/json' -d '{"zip":"02138"}' https://<your-vercel-app>.vercel.app/api/county_data

# Not found (404)
curl -i -H 'content-type: application/json' \
  -d '{"zip":"99999","measure_name":"Adult obesity"}' \
  https://<your-vercel-app>.vercel.app/api/county_data
```

## Response shape (example subset)
For `{"zip":"02138","measure_name":"Adult obesity"}` the response is an array of objects with keys:
`state, county, state_code, county_code, year_span, measure_name, measure_id, numerator, denominator, raw_value, confidence_interval_lower_bound, confidence_interval_upper_bound, data_release_year, fipscode`.

## Deployment (Vercel)
- Ensure `data.db` is committed at repo root (present).
- Files:
  - `api/county_data.js` — Vercel function (Node + sql.js)
  - `vercel.json` — includes `data.db` and `sql-wasm.wasm` in the function bundle
  - `package.json` — ESM enabled (`"type": "module"`), depends on `sql.js`
- Steps:
  1. Push to your GitHub repo.
  2. In Vercel, import the repo and deploy (framework: Other).
  3. Test with curl against `https://<your-vercel-app>.vercel.app/api/county_data`.

## API files
- `api/county_data.js` — Vercel function exposing `POST /api/county_data` with required behaviors (418/400/404)
- `vercel.json` — bundle config
- `package.json` — Node dependencies

## Attribution
This assignment permits the use of generative AI. This repository includes code authored with assistance from a generative AI coding assistant (Cascade) and reviewed/edited by the author. Please include attribution in any additional files that incorporate external sources.
