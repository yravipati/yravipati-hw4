// Netlify Function: county_data
// POST /county_data (via redirect) with JSON body { zip: "02138", measure_name: "Adult obesity" }
// Returns rows from county_health_rankings for the county/state resolved from zip_county.
// Special rule: if coffee == "teapot" return HTTP 418.
// Errors: 400 (missing/invalid inputs), 404 (no matches).
// Uses sql.js (WASM) to query the bundled SQLite database file at runtime.

const path = require("path");
const fs = require("fs");
const initSqlJs = require("sql.js");
const wasmPath = require.resolve("sql.js/dist/sql-wasm.wasm");

const ALLOWED_MEASURES = new Set([
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
]);

// Attempt to locate data.db. Netlify includes files declared in netlify.toml `included_files`.
// Try alongside the compiled function, then fall back to repo root two levels up.
const DB_CANDIDATES = [
  path.resolve(__dirname, "data.db"),
  path.resolve(__dirname, "../../data.db"),
];
function findDbPath() {
  for (const p of DB_CANDIDATES) {
    if (fs.existsSync(p)) return p;
  }
  return DB_CANDIDATES[0];
}
const DB_PATH = findDbPath();

// Lazy-initialize the in-memory database once per function container
let dbPromise = null;
async function getDb() {
  if (!dbPromise) {
    dbPromise = (async () => {
      const SQL = await initSqlJs({
        locateFile: () => wasmPath,
      });
      const fileBuffer = fs.readFileSync(DB_PATH);
      const u8 = new Uint8Array(fileBuffer);
      return new SQL.Database(u8);
    })();
  }
  return dbPromise;
}

function badRequest(body) {
  return {
    statusCode: 400,
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ error: "bad_request", detail: body }),
  };
}

function notFound(detail) {
  return {
    statusCode: 404,
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ error: "not_found", detail }),
  };
}

function teapot() {
  return {
    statusCode: 418,
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ error: null, result: "I'm a teapot" }),
  };
}

exports.handler = async (event) => {
  if (event.httpMethod !== "POST") {
    return badRequest("Only POST with content-type: application/json is supported");
  }
  const ct = event.headers["content-type"] || event.headers["Content-Type"] || "";
  if (!ct.includes("application/json")) {
    return badRequest("content-type must be application/json");
  }

  let payload;
  try {
    payload = JSON.parse(event.body || "{}");
  } catch (e) {
    return badRequest("Malformed JSON body");
  }

  const zip = String(payload.zip || "").trim();
  const measureName = String(payload.measure_name || "").trim();
  const coffee = payload.coffee;

  if (coffee === "teapot") {
    return teapot();
  }

  if (!/^\d{5}$/.test(zip)) {
    return badRequest("zip must be a 5-digit string");
  }
  if (!ALLOWED_MEASURES.has(measureName)) {
    return badRequest("measure_name not in allowed list");
  }

  try {
    const db = await getDb();

    // 1) Resolve county + state_abbreviation from zip_county
    const zipStmt = db.prepare(
      "SELECT county, state_abbreviation AS state FROM zip_county WHERE zip = ? LIMIT 1;"
    );
    zipStmt.bind([zip]);
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
      return notFound("ZIP not found in dataset");
    }

    // 2) Fetch rows from county_health_rankings matching county, state, and measure_name
    const chrStmt = db.prepare(
      "SELECT state, county, state_code, county_code, year_span, measure_name, measure_id, " +
        "numerator, denominator, raw_value, confidence_interval_lower_bound, " +
        "confidence_interval_upper_bound, data_release_year, fipscode " +
        "FROM county_health_rankings WHERE county = ? AND state = ? AND measure_name = ?"
    );
    chrStmt.bind([county, state, measureName]);

    const results = [];
    while (chrStmt.step()) {
      results.push(chrStmt.getAsObject());
    }
    chrStmt.free();

    if (results.length === 0) {
      return notFound("No data for given zip and measure_name");
    }

    return {
      statusCode: 200,
      headers: { "content-type": "application/json" },
      body: JSON.stringify(results),
    };
  } catch (err) {
    return {
      statusCode: 500,
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ error: "server_error", detail: String(err) }),
    };
  }
};
