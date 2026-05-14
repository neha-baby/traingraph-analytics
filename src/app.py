# src/app.py
# PURPOSE: Streamlit dashboard — ties all analysis and charts together
# This is the live web app that runs in the browser

import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import networkx as nx
import streamlit as st

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Page config — must be FIRST streamlit command ─────────────────────────────
st.set_page_config(
    page_title="Global Aviation Hub Analytics",
    page_icon="✈️",
    layout="wide",                  # use full browser width
    initial_sidebar_state="expanded"
)

# ── Load data — cached so it only loads once ──────────────────────────────────
# @st.cache_data means: run this function once, save the result
# Next time someone visits, use the saved result — much faster
@st.cache_data
def load_data():
    centrality    = pd.read_csv("data/centrality_scores.csv")
    country_stats = pd.read_csv("data/country_stats.csv")
    country_edges = pd.read_csv("data/country_edges.csv")
    return centrality, country_stats, country_edges

centrality, country_stats, country_edges = load_data()

# ── Continent mapping ──────────────────────────────────────────────────────────
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
centrality["continent"] = centrality["country"].map(continent_map).fillna("Other")

# ══════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════
st.sidebar.image(
    "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/280px-PNG_transparency_demonstration_1.png",
    width=50
)
st.sidebar.title("✈️ Aviation Analytics")
st.sidebar.markdown("**Global Hub Analysis**")
st.sidebar.markdown("---")

# Filter by continent
all_continents = ["All"] + sorted(centrality["continent"].dropna().unique().tolist())
selected_continent = st.sidebar.selectbox(
    "Filter by Continent",
    all_continents,
    help="Filter all charts to show only countries from this continent"
)

# Filter by minimum routes
min_routes = st.sidebar.slider(
    "Minimum Total Routes",
    min_value=0,
    max_value=1000,
    value=0,
    step=50,
    help="Only show countries with at least this many international routes"
)

# Top N countries slider
top_n = st.sidebar.slider(
    "Top N Countries to show",
    min_value=5,
    max_value=30,
    value=15,
    step=5,
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Dataset**")
st.sidebar.markdown(f"🌍 {len(centrality)} countries")
st.sidebar.markdown(f"🛣️ {country_edges['route_count'].sum():,} routes")
st.sidebar.markdown(f"🔗 {len(country_edges):,} connections")
st.sidebar.markdown("---")
st.sidebar.markdown("Source: [OpenFlights](https://openflights.org/data.html)")

# ── Apply filters ──────────────────────────────────────────────────────────────
filtered = centrality.copy()
if selected_continent != "All":
    filtered = filtered[filtered["continent"] == selected_continent]
filtered = filtered[filtered["total_routes"] >= min_routes]

# ══════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════
st.title("✈️ Global Aviation Hub Analytics")
st.markdown(
    "Analysing **67,663 flight routes** across **237 countries** using "
    "graph theory — degree centrality, betweenness centrality, and PageRank "
    "to identify the world's true aviation hub countries."
)

# ── KPI metrics row ────────────────────────────────────────────────────────────
# st.columns splits the page into equal-width columns side by side
col1, col2, col3, col4 = st.columns(4)

top_hub     = centrality.nlargest(1, "hub_score").iloc[0]
top_bridge  = centrality.nlargest(1, "betweenness").iloc[0]
top_routes  = centrality.nlargest(1, "total_routes").iloc[0]
top_pr      = centrality.nlargest(1, "pagerank").iloc[0]

with col1:
    st.metric(
        label="🏆 Top Hub Country",
        value=top_hub["country"],
        delta=f"Hub score: {top_hub['hub_score']:.3f}"
    )
with col2:
    st.metric(
        label="🌉 Biggest Bridge",
        value=top_bridge["country"],
        delta=f"Betweenness: {top_bridge['betweenness']:.3f}"
    )
with col3:
    st.metric(
        label="🛣️ Most Routes",
        value=top_routes["country"],
        delta=f"{int(top_routes['total_routes']):,} routes"
    )
with col4:
    st.metric(
        label="⭐ Highest PageRank",
        value=top_pr["country"],
        delta=f"PageRank: {top_pr['pagerank']:.4f}"
    )

st.markdown("---")

# ══════════════════════════════════════════════════════
# ROW 1 — Bar chart + World Map side by side
# ══════════════════════════════════════════════════════
col_left, col_right = st.columns([1, 1.5])

with col_left:
    st.subheader("Top Countries by Route Count")

    top_data = filtered.nlargest(top_n, "total_routes").sort_values("total_routes")

    fig1 = px.bar(
        top_data,
        x="total_routes",
        y="country",
        orientation="h",
        color="hub_score",
        color_continuous_scale="Teal",
        labels={"total_routes": "Total Routes", "country": "", "hub_score": "Hub Score"},
        text="total_routes",
    )
    fig1.update_traces(textposition="outside")
    fig1.update_layout(
        height=420,
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=0, r=10, t=10, b=0),
        coloraxis_showscale=False,
        xaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
        yaxis=dict(showgrid=False),
    )
    st.plotly_chart(fig1, use_container_width=True)

