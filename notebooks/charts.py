# notebooks/charts.py
# PURPOSE: Build all 5 Plotly charts for your dashboard
# Each chart answers a different analytical question

import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import networkx as nx
import json

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Load data ──────────────────────────────────────────────────────────────────
centrality  = pd.read_csv("data/centrality_scores.csv")
country_stats = pd.read_csv("data/country_stats.csv")
country_edges = pd.read_csv("data/country_edges.csv")

print("Building 5 charts...")

# ══════════════════════════════════════════════════════
# CHART 1 — Top 15 Countries by Total International Routes
# Type: Horizontal bar chart
# Question: Which countries dominate global aviation?
# ══════════════════════════════════════════════════════

top15 = centrality.nlargest(15, "total_routes").sort_values("total_routes")

fig1 = px.bar(
    top15,
    x="total_routes",
    y="country",
    orientation="h",          # horizontal bars — easier to read country names
    color="hub_score",        # color bars by hub score — adds extra dimension
    color_continuous_scale="Teal",
    title="Top 15 Countries by International Route Count",
    labels={
        "total_routes": "Total International Routes",
        "country"     : "Country",
        "hub_score"   : "Hub Score"
    },
    text="total_routes",      # show the number on each bar
)

fig1.update_traces(textposition="outside")
fig1.update_layout(
    height=550,
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(family="Arial", size=12),
    coloraxis_colorbar=dict(title="Hub Score"),
    xaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
    yaxis=dict(showgrid=False),
    title_font_size=16,
)

fig1.write_html("data/chart1_top_countries.html")
print("✅ Chart 1 saved — top countries bar chart")


# ══════════════════════════════════════════════════════
# CHART 2 — World Choropleth Map colored by Hub Score
# Type: Filled world map
# Question: Where are the world's aviation hubs located?
# This is YOUR signature chart — partner had dots, you have filled countries
# ══════════════════════════════════════════════════════

fig2 = px.choropleth(
    centrality,
    locations="country",           # column with country names
    locationmode="country names",  # tells plotly to match by name not code
    color="hub_score",             # fill color = hub score
    hover_name="country",
    hover_data={
        "hub_score"         : ":.4f",
        "total_routes"      : True,
        "degree_centrality" : ":.4f",
        "betweenness"       : ":.4f",
        "pagerank"          : ":.4f",
    },
    color_continuous_scale="Viridis",
    title="Global Aviation Hub Score by Country",
    labels={"hub_score": "Hub Score"},
)

fig2.update_layout(
    height=500,
    geo=dict(
        showframe=False,
        showcoastlines=True,
        coastlinecolor="white",
        showland=True,
        landcolor="#f5f5f5",
        showocean=True,
        oceancolor="#e8f4f8",
        projection_type="natural earth",
    ),
    paper_bgcolor="white",
    font=dict(family="Arial", size=12),
    title_font_size=16,
    coloraxis_colorbar=dict(title="Hub Score"),
)

fig2.write_html("data/chart2_world_map.html")
print("✅ Chart 2 saved — world choropleth map")


# ══════════════════════════════════════════════════════
# CHART 3 — Degree vs Betweenness Centrality Scatter
# Type: Scatter plot with bubbles
# Question: Which countries are bridges vs which are just busy?
# The most analytically interesting chart — shows hidden gems
# ══════════════════════════════════════════════════════

# Only show top 40 countries to keep chart readable
top40 = centrality.nlargest(40, "hub_score").copy()

fig3 = px.scatter(
    top40,
    x="degree_centrality",      # x-axis: how many countries connected to
    y="betweenness",            # y-axis: how often on shortest path
    size="total_routes",        # bubble size: raw route count
    color="pagerank",           # bubble color: pagerank score
    hover_name="country",
    color_continuous_scale="RdYlGn",
    title="Degree vs Betweenness Centrality — Finding True Hub Countries",
    labels={
        "degree_centrality" : "Degree Centrality (breadth of connections)",
        "betweenness"       : "Betweenness Centrality (bridge importance)",
        "total_routes"      : "Total Routes",
        "pagerank"          : "PageRank",
    },
    text="country",             # show country name on each bubble
)

