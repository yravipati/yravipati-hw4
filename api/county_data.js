// Vercel Serverless Function: /api/county_data
// POST JSON { zip: "02138", measure_name: "Adult obesity" }
// Returns rows from county_health_rankings for the county/state resolved from zip_county.
// Special rule: if coffee == "teapot" → 418. Errors: 400 (bad request), 404 (not found).
// Uses sql.js (WASM) to query the bundled SQLite database (data.db) read-only.

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

// Lazy-load sql.js and database
let dbPromise = null;
async function getDb() {
  if (!dbPromise) {
    dbPromise = (async () => {
      const initSqlJs = require('sql.js');
      const SQL = await initSqlJs();
      
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
      
      const fileBuffer = fs.readFileSync(dbPath);
      const u8 = new Uint8Array(fileBuffer);
      return new SQL.Database(u8);
    })();
  }
  return dbPromise;
}

function send(res, status, payload) {
  res.status(status).setHeader('content-type', 'application/json');
  res.send(JSON.stringify(payload));
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
    res.status(418).setHeader('content-type', 'application/json');
    return res.send(JSON.stringify({ error: null, result: "I'm a teapot" }));
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
    const db = await getDb();

    // Resolve county + state for the ZIP
    const zipStmt = db.prepare('SELECT county, state_abbreviation AS state FROM zip_county WHERE zip = ? LIMIT 1;');
    zipStmt.bind([zipStr]);
    let county = null;
    let state = null;
    while (zipStmt.step()) {
      const row = zipStmt.getAsObject();
      county = row.county;
      state = row.state;
      break;
    }
    zipStmt.free();

    if (!county || !state) {
      return send(res, 404, { error: 'not_found', detail: 'ZIP not found in dataset' });
    }

    // Fetch rows from county_health_rankings
    const chrStmt = db.prepare(
      'SELECT state, county, state_code, county_code, year_span, measure_name, measure_id, ' +
      'numerator, denominator, raw_value, confidence_interval_lower_bound, ' +
      'confidence_interval_upper_bound, data_release_year, fipscode ' +
      'FROM county_health_rankings WHERE county = ? AND state = ? AND measure_name = ?'
    );
    chrStmt.bind([county, state, measureName]);

    const results = [];
    while (chrStmt.step()) {
      results.push(chrStmt.getAsObject());
    }
    chrStmt.free();

    if (results.length === 0) {
      return send(res, 404, { error: 'not_found', detail: 'No data for given zip and measure_name' });
    }

    return send(res, 200, results);
  } catch (err) {
    return send(res, 500, { error: 'server_error', detail: String(err) });
  }
}
