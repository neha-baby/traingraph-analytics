import os
import pandas as pd
import numpy as np

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
print("Working from:", os.getcwd())

# ── Load raw files ─────────────────────────────────────────────────────────
airports = pd.read_csv("data/airports.dat", header=None)
airports.columns = ["airport_id", "name", "city", "country", "iata", "icao",
                    "lat", "lon", "altitude", "timezone", "dst", "tz", "type", "source"]

routes = pd.read_csv("data/routes.dat", header=None)
routes.columns = ["airline", "airline_id", "source_airport", "source_airport_id",
                  "dest_airport", "dest_airport_id", "codeshare", "stops", "equipment"]

print(f"Raw airports : {airports.shape}")
print(f"Raw routes   : {routes.shape}")

# ── Fix \N problem ─────────────────────────────────────────────────────────
airports.replace("\\N", np.nan, inplace=True)
routes.replace("\\N", np.nan, inplace=True)

# ── Clean airports ─────────────────────────────────────────────────────────
airports = airports[airports["type"] == "airport"]
airports = airports.dropna(subset=["country"])
airports = airports.dropna(subset=["lat", "lon"])
airports["lat"] = pd.to_numeric(airports["lat"], errors="coerce")
airports["lon"] = pd.to_numeric(airports["lon"], errors="coerce")

airports_clean = airports[["airport_id", "name", "city", "country", "iata", "lat", "lon"]].copy()
airports_clean = airports_clean.reset_index(drop=True)
print(f"Clean airports : {airports_clean.shape}")

# ── Clean routes ───────────────────────────────────────────────────────────
routes = routes.dropna(subset=["source_airport", "dest_airport"])
routes["stops"] = pd.to_numeric(routes["stops"], errors="coerce")
routes = routes[routes["stops"] == 0]
routes_clean = routes[["airline", "source_airport", "dest_airport"]].drop_duplicates()
routes_clean = routes_clean.reset_index(drop=True)
print(f"Clean routes   : {routes_clean.shape}")

# ── Build country lookup ───────────────────────────────────────────────────
iata_to_country = (
    airports_clean
    .dropna(subset=["iata"])
    .set_index("iata")["country"]
    .to_dict()
)

print("\nSample lookups:")
for code in ["ATL", "LHR", "DXB", "SYD", "NRT"]:
    print(f"  {code} → {iata_to_country.get(code, 'NOT FOUND')}")

# ── Map countries onto routes ──────────────────────────────────────────────
routes_clean = routes_clean.copy()
routes_clean["source_country"] = routes_clean["source_airport"].map(iata_to_country)
routes_clean["dest_country"]   = routes_clean["dest_airport"].map(iata_to_country)
routes_clean = routes_clean.dropna(subset=["source_country", "dest_country"])
routes_clean = routes_clean[routes_clean["source_country"] != routes_clean["dest_country"]]
print(f"\nInternational routes : {len(routes_clean)}")

# ── Build country edges ────────────────────────────────────────────────────
country_edges = (
    routes_clean
    .groupby(["source_country", "dest_country"])
    .size()
    .reset_index(name="route_count")
)
print(f"Country edges        : {len(country_edges)}")

# ── Build country stats ────────────────────────────────────────────────────
airports_per_country = airports_clean.groupby("country").size().reset_index(name="airport_count")
outgoing = routes_clean.groupby("source_country").size().reset_index(name="outgoing_routes")
incoming = routes_clean.groupby("dest_country").size().reset_index(name="incoming_routes")

country_stats = airports_per_country.merge(outgoing, left_on="country", right_on="source_country", how="left")
country_stats = country_stats.merge(incoming, left_on="country", right_on="dest_country", how="left")
country_stats = country_stats.drop(columns=["source_country", "dest_country"])
country_stats["outgoing_routes"] = country_stats["outgoing_routes"].fillna(0).astype(int)
country_stats["incoming_routes"] = country_stats["incoming_routes"].fillna(0).astype(int)
country_stats["total_routes"]    = country_stats["outgoing_routes"] + country_stats["incoming_routes"]
country_stats = country_stats.sort_values("total_routes", ascending=False).reset_index(drop=True)

print(f"\nTop 10 most connected countries:")
print(country_stats.head(10).to_string(index=False))

# ── Save all 4 files ───────────────────────────────────────────────────────
airports_clean.to_csv("data/airports_clean.csv", index=False)
routes_clean.to_csv("data/routes_clean.csv", index=False)
country_edges.to_csv("data/country_edges.csv", index=False)
country_stats.to_csv("data/country_stats.csv", index=False)

print("\n✅ Done! Saved 4 files to data/")
print(f"  airports_clean.csv  → {len(airports_clean)} airports")
print(f"  routes_clean.csv    → {len(routes_clean)} routes")
print(f"  country_edges.csv   → {len(country_edges)} country connections")
print(f"  country_stats.csv   → {len(country_stats)} countries")