fig3.update_traces(
    textposition="top center",
    textfont=dict(size=9),
    marker=dict(opacity=0.8, line=dict(width=1, color="white"))
)

# Add quadrant lines at the median values
median_degree = top40["degree_centrality"].median()
median_between = top40["betweenness"].median()

fig3.add_hline(
    y=median_between,
    line_dash="dot",
    line_color="gray",
    annotation_text="median betweenness",
    annotation_position="right"
)
fig3.add_vline(
    x=median_degree,
    line_dash="dot",
    line_color="gray",
    annotation_text="median degree",
    annotation_position="top"
)

fig3.update_layout(
    height=580,
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(family="Arial", size=11),
    title_font_size=16,
    xaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
    yaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
)

fig3.write_html("data/chart3_centrality_scatter.html")
print("✅ Chart 3 saved — centrality scatter plot")


# ══════════════════════════════════════════════════════
# CHART 4 — Top 20 Country Network Graph
# Type: Network/graph visualization
# Question: How are the top hub countries connected to each other?
# ══════════════════════════════════════════════════════

# Get top 20 countries by hub score
top20_countries = centrality.nlargest(20, "hub_score")["country"].tolist()

# Filter edges to only those between top 20 countries
top20_edges = country_edges[
    country_edges["source_country"].isin(top20_countries) &
    country_edges["dest_country"].isin(top20_countries)
]

# Build NetworkX graph for layout calculation only
G_top20 = nx.DiGraph()
for _, row in top20_edges.iterrows():
    G_top20.add_edge(row["source_country"], row["dest_country"], weight=row["route_count"])

# Calculate positions using spring layout
# spring layout places highly connected nodes near each other
pos = nx.spring_layout(G_top20, seed=42, k=2)

# Build Plotly network graph manually
# Edges first (drawn behind nodes)
edge_x, edge_y = [], []
for u, v in G_top20.edges():
    x0, y0 = pos[u]
    x1, y1 = pos[v]
    edge_x += [x0, x1, None]   # None creates a gap between edges
    edge_y += [y0, y1, None]

edge_trace = go.Scatter(
    x=edge_x, y=edge_y,
    mode="lines",
    line=dict(width=0.5, color="#cccccc"),
    hoverinfo="none",
    showlegend=False,
)

# Nodes (drawn on top of edges)
node_x = [pos[n][0] for n in G_top20.nodes()]
node_y = [pos[n][1] for n in G_top20.nodes()]
node_names = list(G_top20.nodes())

# Get hub score for each node for coloring
hub_scores = []
for name in node_names:
    score = centrality[centrality["country"] == name]["hub_score"].values
    hub_scores.append(float(score[0]) if len(score) > 0 else 0)

node_trace = go.Scatter(
    x=node_x, y=node_y,
    mode="markers+text",
    text=node_names,
    textposition="top center",
    textfont=dict(size=9),
    hoverinfo="text",
    marker=dict(
        showscale=True,
        colorscale="Viridis",
        color=hub_scores,
        size=20,
        colorbar=dict(
            thickness=15,
            title="Hub Score",
            xanchor="left",
        ),
        line=dict(width=2, color="white")
    ),
    showlegend=False,
)

fig4 = go.Figure(
    data=[edge_trace, node_trace],
    layout=go.Layout(
        title=dict(text="Top 20 Aviation Hub Countries — Network Graph", font=dict(size=16)),
        height=600,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Arial"),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        margin=dict(b=20, l=5, r=5, t=60),
    )
)

fig4.write_html("data/chart4_network_graph.html")
print("✅ Chart 4 saved — network graph")


