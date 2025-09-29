#!/usr/bin/env python3
"""
Comprehensive test suite for CS1060 HW4 - Tests both Part 1 and Part 2

This script tests the entire implementation from scratch:
1. Part 1: CSV to SQLite conversion
2. Part 2: API endpoint functionality (if deployed)

Run with: python3 test_full_implementation.py
"""

import os
import sqlite3
import subprocess
import sys
import tempfile
import shutil
import json
import urllib.request
import urllib.parse
from typing import Dict, List, Any

# Test configuration
CSV_FILES = ["zip_county.csv", "county_health_rankings.csv"]
EXPECTED_ZIP_COUNT = 54553
EXPECTED_CHR_COUNT = 303864
API_ENDPOINT = "https://yravipati-hw4.vercel.app/county_data"

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def pass_test(self, name: str):
        print(f"✅ PASS: {name}")
        self.passed += 1
    
    def fail_test(self, name: str, error: str):
        print(f"❌ FAIL: {name} - {error}")
        self.failed += 1
        self.errors.append(f"{name}: {error}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"TEST SUMMARY: {self.passed}/{total} tests passed")
        if self.failed > 0:
            print(f"\nFAILED TESTS:")
            for error in self.errors:
                print(f"  - {error}")
        print(f"{'='*60}")
        return self.failed == 0

def test_part1_csv_to_sqlite(results: TestResults, test_dir: str):
    """Test Part 1: CSV to SQLite conversion"""
    print("\n🔍 TESTING PART 1: CSV to SQLite Conversion")
    
    # Copy script to test directory
    script_path = os.path.join(test_dir, "csv_to_sqlite.py")
    shutil.copy("csv_to_sqlite.py", script_path)
    
    # Copy CSV files to test directory
    for csv_file in CSV_FILES:
        if os.path.exists(csv_file):
            shutil.copy(csv_file, test_dir)
        else:
            results.fail_test("CSV files present", f"{csv_file} not found in current directory")
            return
    
    results.pass_test("CSV files present")
    
    # Test 1: Script exists and is executable
    if not os.path.exists(script_path):
        results.fail_test("csv_to_sqlite.py exists", "Script not found")
        return
    results.pass_test("csv_to_sqlite.py exists")
    
    # Test 2: Run script on zip_county.csv
    db_path = os.path.join(test_dir, "test_data.db")
    try:
        subprocess.run([
            sys.executable, script_path, db_path, "zip_county.csv"
        ], cwd=test_dir, check=True, capture_output=True)
        results.pass_test("Load zip_county.csv")
    except subprocess.CalledProcessError as e:
        results.fail_test("Load zip_county.csv", f"Script failed: {e.stderr.decode()}")
        return
    
    # Test 3: Run script on county_health_rankings.csv
    try:
        subprocess.run([
            sys.executable, script_path, db_path, "county_health_rankings.csv"
        ], cwd=test_dir, check=True, capture_output=True)
        results.pass_test("Load county_health_rankings.csv")
    except subprocess.CalledProcessError as e:
        results.fail_test("Load county_health_rankings.csv", f"Script failed: {e.stderr.decode()}")
        return
    
    # Test 4: Verify database was created
    if not os.path.exists(db_path):
        results.fail_test("Database created", "test_data.db not found")
        return
    results.pass_test("Database created")
    
    # Test 5: Verify database schema and content
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Check zip_county table
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='zip_county';")
        if not cur.fetchone():
            results.fail_test("zip_county table exists", "Table not found")
        else:
            results.pass_test("zip_county table exists")
        
        # Check county_health_rankings table
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='county_health_rankings';")
        if not cur.fetchone():
            results.fail_test("county_health_rankings table exists", "Table not found")
        else:
            results.pass_test("county_health_rankings table exists")
        
        # Check zip_county row count
        cur.execute("SELECT COUNT(*) FROM zip_county;")
        zip_count = cur.fetchone()[0]
        if zip_count == EXPECTED_ZIP_COUNT:
            results.pass_test(f"zip_county row count ({EXPECTED_ZIP_COUNT})")
        else:
            results.fail_test(f"zip_county row count", f"Expected {EXPECTED_ZIP_COUNT}, got {zip_count}")
        
        # Check county_health_rankings row count
        cur.execute("SELECT COUNT(*) FROM county_health_rankings;")
        chr_count = cur.fetchone()[0]
        if chr_count == EXPECTED_CHR_COUNT:
            results.pass_test(f"county_health_rankings row count ({EXPECTED_CHR_COUNT})")
        else:
            results.fail_test(f"county_health_rankings row count", f"Expected {EXPECTED_CHR_COUNT}, got {chr_count}")
        
        # Check zip_county schema
        cur.execute("PRAGMA table_info(zip_county);")
        zip_columns = [row[1] for row in cur.fetchall()]
        expected_zip_cols = ["zip", "default_state", "county", "county_state", "state_abbreviation", 
                           "county_code", "zip_pop", "zip_pop_in_county", "n_counties", "default_city"]
        if zip_columns == expected_zip_cols:
            results.pass_test("zip_county schema correct")
        else:
            results.fail_test("zip_county schema", f"Expected {expected_zip_cols}, got {zip_columns}")
        
        # Check county_health_rankings schema
        cur.execute("PRAGMA table_info(county_health_rankings);")
        chr_columns = [row[1] for row in cur.fetchall()]
        expected_chr_cols = ["state", "county", "state_code", "county_code", "year_span", "measure_name", 
                           "measure_id", "numerator", "denominator", "raw_value", "confidence_interval_lower_bound",
                           "confidence_interval_upper_bound", "data_release_year", "fipscode"]
        if chr_columns == expected_chr_cols:
            results.pass_test("county_health_rankings schema correct")
        else:
            results.fail_test("county_health_rankings schema", f"Expected {expected_chr_cols}, got {chr_columns}")
        
        # Test sample query (ZIP 02138 -> Middlesex County, MA)
        cur.execute("SELECT county, state_abbreviation FROM zip_county WHERE zip = '02138';")
        zip_result = cur.fetchone()
        if zip_result and "Middlesex" in zip_result[0] and zip_result[1] == "MA":
            results.pass_test("Sample ZIP lookup (02138)")
        else:
            results.fail_test("Sample ZIP lookup (02138)", f"Expected Middlesex County, MA; got {zip_result}")
        
        conn.close()
        
    except Exception as e:
        results.fail_test("Database validation", f"Error: {str(e)}")

def make_api_request(url: str, data: Dict[str, Any]) -> tuple[int, Dict[str, Any]]:
    """Make HTTP POST request to API endpoint"""
    json_data = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=json_data,
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            status = response.getcode()
            response_data = json.loads(response.read().decode('utf-8'))
            return status, response_data
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            response_data = json.loads(e.read().decode('utf-8'))
        except:
            response_data = {"error": "http_error", "detail": str(e)}
        return status, response_data

def test_part2_api_endpoint(results: TestResults):
    """Test Part 2: API endpoint functionality"""
    print("\n🔍 TESTING PART 2: API Endpoint")
    
    # Test 1: Valid request (200)
    try:
        status, data = make_api_request(API_ENDPOINT, {
            "zip": "02138",
            "measure_name": "Adult obesity"
        })
        if status == 200:
            results.pass_test("Valid request returns 200")
            if isinstance(data, list) and len(data) > 0:
                results.pass_test("Valid request returns data array")
                # Check required fields in response
                sample = data[0]
                required_fields = ["state", "county", "state_code", "county_code", "year_span", 
                                 "measure_name", "measure_id", "numerator", "denominator", "raw_value",
                                 "confidence_interval_lower_bound", "confidence_interval_upper_bound", 
                                 "data_release_year", "fipscode"]
                missing_fields = [f for f in required_fields if f not in sample]
                if not missing_fields:
                    results.pass_test("Response contains all required fields")
                else:
                    results.fail_test("Response schema", f"Missing fields: {missing_fields}")
            else:
                results.fail_test("Valid request returns data", "Expected non-empty array")
        else:
            results.fail_test("Valid request returns 200", f"Got status {status}")
    except Exception as e:
        results.fail_test("Valid request", f"Error: {str(e)}")
    
    # Test 2: Teapot request (418)
    try:
        status, data = make_api_request(API_ENDPOINT, {
            "zip": "02138",
            "measure_name": "Adult obesity",
            "coffee": "teapot"
        })
        if status == 418:
            results.pass_test("Teapot request returns 418")
        else:
            results.fail_test("Teapot request returns 418", f"Got status {status}")
    except Exception as e:
        results.fail_test("Teapot request", f"Error: {str(e)}")
    
    # Test 3: Missing zip (400)
    try:
        status, data = make_api_request(API_ENDPOINT, {
            "measure_name": "Adult obesity"
        })
        if status == 400:
            results.pass_test("Missing zip returns 400")
        else:
            results.fail_test("Missing zip returns 400", f"Got status {status}")
    except Exception as e:
        results.fail_test("Missing zip request", f"Error: {str(e)}")
    
    # Test 4: Invalid measure_name (400)
    try:
        status, data = make_api_request(API_ENDPOINT, {
            "zip": "02138",
            "measure_name": "Invalid Measure"
        })
        if status == 400:
            results.pass_test("Invalid measure_name returns 400")
        else:
            results.fail_test("Invalid measure_name returns 400", f"Got status {status}")
    except Exception as e:
        results.fail_test("Invalid measure_name request", f"Error: {str(e)}")
    
    # Test 5: Non-existent ZIP (404)
    try:
        status, data = make_api_request(API_ENDPOINT, {
            "zip": "99999",
            "measure_name": "Adult obesity"
        })
        if status == 404:
            results.pass_test("Non-existent ZIP returns 404")
        else:
            results.fail_test("Non-existent ZIP returns 404", f"Got status {status}")
    except Exception as e:
        results.fail_test("Non-existent ZIP request", f"Error: {str(e)}")
    
    # Test 6: All allowed measure names
    allowed_measures = [
        "Violent crime rate", "Unemployment", "Children in poverty", "Diabetic screening",
        "Mammography screening", "Preventable hospital stays", "Uninsured", 
        "Sexually transmitted infections", "Physical inactivity", "Adult obesity",
        "Premature Death", "Daily fine particulate matter"
    ]
    
    valid_measures = 0
    for measure in allowed_measures:
        try:
            status, data = make_api_request(API_ENDPOINT, {
                "zip": "02138",
                "measure_name": measure
            })
            if status in [200, 404]:  # 200 if data exists, 404 if no data for this measure
                valid_measures += 1
        except:
            pass
    
    if valid_measures == len(allowed_measures):
        results.pass_test("All allowed measure names accepted")
    else:
        results.fail_test("All allowed measure names", f"Only {valid_measures}/{len(allowed_measures)} worked")

def main():
    print("🧪 CS1060 HW4 - Comprehensive Implementation Test")
    print("=" * 60)
    
    results = TestResults()
    
    # Create temporary test directory
    with tempfile.TemporaryDirectory() as test_dir:
        print(f"📁 Using test directory: {test_dir}")
        
        # Test Part 1
        test_part1_csv_to_sqlite(results, test_dir)
        
        # Test Part 2
        test_part2_api_endpoint(results)
    
    # Print final results
    success = results.summary()
    
    if success:
        print("\n🎉 ALL TESTS PASSED! Implementation is ready for submission.")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED! Please fix issues before submission.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
