# src/load_neo4j.py
# PURPOSE: Load cleaned CSV data into Neo4j as a graph
# This script runs once — it builds your entire graph database

import os
import pandas as pd
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Fix path — go up one level from src/ to project root
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load your .env file so we can read NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
load_dotenv()

# ── Connect to Neo4j ───────────────────────────────────────────────────────────
# GraphDatabase.driver() opens a connection to your running Neo4j database
# auth= takes a tuple of (username, password)
uri      = os.getenv("NEO4J_URI")
user     = os.getenv("NEO4J_USER")
password = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(uri, auth=(user, password))

# Test the connection before doing anything else
try:
    driver.verify_connectivity()
    print("✅ Connected to Neo4j successfully")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    print("   → Make sure Neo4j Desktop is open and your database is running (green dot)")
    exit()

# ── Load your clean CSV files ──────────────────────────────────────────────────
country_stats = pd.read_csv("data/country_stats.csv")
country_edges = pd.read_csv("data/country_edges.csv")

print(f"Countries to load : {len(country_stats)}")
print(f"Edges to load     : {len(country_edges)}")

# ── Helper function to run Cypher queries ──────────────────────────────────────
# Cypher is Neo4j's query language — like SQL but for graphs
# session.run() sends a Cypher command to the database
def run_query(query, parameters=None):
    with driver.session() as session:
        result = session.run(query, parameters or {})
        # .data() fetches ALL records into a plain Python list immediately
        # before the session closes — this fixes the "result consumed" error
        return result.data()

# ── Step 1: Clear existing data ────────────────────────────────────────────────
# MATCH (n) finds ALL nodes
# DETACH DELETE n removes them AND all their relationships
# We do this so you can re-run this script cleanly without duplicates
print("\nClearing existing data...")
run_query("MATCH (n) DETACH DELETE n")
print("✅ Database cleared")

# ── Step 2: Create constraints ─────────────────────────────────────────────────
# A constraint is like a rule: "country name must be unique"
# This also creates an INDEX — makes lookups 100x faster
# Without this, loading 4557 edges would check every node one by one = very slow
print("\nCreating constraints...")
run_query("""
    CREATE CONSTRAINT country_name IF NOT EXISTS
    FOR (c:Country) REQUIRE c.name IS UNIQUE
""")
print("✅ Constraints created")

# ── Step 3: Load Country nodes ─────────────────────────────────────────────────
# Each row in country_stats becomes one node in the graph
# MERGE means: create this node IF it doesn't exist yet
#              if it already exists, just update it
# SET c += {...} adds properties to the node
print("\nLoading country nodes...")

# We load in batches — sending all 237 countries at once in one query
# is faster than sending 237 separate queries
countries_data = country_stats.to_dict("records")
# .to_dict("records") converts dataframe to a list of dicts like:
# [{"country": "United States", "airport_count": 1512, ...}, ...]

run_query("""
    UNWIND $rows AS row
    MERGE (c:Country {name: row.country})
    SET c.airport_count    = row.airport_count,
        c.outgoing_routes  = row.outgoing_routes,
        c.incoming_routes  = row.incoming_routes,
        c.total_routes     = row.total_routes
""", {"rows": countries_data})

# Verify how many nodes were created
result = run_query("MATCH (c:Country) RETURN count(c) AS total")
count = result[0]["total"]
print(f"✅ Created {count} Country nodes")

# ── Step 4: Load Relationships (edges) ────────────────────────────────────────
# Each row in country_edges becomes one relationship in the graph
# We load in batches of 500 for speed
print("\nLoading country connections (edges)...")

edges_data = country_edges.to_dict("records")
batch_size = 500
total_batches = len(edges_data) // batch_size + 1

for i in range(0, len(edges_data), batch_size):
    batch = edges_data[i:i + batch_size]
    batch_num = i // batch_size + 1

    run_query("""
        UNWIND $rows AS row
        MATCH (source:Country {name: row.source_country})
        MATCH (dest:Country   {name: row.dest_country})
        MERGE (source)-[r:CONNECTS_TO]->(dest)
        SET r.route_count = row.route_count
    """, {"rows": batch})

    print(f"  Loaded batch {batch_num}/{total_batches} ({min(i+batch_size, len(edges_data))}/{len(edges_data)} edges)")

# Verify how many relationships were created
result = run_query("MATCH ()-[r:CONNECTS_TO]->() RETURN count(r) AS total")
count = result[0]["total"]
print(f"✅ Created {count} CONNECTS_TO relationships")

# ── Step 5: Verify the graph with sample queries ───────────────────────────────
print("\n" + "="*50)
print("VERIFICATION — Sample Cypher Query Results")
print("="*50)

# Query 1: Top 5 most connected countries
print("\nTop 5 countries by total routes:")
result = run_query("""
    MATCH (c:Country)
    RETURN c.name AS country, c.total_routes AS total_routes
    ORDER BY total_routes DESC
    LIMIT 5
""")
for record in result:
    print(f"  {record['country']:<25} {record['total_routes']} routes")

# Query 2: How many countries does USA connect to directly?
print("\nCountries USA connects to directly:")
result = run_query("""
    MATCH (usa:Country {name: 'United States'})-[r:CONNECTS_TO]->(other:Country)
    RETURN count(other) AS direct_connections
""")
print(f"  {result[0]['direct_connections']} countries")

# Query 3: Strongest connection (most routes between two countries)
print("\nStrongest country connection (most routes):")
result = run_query("""
    MATCH (a:Country)-[r:CONNECTS_TO]->(b:Country)
    RETURN a.name AS from, b.name AS to, r.route_count AS routes
    ORDER BY routes DESC
    LIMIT 3
""")
for record in result:
    print(f"  {record['from']} → {record['to']} : {record['routes']} routes")

driver.close()
print("\n✅ Neo4j loading complete! Your graph is ready.")
print("   Open Neo4j Browser to visually explore it:")
print("   Click 'Open' in Neo4j Desktop → type this query:")
print("   MATCH (c:Country)-[r:CONNECTS_TO]->(d:Country)")
print("   RETURN c,r,d LIMIT 50")