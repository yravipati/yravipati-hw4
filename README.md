# CS1060 Homework 4 — CSV to SQLite + API Prototype

This repository contains:
- **Part 1**: Python script to convert CSV files into SQLite database
- **Part 2**: Vercel serverless API endpoint for querying county health data

**Live API**: https://yravipati-hw4.vercel.app/county_data

---

# Part 1: CSV → SQLite Loader

Python 3 script that converts CSV files (with header row) into SQLite database tables, with automated testing.

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

## Files
- `csv_to_sqlite.py` — CSV → SQLite loader script
- `test_csv_to_sqlite.py` — Automated tests for Part 1
- `data.db` — Generated SQLite database (31MB, committed for deployment)

---

# Part 2: API Prototype (Vercel)

Serverless API endpoint deployed on Vercel that queries the SQLite database from Part 1.

**Live endpoint**: https://yravipati-hw4.vercel.app/county_data

## API Specification

### Endpoint
- **Method**: POST
- **Path**: `/county_data` (also works at `/api/county_data`)
- **Content-Type**: `application/json`

### Request Body (JSON):
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

### Response Codes
- **200**: Success - returns array of health data records
- **400**: Bad request - missing/invalid zip or measure_name
- **404**: Not found - ZIP not in dataset or no health data available
- **418**: I'm a teapot - when `coffee=teapot` is provided

## Testing Examples

```bash
# Success (200) - Returns health data for Cambridge, MA
curl -s -H 'content-type: application/json' \
  -d '{"zip":"02138","measure_name":"Adult obesity"}' \
  https://yravipati-hw4.vercel.app/county_data | head

# Teapot (418) - Special easter egg
curl -i -H 'content-type: application/json' \
  -d '{"zip":"02138","measure_name":"Adult obesity","coffee":"teapot"}' \
  https://yravipati-hw4.vercel.app/county_data

# Bad request (400) - Missing measure_name
curl -i -H 'content-type: application/json' \
  -d '{"zip":"02138"}' \
  https://yravipati-hw4.vercel.app/county_data

# Not found (404) - Invalid ZIP code
curl -i -H 'content-type: application/json' \
  -d '{"zip":"99999","measure_name":"Adult obesity"}' \
  https://yravipati-hw4.vercel.app/county_data
```

## Response shape (example subset)
For `{"zip":"02138","measure_name":"Adult obesity"}` the response is an array of objects with keys:
`state, county, state_code, county_code, year_span, measure_name, measure_id, numerator, denominator, raw_value, confidence_interval_lower_bound, confidence_interval_upper_bound, data_release_year, fipscode`.

## Implementation Details

### Architecture
- **Database**: SQLite (`data.db`) with 54K+ ZIP codes and 300K+ health records
- **Backend**: Vercel serverless function using `better-sqlite3` (Node.js)
- **Deployment**: Automatic deployment from GitHub to Vercel

### Files
- `api/county_data.js` — Serverless function implementation
- `vercel.json` — Deployment configuration (includes database)
- `package.json` — Node.js dependencies
- `public/index.html` — Static homepage
- `link.txt` — Contains live API endpoint URL

### Query Logic
1. Validate input (ZIP format, allowed measure names)
2. Look up county/state from ZIP code in `zip_county` table
3. Query health data from `county_health_rankings` table
4. Return results with proper HTTP status codes

---

# Testing

## Automated Test Suite
Run comprehensive tests for both parts:
```bash
python3 test_full_implementation.py
```

This tests:
- ✅ Part 1: CSV loading, database creation, schema validation
- ✅ Part 2: All API endpoints, error codes, data validation
- ✅ Live API testing against deployed endpoint

## Individual Tests
```bash
# Test Part 1 only
python3 test_csv_to_sqlite.py

# Manual API testing
curl -H 'content-type: application/json' \
  -d '{"zip":"02138","measure_name":"Adult obesity"}' \
  https://yravipati-hw4.vercel.app/county_data
```

---

# Repository Structure

```
yravipati-hw4/
├── README.md                    # This file
├── link.txt                     # Live API endpoint
├── requirements.txt             # Python dependencies
├── .gitignore                   # Git ignore patterns
│
├── csv_to_sqlite.py            # Part 1: CSV loader
├── test_csv_to_sqlite.py       # Part 1: Tests
├── data.db                     # SQLite database (31MB)
│
├── api/county_data.js          # Part 2: Serverless function
├── vercel.json                 # Vercel configuration
├── package.json                # Node.js dependencies
├── public/index.html           # Static homepage
│
├── test_full_implementation.py # Comprehensive test suite
├── zip_county.csv              # Source data (ZIP → County)
└── county_health_rankings.csv  # Source data (Health metrics)
```

---

# Submission Information

- **Course Repository**: https://github.com/cs1060f25/yravipati-hw4
- **Personal Repository**: https://github.com/yravipati/yravipati-hw4
- **Live API Endpoint**: https://yravipati-hw4.vercel.app/county_data
- **Test Status**: 20/20 tests passing ✅

## Attribution
This assignment permits the use of generative AI. This repository includes code authored with assistance from a generative AI coding assistant (Cascade) and reviewed/edited by the author.