with col_right:
    st.subheader("World Hub Score Map")

    fig2 = px.choropleth(
        filtered,
        locations="country",
        locationmode="country names",
        color="hub_score",
        hover_name="country",
        hover_data={"total_routes": True, "hub_score": ":.3f"},
        color_continuous_scale="Viridis",
        labels={"hub_score": "Hub Score"},
    )
    fig2.update_layout(
        height=420,
        margin=dict(l=0, r=0, t=0, b=0),
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
        coloraxis_colorbar=dict(title="Hub Score", thickness=12),
    )
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# ══════════════════════════════════════════════════════
# ROW 2 — Centrality Scatter + Network Graph
# ══════════════════════════════════════════════════════
col_left2, col_right2 = st.columns(2)

with col_left2:
    st.subheader("Degree vs Betweenness Centrality")
    st.caption("Bubble size = total routes · Color = PageRank · Top 40 countries shown")

    top40 = filtered.nlargest(40, "hub_score")

    fig3 = px.scatter(
        top40,
        x="degree_centrality",
        y="betweenness",
        size="total_routes",
        color="pagerank",
        hover_name="country",
        color_continuous_scale="RdYlGn",
        text="country",
        labels={
            "degree_centrality": "Degree Centrality",
            "betweenness"      : "Betweenness Centrality",
            "total_routes"     : "Total Routes",
            "pagerank"         : "PageRank",
        },
    )
    fig3.update_traces(
        textposition="top center",
        textfont=dict(size=8),
        marker=dict(opacity=0.8)
    )
    fig3.update_layout(
        height=420,
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
        yaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig3, use_container_width=True)

with col_right2:
    st.subheader("Top 20 Countries Network Graph")
    st.caption("Node color = hub score · Edges = direct aviation connections")

    top20_countries = filtered.nlargest(20, "hub_score")["country"].tolist()
    top20_edges = country_edges[
        country_edges["source_country"].isin(top20_countries) &
        country_edges["dest_country"].isin(top20_countries)
    ]

    G = nx.DiGraph()
    for _, row in top20_edges.iterrows():
        G.add_edge(row["source_country"], row["dest_country"], weight=row["route_count"])

    if len(G.nodes()) > 0:
        pos = nx.spring_layout(G, seed=42, k=2)

        edge_x, edge_y = [], []
        for u, v in G.edges():
            x0, y0 = pos[u]
            x1, y1 = pos[v]
            edge_x += [x0, x1, None]
            edge_y += [y0, y1, None]

        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            mode="lines",
            line=dict(width=0.5, color="#cccccc"),
            hoverinfo="none",
            showlegend=False,
        )

        node_names  = list(G.nodes())
        node_x      = [pos[n][0] for n in node_names]
        node_y      = [pos[n][1] for n in node_names]
        hub_scores  = []
        for name in node_names:
            score = centrality[centrality["country"] == name]["hub_score"].values
            hub_scores.append(float(score[0]) if len(score) > 0 else 0)

        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode="markers+text",
            text=node_names,
            textposition="top center",
            textfont=dict(size=8),
            hoverinfo="text",
            marker=dict(
                colorscale="Viridis",
                color=hub_scores,
                size=18,
                showscale=True,
                colorbar=dict(thickness=10, title="Hub Score"),
                line=dict(width=1, color="white")
            ),
            showlegend=False,
        )

        fig4 = go.Figure(
            data=[edge_trace, node_trace],
            layout=go.Layout(
                height=420,
                plot_bgcolor="white",
                paper_bgcolor="white",
                margin=dict(l=0, r=0, t=10, b=0),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            )
        )
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("No network data available for current filter selection.")

