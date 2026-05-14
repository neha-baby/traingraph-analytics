# notebooks/analysis.py
# PURPOSE: Perform EDA and NetworkX graph analysis
# This finds which countries are the true hubs of global aviation

import os
import pandas as pd
import networkx as nx
import json

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Load your clean CSV files ──────────────────────────────────────────────────
# We use the CSV files (not Neo4j) for NetworkX analysis
# NetworkX works with Python objects — easier to feed it CSVs directly
country_stats = pd.read_csv("data/country_stats.csv")
country_edges = pd.read_csv("data/country_edges.csv")
airports      = pd.read_csv("data/airports_clean.csv")
routes        = pd.read_csv("data/routes_clean.csv")

print("=" * 55)
print("PART 1 — BASIC EDA (Exploratory Data Analysis)")
print("=" * 55)

# ── EDA Question 1: Which countries have the most airports? ───────────────────
# value_counts() counts how many times each country appears in airports file
print("\nTop 10 countries by airport count:")
top_airports = country_stats.nlargest(10, "airport_count")[["country", "airport_count"]]
print(top_airports.to_string(index=False))
# INSIGHT: USA dominates domestic infrastructure
# but airport count alone doesn't mean global connectivity

# ── EDA Question 2: Which countries send the most international flights? ──────
print("\nTop 10 countries by outgoing international routes:")
top_outgoing = country_stats.nlargest(10, "outgoing_routes")[["country", "outgoing_routes"]]
print(top_outgoing.to_string(index=False))

# ── EDA Question 3: Route distribution — is it equal or skewed? ───────────────
# describe() gives count, mean, min, max, percentiles
print("\nRoute count distribution across all countries:")
print(country_stats["total_routes"].describe().round(1))
# INSIGHT: The top 10% of countries handle most routes
# This is a "power law" distribution — common in networks

# ── EDA Question 4: Which country PAIR has the most routes? ───────────────────
print("\nTop 10 busiest country-to-country connections:")
top_pairs = country_edges.nlargest(10, "route_count")
print(top_pairs.to_string(index=False))

# ── EDA Question 5: Continent analysis ────────────────────────────────────────
# Manually map countries to continents for regional analysis
continent_map = {
    "United States": "North America", "Canada": "North America",
    "Mexico": "North America", "Brazil": "South America",
    "Argentina": "South America", "Colombia": "South America",
    "Chile": "South America", "Peru": "South America",
    "United Kingdom": "Europe", "Germany": "Europe",
    "France": "Europe", "Spain": "Europe", "Italy": "Europe",
    "Netherlands": "Europe", "Turkey": "Europe", "Russia": "Europe",
    "Norway": "Europe", "Sweden": "Europe", "Switzerland": "Europe",
    "Austria": "Europe", "Portugal": "Europe", "Greece": "Europe",
    "Poland": "Europe", "Ukraine": "Europe", "Denmark": "Europe",
    "Finland": "Europe", "Czech Republic": "Europe", "Romania": "Europe",
    "Hungary": "Europe", "Belgium": "Europe", "Serbia": "Europe",
    "Croatia": "Europe", "Bulgaria": "Europe", "Slovakia": "Europe",
    "China": "Asia", "India": "Asia", "Japan": "Asia",
    "South Korea": "Asia", "Indonesia": "Asia", "Thailand": "Asia",
    "Malaysia": "Asia", "Singapore": "Asia", "Philippines": "Asia",
    "Vietnam": "Asia", "Taiwan": "Asia", "Hong Kong": "Asia",
    "Pakistan": "Asia", "Bangladesh": "Asia", "Sri Lanka": "Asia",
    "Nepal": "Asia", "Kazakhstan": "Asia", "Uzbekistan": "Asia",
    "United Arab Emirates": "Middle East", "Saudi Arabia": "Middle East",
    "Qatar": "Middle East", "Kuwait": "Middle East", "Bahrain": "Middle East",
    "Oman": "Middle East", "Jordan": "Middle East", "Lebanon": "Middle East",
    "Israel": "Middle East", "Iraq": "Middle East", "Iran": "Middle East",
    "Egypt": "Africa", "South Africa": "Africa", "Nigeria": "Africa",
    "Kenya": "Africa", "Ethiopia": "Africa", "Morocco": "Africa",
    "Tunisia": "Africa", "Ghana": "Africa", "Tanzania": "Africa",
    "Senegal": "Africa", "Cameroon": "Africa", "Ivory Coast": "Africa",
    "Australia": "Oceania", "New Zealand": "Oceania",
    "Papua New Guinea": "Oceania", "Fiji": "Oceania",
}

# Map continent onto country_stats
country_stats["continent"] = country_stats["country"].map(continent_map)
country_stats["continent"] = country_stats["continent"].fillna("Other")

# Routes per continent
print("\nTotal international routes by continent:")
continent_routes = (
    country_stats
    .groupby("continent")["total_routes"]
    .sum()
    .sort_values(ascending=False)
    .reset_index()
)
print(continent_routes.to_string(index=False))


