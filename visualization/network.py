"""
visualization/network.py
------------------------
Artist similarity network graph using NetworkX + Plotly.
"""

from __future__ import annotations

from pathlib import Path

import networkx as nx
import pandas as pd
import plotly.graph_objects as go

from config.settings import RAW_DIR, COLOR_PALETTE
from visualization.style import plotly_fig, CARD_BG, TEXT_COLOR
from utils.logger import get_logger

logger = get_logger(__name__)

NETWORK_CSV = RAW_DIR / "artist_network.csv"


def build_network(df_artists: pd.DataFrame | None = None) -> nx.Graph:
    """
    Build a NetworkX graph from artist similarity edges.
    Edges come from the artist_network.csv or the related_artists column.
    """
    G = nx.Graph()

    if NETWORK_CSV.exists():
        edges_df = pd.read_csv(NETWORK_CSV)
        for _, row in edges_df.iterrows():
            G.add_edge(row["source"], row["target"])
    elif df_artists is not None and "related_artists" in df_artists.columns:
        for _, row in df_artists.iterrows():
            artist = row["name"]
            related = str(row.get("related_artists", "")).split("|")
            for rel in related:
                if rel.strip():
                    G.add_edge(artist, rel.strip())

    logger.info("Network: %d nodes, %d edges", G.number_of_nodes(), G.number_of_edges())
    return G


def artist_network_figure(
    df_artists: pd.DataFrame | None = None,
    highlight_artist: str | None = None,
) -> go.Figure:
    """
    Return a Plotly figure of the artist similarity network.
    Nodes sized by degree; highlighted artist node is accented.
    """
    G = build_network(df_artists)
    if G.number_of_nodes() == 0:
        return go.Figure().update_layout(
            title="No network data available",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(22,27,34,1)",
        )

    pos = nx.spring_layout(G, seed=42, k=1.5)
    degrees = dict(G.degree())
    max_deg = max(degrees.values(), default=1)

    # ── Edge traces ────────────────────────────────────────────────────────────
    edge_x, edge_y = [], []
    for u, v in G.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        mode="lines",
        line=dict(width=0.8, color="rgba(255,255,255,0.12)"),
        hoverinfo="none",
    )

    # ── Node traces ────────────────────────────────────────────────────────────
    node_x = [pos[n][0] for n in G.nodes()]
    node_y = [pos[n][1] for n in G.nodes()]
    node_sizes = [8 + (degrees[n] / max_deg) * 30 for n in G.nodes()]
    node_colors = [
        "#E63946" if n == highlight_artist else COLOR_PALETTE[1]
        for n in G.nodes()
    ]

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        text=list(G.nodes()),
        textposition="top center",
        textfont=dict(size=9, color=TEXT_COLOR),
        marker=dict(
            size=node_sizes,
            color=node_colors,
            line=dict(color="rgba(255,255,255,0.2)", width=1),
        ),
        hovertext=[f"{n} (connections: {degrees[n]})" for n in G.nodes()],
        hoverinfo="text",
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=CARD_BG,
        showlegend=False,
        hovermode="closest",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        title=dict(text="🕸️ Artist Similarity Network", font=dict(size=18, color=TEXT_COLOR)),
        margin=dict(l=10, r=10, t=50, b=10),
    )
    return fig
