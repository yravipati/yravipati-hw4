/**
 * CS1060 HW4 - Vercel Serverless Function: /api/county_data
 * 
 * POST JSON endpoint that queries county health data by ZIP code.
 * Input: { zip: "02138", measure_name: "Adult obesity" }
 * Output: Array of health records from county_health_rankings table
 * 
 * HTTP Status Codes:
 * - 200: Success (returns data array)
 * - 400: Bad request (invalid/missing zip or measure_name)
 * - 404: Not found (ZIP not in dataset or no health data)
 * - 418: I'm a teapot (when coffee=teapot is provided)
 * 
 * Uses better-sqlite3 to query bundled SQLite database (data.db) read-only.
 * Deployment: Vercel with automatic GitHub integration
 */

const fs = require('fs');
const path = require('path');

const ALLOWED_MEASURES = new Set([
  'Violent crime rate',
  'Unemployment',
  'Children in poverty',
  'Diabetic screening',
  'Mammography screening',
  'Preventable hospital stays',
  'Uninsured',
  'Sexually transmitted infections',
  'Physical inactivity',
  'Adult obesity',
  'Premature Death',
  'Daily fine particulate matter',
]);

// Database connection using better-sqlite3 (Vercel-compatible)
let db = null;
function getDb() {
  if (!db) {
    const Database = require('better-sqlite3');
    
    // Try multiple paths for data.db in Vercel environment
    const candidates = [
      path.join(__dirname, 'data.db'),
      path.join(process.cwd(), 'data.db'),
      path.join(__dirname, '..', '..', 'data.db'),
    ];
    
    let dbPath = null;
    for (const p of candidates) {
      if (fs.existsSync(p)) {
        dbPath = p;
        break;
      }
    }
    
    if (!dbPath) {
      throw new Error(`data.db not found. Tried: ${candidates.join(', ')}`);
    }
    
    db = new Database(dbPath, { readonly: true });
  }
  return db;
}

function send(res, status, payload) {
  return res.status(status).json(payload);
}

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') {
    return send(res, 400, { error: 'bad_request', detail: 'Only POST with content-type: application/json is supported' });
  }
  const ct = req.headers['content-type'] || '';
  if (!ct.includes('application/json')) {
    return send(res, 400, { error: 'bad_request', detail: 'content-type must be application/json' });
  }

  const { zip = '', measure_name = '', coffee } = req.body || {};

  if (coffee === 'teapot') {
    return res.status(418).json({ error: null, result: "I'm a teapot" });
  }

  const zipStr = String(zip).trim();
  const measureName = String(measure_name).trim();

  if (!/^\d{5}$/.test(zipStr)) {
    return send(res, 400, { error: 'bad_request', detail: 'zip must be a 5-digit string' });
  }
  if (!ALLOWED_MEASURES.has(measureName)) {
    return send(res, 400, { error: 'bad_request', detail: 'measure_name not in allowed list' });
  }

  try {
    const db = getDb();

    // Resolve county + state for the ZIP
    const zipStmt = db.prepare('SELECT county, state_abbreviation AS state FROM zip_county WHERE zip = ? LIMIT 1');
    const zipResult = zipStmt.get(zipStr);

    if (!zipResult) {
      return send(res, 404, { error: 'not_found', detail: 'ZIP not found in dataset' });
    }

    const { county, state } = zipResult;

    // Fetch rows from county_health_rankings
    const chrStmt = db.prepare(
      'SELECT state, county, state_code, county_code, year_span, measure_name, measure_id, ' +
      'numerator, denominator, raw_value, confidence_interval_lower_bound, ' +
      'confidence_interval_upper_bound, data_release_year, fipscode ' +
      'FROM county_health_rankings WHERE county = ? AND state = ? AND measure_name = ?'
    );
    const results = chrStmt.all(county, state, measureName);

    if (results.length === 0) {
      return send(res, 404, { error: 'not_found', detail: 'No data for given zip and measure_name' });
    }

    return send(res, 200, results);
  } catch (err) {
    return send(res, 500, { error: 'server_error', detail: String(err) });
  }
}