# ══════════════════════════════════════════════════════
# CHART 5 — Continent-to-Continent Route Flow
# Type: Bar chart grouped by continent
# Question: Which continents are most connected to each other?
# ══════════════════════════════════════════════════════

# Map continents onto edges
continent_map = {
    "United States": "N. America", "Canada": "N. America",
    "Mexico": "N. America", "Brazil": "S. America",
    "Argentina": "S. America", "Colombia": "S. America",
    "Chile": "S. America", "Peru": "S. America",
    "United Kingdom": "Europe", "Germany": "Europe",
    "France": "Europe", "Spain": "Europe", "Italy": "Europe",
    "Netherlands": "Europe", "Turkey": "Europe", "Russia": "Europe",
    "Norway": "Europe", "Sweden": "Europe", "Switzerland": "Europe",
    "Austria": "Europe", "Portugal": "Europe", "Greece": "Europe",
    "Poland": "Europe", "Ukraine": "Europe", "Denmark": "Europe",
    "Finland": "Europe", "Czech Republic": "Europe", "Romania": "Europe",
    "Hungary": "Europe", "Belgium": "Europe", "Serbia": "Europe",
    "China": "Asia", "India": "Asia", "Japan": "Asia",
    "South Korea": "Asia", "Indonesia": "Asia", "Thailand": "Asia",
    "Malaysia": "Asia", "Singapore": "Asia", "Philippines": "Asia",
    "Vietnam": "Asia", "Taiwan": "Asia", "Hong Kong": "Asia",
    "Pakistan": "Asia", "Bangladesh": "Asia",
    "United Arab Emirates": "Middle East", "Saudi Arabia": "Middle East",
    "Qatar": "Middle East", "Kuwait": "Middle East",
    "Bahrain": "Middle East", "Oman": "Middle East",
    "Egypt": "Africa", "South Africa": "Africa", "Nigeria": "Africa",
    "Kenya": "Africa", "Ethiopia": "Africa", "Morocco": "Africa",
    "Australia": "Oceania", "New Zealand": "Oceania",
}

edges_cont = country_edges.copy()
edges_cont["source_continent"] = edges_cont["source_country"].map(continent_map).fillna("Other")
edges_cont["dest_continent"]   = edges_cont["dest_country"].map(continent_map).fillna("Other")

# Remove same-continent flows (keep only inter-continental)
inter = edges_cont[edges_cont["source_continent"] != edges_cont["dest_continent"]]

# Sum routes by continent pair
flow = (
    inter.groupby(["source_continent", "dest_continent"])["route_count"]
    .sum()
    .reset_index()
    .sort_values("route_count", ascending=False)
    .head(20)
)

fig5 = px.bar(
    flow,
    x="route_count",
    y="source_continent",
    color="dest_continent",
    orientation="h",
    barmode="group",
    title="Top Inter-Continental Aviation Route Flows",
    labels={
        "route_count"      : "Number of Routes",
        "source_continent" : "From Continent",
        "dest_continent"   : "To Continent",
    },
    color_discrete_sequence=px.colors.qualitative.Set2,
)

fig5.update_layout(
    height=500,
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(family="Arial", size=12),
    title_font_size=16,
    xaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
    legend=dict(title="To Continent"),
)

fig5.write_html("data/chart5_continent_flow.html")
print("✅ Chart 5 saved — continent flow chart")

print("\n" + "="*50)
print("ALL 5 CHARTS BUILT SUCCESSFULLY")
print("="*50)
print("\nFiles saved in data/ folder:")
print("  chart1_top_countries.html    — bar chart")
print("  chart2_world_map.html        — choropleth map")
print("  chart3_centrality_scatter.html — scatter plot")
print("  chart4_network_graph.html    — network graph")
print("  chart5_continent_flow.html   — continent flow")
print("\nOpen any .html file in your browser to preview it!")
print("\n✅ Phase 5 complete — ready to build Streamlit dashboard!")