print("\n" + "=" * 55)
print("PART 2 — NETWORKX GRAPH ANALYSIS")
print("=" * 55)

# ── Build the NetworkX graph ───────────────────────────────────────────────────
# DiGraph = Directed Graph (routes have direction: A→B is different from B→A)
# We add each country-pair as an edge with route_count as a weight
G = nx.DiGraph()

# Add edges from country_edges dataframe
# Each row becomes one directed edge in the graph
for _, row in country_edges.iterrows():
    G.add_edge(
        row["source_country"],
        row["dest_country"],
        weight=row["route_count"]
    )

print(f"\nGraph built:")
print(f"  Nodes (countries)     : {G.number_of_nodes()}")
print(f"  Edges (connections)   : {G.number_of_edges()}")
print(f"  Average connections   : {sum(dict(G.degree()).values()) / G.number_of_nodes():.1f} per country")

# ── Centrality Analysis ────────────────────────────────────────────────────────

# 1. DEGREE CENTRALITY
# Measures: what fraction of all countries does this country connect to?
# Formula: connections / (total_countries - 1)
# Range: 0 to 1 — higher = more connected
print("\nCalculating degree centrality...")
degree_centrality = nx.degree_centrality(G)

# 2. BETWEENNESS CENTRALITY
# Measures: how often does this country sit on the shortest path between others?
# A country with high betweenness is a "bridge" — remove it and many paths break
# This takes ~30 seconds for 237 nodes — normal, don't worry
print("Calculating betweenness centrality (takes ~30 seconds)...")
betweenness_centrality = nx.betweenness_centrality(G, weight="weight", normalized=True)

# 3. PAGERANK
# Originally Google's algorithm for ranking web pages
# Here: a country scores higher if important countries link to it
# Think of it as "prestige" — being connected to powerful hubs matters more
print("Calculating PageRank...")
pagerank = nx.pagerank(G, weight="weight", alpha=0.85)
# alpha=0.85 is the standard "damping factor" — industry standard value

# ── Combine all scores into one dataframe ─────────────────────────────────────
print("\nCombining scores...")
centrality_df = pd.DataFrame({
    "country"            : list(degree_centrality.keys()),
    "degree_centrality"  : list(degree_centrality.values()),
    "betweenness"        : [betweenness_centrality[c] for c in degree_centrality.keys()],
    "pagerank"           : [pagerank[c] for c in degree_centrality.keys()],
})

# Round to 4 decimal places for readability
centrality_df = centrality_df.round(4)

# Create a composite hub score = average of all 3 normalized scores
# This gives a single number representing overall importance
centrality_df["hub_score"] = (
    centrality_df["degree_centrality"] +
    centrality_df["betweenness"] +
    centrality_df["pagerank"]
).round(4)

# Sort by hub score
centrality_df = centrality_df.sort_values("hub_score", ascending=False).reset_index(drop=True)

print("\nTop 15 Aviation Hub Countries (by composite hub score):")
print(centrality_df.head(15).to_string(index=False))

# ── Merge with country stats for full picture ──────────────────────────────────
final_df = centrality_df.merge(country_stats, on="country", how="left")
final_df = final_df.sort_values("hub_score", ascending=False).reset_index(drop=True)

# ── Key Insights ───────────────────────────────────────────────────────────────
print("\n" + "=" * 55)
print("KEY INSIGHTS")
print("=" * 55)

top1 = final_df.iloc[0]
print(f"\n🏆 Top global aviation hub: {top1['country']}")
print(f"   Connects to {int(G.degree(top1['country']))} countries")
print(f"   Hub score: {top1['hub_score']}")

# Find the biggest "bridge" country (highest betweenness)
bridge = final_df.nlargest(1, "betweenness").iloc[0]
print(f"\n🌉 Biggest bridge country: {bridge['country']}")
print(f"   Betweenness score: {bridge['betweenness']}")
print(f"   (Remove this country and many international routes break)")

# Find hidden gems — high betweenness but not top by total routes
# These are countries that punch above their weight as connectors
final_df["rank_routes"]      = final_df["total_routes"].rank(ascending=False)
final_df["rank_betweenness"] = final_df["betweenness"].rank(ascending=False)
final_df["hidden_gem_score"] = final_df["rank_routes"] - final_df["rank_betweenness"]
hidden_gems = final_df.nlargest(5, "hidden_gem_score")[["country", "total_routes", "betweenness"]]
print(f"\n💎 Hidden gem hub countries (important bridges, not obvious from route count):")
print(hidden_gems.to_string(index=False))

# ── Save results ───────────────────────────────────────────────────────────────
final_df.to_csv("data/centrality_scores.csv", index=False)
country_stats.to_csv("data/country_stats.csv", index=False)  # resave with continent column

print("\n✅ Saved data/centrality_scores.csv")
print(f"   {len(final_df)} countries with degree, betweenness, pagerank and hub scores")
print("\n✅ Phase 4 complete — ready to build Plotly charts!")