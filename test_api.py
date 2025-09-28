#!/usr/bin/env python3
"""
Automated API tests for FastAPI app (Part 2)

Validates required behaviors:
- 200 for valid zip+measure_name
- 418 when coffee=teapot
- 400 when inputs missing/invalid
- 404 when zip or measure_name not found in data
"""
from fastapi.testclient import TestClient
import os
import sys

# Ensure DB_PATH points to local data.db
os.environ.setdefault("DB_PATH", os.path.join(os.path.dirname(__file__), "data.db"))

from app import app  # noqa: E402  (after setting env)

client = TestClient(app)


def test_county_data_success():
    resp = client.post(
        "/county_data",
        json={"zip": "02138", "measure_name": "Adult obesity"},
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # Expect standard keys present
    sample = data[0]
    for key in [
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
    ]:
        assert key in sample


def test_teapot():
    resp = client.post(
        "/county_data",
        json={"zip": "02138", "measure_name": "Adult obesity", "coffee": "teapot"},
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 418


def test_missing_inputs():
    resp = client.post(
        "/county_data",
        json={"zip": "02138"},
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 400


def test_not_found():
    resp = client.post(
        "/county_data",
        json={"zip": "99999", "measure_name": "Adult obesity"},
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 404


def main() -> int:
    # Run tests and report
    tests = [
        test_county_data_success,
        test_teapot,
        test_missing_inputs,
        test_not_found,
    ]
    for t in tests:
        t()
    print("All API tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