st.markdown("---")

# ══════════════════════════════════════════════════════
# ROW 3 — Continent Flow + Data Table
# ══════════════════════════════════════════════════════
col_left3, col_right3 = st.columns(2)

with col_left3:
    st.subheader("Inter-Continental Route Flows")

    edges_cont = country_edges.copy()
    edges_cont["source_continent"] = edges_cont["source_country"].map(continent_map).fillna("Other")
    edges_cont["dest_continent"]   = edges_cont["dest_country"].map(continent_map).fillna("Other")
    inter = edges_cont[edges_cont["source_continent"] != edges_cont["dest_continent"]]
    flow  = (
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
        labels={
            "route_count"      : "Number of Routes",
            "source_continent" : "From",
            "dest_continent"   : "To",
        },
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig5.update_layout(
        height=420,
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(title="To Continent"),
        xaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
    )
    st.plotly_chart(fig5, use_container_width=True)

with col_right3:
    st.subheader("Country Rankings Table")
    st.caption("Sorted by hub score — all centrality metrics combined")

    table_data = filtered.nlargest(top_n, "hub_score")[[
        "country", "total_routes", "degree_centrality",
        "betweenness", "pagerank", "hub_score"
    ]].copy()

    table_data.columns = ["Country", "Routes", "Degree", "Betweenness", "PageRank", "Hub Score"]
    table_data = table_data.reset_index(drop=True)
    table_data.index = table_data.index + 1  # start ranking from 1

    # Round numbers for display
    for col in ["Degree", "Betweenness", "PageRank", "Hub Score"]:
        table_data[col] = table_data[col].round(4)

    st.dataframe(
        table_data,
        use_container_width=True,
        height=400,
    )

st.markdown("---")

# ══════════════════════════════════════════════════════
# FOOTER — Key Insights
# ══════════════════════════════════════════════════════
st.subheader("🔍 Key Findings")

insight1, insight2, insight3 = st.columns(3)

with insight1:
    st.info(
        "**France is the #1 Hub**\n\n"
        "France connects to 227 countries with a hub score of 1.15 — "
        "highest in the world when combining degree, betweenness and PageRank."
    )
with insight2:
    st.warning(
        "**Qatar is the biggest bridge**\n\n"
        "Qatar has the highest betweenness centrality (0.1157) — "
        "it sits on more shortest paths between countries than any other nation, "
        "making it a critical aviation bridge between East and West."
    )
with insight3:
    st.success(
        "**Europe dominates globally**\n\n"
        "Europe accounts for 31,974 international routes — "
        "nearly 3x more than Asia (11,584) and 4x more than North America (7,336)."
    )

st.markdown(
    "<div style='text-align:center;color:gray;font-size:12px;margin-top:20px'>"
    "Built with Python · Pandas · NetworkX · Neo4j · Plotly · Streamlit · "
    "Data: OpenFlights (67,663 routes, 237 countries)"
    "</div>",
    unsafe_allow_html=True
)