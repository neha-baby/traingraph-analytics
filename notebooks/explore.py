# notebooks/explore.py
# PURPOSE: Understand the raw data before touching it
# Rule in analytics: never clean data you haven't looked at first

import pandas as pd

# ── Load airports ──────────────────────────────────────────────────────────────
airports = pd.read_csv("data/airports.dat", header=None)
airports.columns = ["airport_id", "name", "city", "country", "iata", "icao",
                    "lat", "lon", "altitude", "timezone", "dst", "tz", "type", "source"]

# ── Load routes ────────────────────────────────────────────────────────────────
routes = pd.read_csv("data/routes.dat", header=None)
routes.columns = ["airline", "airline_id", "source_airport", "source_airport_id",
                  "dest_airport", "dest_airport_id", "codeshare", "stops", "equipment"]

# ── Basic shape ────────────────────────────────────────────────────────────────
print("=" * 50)
print("AIRPORTS")
print("=" * 50)
print(f"Rows    : {len(airports)}")        # how many airports
print(f"Columns : {airports.shape[1]}")    # how many columns
print()

# dtypes tells you whether pandas read each column as number or text
print("Column data types:")
print(airports.dtypes)
print()

# ── Check for missing values ───────────────────────────────────────────────────
# isnull() marks every missing cell as True
# .sum() counts the Trues per column
print("Missing values per column:")
print(airports.isnull().sum())
print()

# ── Sample rows ────────────────────────────────────────────────────────────────
print("First 3 rows:")
print(airports[["name", "city", "country", "iata", "lat", "lon"]].head(3))
print()

# ── How many unique countries? ─────────────────────────────────────────────────
print(f"Unique countries in airports: {airports['country'].nunique()}")
print()
print("Sample countries:")
print(airports["country"].value_counts().head(10))

print()
print("=" * 50)
print("ROUTES")
print("=" * 50)
print(f"Rows    : {len(routes)}")
print(f"Columns : {routes.shape[1]}")
print()

print("Missing values per column:")
print(routes.isnull().sum())
print()

print("First 3 rows:")
print(routes[["airline", "source_airport", "dest_airport", "stops"]].head(3))
print()

# ── Check the special \N value ─────────────────────────────────────────────────
# OpenFlights uses \N as a placeholder for "unknown" — this is NOT a real value
# We need to find and remove these
backslash_n_routes = (routes == "\\N").sum()
print("Cells containing \\N (unknown placeholder):")
print(backslash_n_routes[backslash_n_routes > 0])