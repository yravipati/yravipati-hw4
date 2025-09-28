#!/usr/bin/env python3
"""
FastAPI app exposing /county_data endpoint over the SQLite database from Part 1.

Behavior:
- POST /county_data with JSON body {"zip": "02138", "measure_name": "Adult obesity"}
- Returns list of rows from county_health_rankings matching the county for the given ZIP and the measure name.
- Required keys: zip (5 digits), measure_name (one of allowed list).
- If coffee=teapot is provided, returns HTTP 418.
- 400 if required inputs missing/invalid. 404 if no matching data.
- Input values are parameterized to avoid SQL injection.

Attribution: Created with assistance from a generative AI coding assistant (Cascade) and reviewed/edited by the author.
"""
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, validator
import os
import re
import sqlite3

ALLOWED_MEASURES = {
    "Violent crime rate",
    "Unemployment",
    "Children in poverty",
    "Diabetic screening",
    "Mammography screening",
    "Preventable hospital stays",
    "Uninsured",
    "Sexually transmitted infections",
    "Physical inactivity",
    "Adult obesity",
    "Premature Death",
    "Daily fine particulate matter",
}

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "data.db"))

app = FastAPI(title="CS1060 HW4 API Prototype")


class CountyDataRequest(BaseModel):
    zip: str = Field(..., description="5-digit ZIP code")
    measure_name: str = Field(..., description="Allowed measure name")
    coffee: Optional[str] = Field(default=None, description="Easter egg to return 418 if 'teapot'")

    @validator("zip")
    def zip_is_five_digits(cls, v: str) -> str:
        if not re.fullmatch(r"\d{5}", v or ""):
            raise ValueError("zip must be a 5-digit string")
        return v

    @validator("measure_name")
    def measure_is_allowed(cls, v: str) -> str:
        if v not in ALLOWED_MEASURES:
            raise ValueError("measure_name not in allowed list")
        return v


def get_db_connection() -> sqlite3.Connection:
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=500, detail="Database not found. Ensure data.db is present on the server.")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.post("/county_data")
async def county_data(req: CountyDataRequest) -> List[Dict[str, Any]]:
    # Special case: coffee=teapot
    if req.coffee == "teapot":
        # RFC 2324
        raise HTTPException(status_code=418, detail="I'm a teapot")

    # Query: find the county/state for the given ZIP from zip_county
    # Then fetch rows from county_health_rankings matching that county/state and measure_name
    with get_db_connection() as conn:
        cur = conn.cursor()
        zip_sql = (
            "SELECT county, state_abbreviation AS state FROM zip_county WHERE zip = ? LIMIT 1;"
        )
        zip_row = cur.execute(zip_sql, (req.zip,)).fetchone()
        if not zip_row:
            raise HTTPException(status_code=404, detail="ZIP not found in dataset")

        county_name = zip_row["county"]
        state_abbr = zip_row["state"]

        chr_sql = (
            "SELECT state, county, state_code, county_code, year_span, measure_name, measure_id, "
            "numerator, denominator, raw_value, confidence_interval_lower_bound, "
            "confidence_interval_upper_bound, data_release_year, fipscode "
            "FROM county_health_rankings "
            "WHERE county = ? AND state = ? AND measure_name = ?"
        )
        rows = cur.execute(chr_sql, (county_name, state_abbr, req.measure_name)).fetchall()
        if not rows:
            # No data for this combination
            raise HTTPException(status_code=404, detail="No data for given zip and measure_name")

        results: List[Dict[str, Any]] = [dict(row) for row in rows]
        return results


@app.get("/")
async def root() -> Dict[str, str]:
    return {"status": "ok", "message": "Use POST /county_data"}
