"""
visualization/charts.py
-----------------------
All Plotly chart factories used by the Streamlit dashboard.
Each function accepts a DataFrame and returns a go.Figure.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config.settings import AUDIO_FEATURES, COLOR_PALETTE
from visualization.style import plotly_fig, PLOTLY_LAYOUT, CARD_BG, TEXT_COLOR, GRID_COLOR


# ── Bar charts ─────────────────────────────────────────────────────────────────

def bar_top_artists(df_summary: pd.DataFrame) -> go.Figure:
    """Horizontal bar: top artists by mean popularity."""
    fig = px.bar(
        df_summary.sort_values("mean_popularity"),
        x="mean_popularity", y="artist",
        orientation="h",
        color="mean_popularity",
        color_continuous_scale=["#264653", "#E63946"],
        text="mean_popularity",
        hover_data=["track_count"],
    )
    fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    fig.update_coloraxes(showscale=False)
    return plotly_fig(fig, "🎵 Top Artists by Popularity")


def bar_genre_distribution(df_genres: pd.DataFrame) -> go.Figure:
    """Horizontal bar: genre frequency."""
    fig = px.bar(
        df_genres.sort_values("count"),
        x="count", y="genre",
        orientation="h",
        color="count",
        color_continuous_scale=["#457B9D", "#E63946"],
    )
    fig.update_coloraxes(showscale=False)
    return plotly_fig(fig, "🎸 Genre Distribution")


# ── Line / area charts ─────────────────────────────────────────────────────────

def line_popularity_trend(df_trend: pd.DataFrame) -> go.Figure:
    """Line chart: popularity over years with track count as area."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=df_trend["release_year"], y=df_trend["mean_popularity"],
            name="Mean Popularity", line=dict(color="#E63946", width=3),
            fill="tozeroy", fillcolor="rgba(230,57,70,0.15)",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(
            x=df_trend["release_year"], y=df_trend["track_count"],
            name="Track Count", marker_color="rgba(69,123,157,0.4)",
        ),
        secondary_y=True,
    )
    fig.update_layout(**PLOTLY_LAYOUT, title=dict(text="📈 Popularity Trend by Year", font=dict(size=18)))
    fig.update_yaxes(title_text="Mean Popularity", secondary_y=False)
    fig.update_yaxes(title_text="Track Count", secondary_y=True)
    return fig


def line_feature_trends(df_trend: pd.DataFrame) -> go.Figure:
    """Multi-line chart: audio feature trends over years."""
    features = [c for c in ["energy", "valence", "danceability", "acousticness"] if c in df_trend.columns]
    colors = ["#E63946", "#457B9D", "#A8DADC", "#F4A261"]
    fig = go.Figure()
    for feat, color in zip(features, colors):
        fig.add_trace(go.Scatter(
            x=df_trend["release_year"], y=df_trend[feat],
            name=feat.capitalize(),
            line=dict(color=color, width=2.5),
            mode="lines+markers",
            marker=dict(size=5),
        ))
    return plotly_fig(fig, "🌊 Audio Feature Trends Over Time")


# ── Scatter plots ──────────────────────────────────────────────────────────────

def scatter_energy_valence(df: pd.DataFrame, color_col: str = "mood_quadrant") -> go.Figure:
    """Scatter: energy vs valence, coloured by mood quadrant."""
    fig = px.scatter(
        df,
        x="valence", y="energy",
        color=color_col,
        hover_data=["title", "artist", "popularity"],
        opacity=0.75,
        size="popularity",
        size_max=18,
        color_discrete_sequence=COLOR_PALETTE,
    )
    # Quadrant lines
    fig.add_hline(y=0.5, line_dash="dash", line_color="rgba(255,255,255,0.2)")
    fig.add_vline(x=0.5, line_dash="dash", line_color="rgba(255,255,255,0.2)")
    # Quadrant labels
    for (x, y, text) in [
        (0.1, 0.9, "⚡ Dark Energy"), (0.75, 0.9, "🔥 High Energy"),
        (0.1, 0.1, "🌧️ Melancholic"), (0.75, 0.1, "☀️ Chill Positive"),
    ]:
        fig.add_annotation(x=x, y=y, text=text, showarrow=False,
                           font=dict(color="rgba(255,255,255,0.4)", size=10))
    return plotly_fig(fig, "🌡️ Mood Map: Energy × Valence")


def scatter_pca_clusters(df: pd.DataFrame) -> go.Figure:
    """Scatter: PCA projection coloured by cluster label."""
    if "pca_x" not in df.columns:
        return go.Figure()
    fig = px.scatter(
        df.dropna(subset=["pca_x", "pca_y"]),
        x="pca_x", y="pca_y",
        color="cluster_label",
        hover_data=["title", "artist", "energy", "valence"],
        opacity=0.7,
        color_discrete_sequence=COLOR_PALETTE,
    )
    return plotly_fig(fig, "🔵 Track Clusters (PCA Projection)")


# ── Heatmap ────────────────────────────────────────────────────────────────────

def heatmap_correlation(corr_df: pd.DataFrame) -> go.Figure:
    """Heatmap of audio feature correlations."""
    fig = go.Figure(go.Heatmap(
        z=corr_df.values,
        x=corr_df.columns.tolist(),
        y=corr_df.index.tolist(),
        colorscale=[
            [0.0, "#264653"], [0.5, "#21262D"], [1.0, "#E63946"]
        ],
        zmin=-1, zmax=1,
        text=corr_df.round(2).values,
        texttemplate="%{text}",
        textfont=dict(size=10),
    ))
    return plotly_fig(fig, "🔥 Feature Correlation Heatmap")


def heatmap_artist_features(df_features: pd.DataFrame) -> go.Figure:
    """Heatmap: mean audio features per artist."""
    cols = [c for c in AUDIO_FEATURES if c in df_features.columns and c != "tempo"]
    heat_df = df_features.set_index("artist")[cols]
    fig = go.Figure(go.Heatmap(
        z=heat_df.values,
        x=cols,
        y=heat_df.index.tolist(),
        colorscale="RdYlBu",
        zmin=0, zmax=1,
        text=heat_df.round(2).values,
        texttemplate="%{text}",
        textfont=dict(size=9),
    ))
    fig.update_layout(height=max(400, len(heat_df) * 28))
    return plotly_fig(fig, "🎛️ Artist Audio Feature Heatmap")


# ── Histograms ─────────────────────────────────────────────────────────────────

def histogram_feature(df: pd.DataFrame, feature: str) -> go.Figure:
    """Histogram of a single audio feature."""
    fig = px.histogram(
        df, x=feature,
        nbins=40,
        color_discrete_sequence=["#E63946"],
        opacity=0.8,
    )
    fig.update_layout(**PLOTLY_LAYOUT, title=dict(text=f"Distribution of {feature.capitalize()}", font=dict(size=18)))
    return fig


def histogram_popularity(df: pd.DataFrame) -> go.Figure:
    """Popularity distribution histogram."""
    fig = px.histogram(
        df, x="popularity",
        nbins=50,
        color_discrete_sequence=["#457B9D"],
        marginal="box",
    )
    return plotly_fig(fig, "📊 Popularity Distribution")


# ── Radar chart ────────────────────────────────────────────────────────────────

def radar_artist_comparison(
    df_features: pd.DataFrame, artists: list[str]
) -> go.Figure:
    """
    Radar/spider chart comparing audio profiles of selected artists.
    Features are normalised 0-1 (tempo excluded for scale reasons).
    """
    radar_features = [c for c in
        ["danceability", "energy", "valence", "acousticness",
         "instrumentalness", "liveness", "speechiness"]
        if c in df_features.columns
    ]
    fig = go.Figure()
    colors = COLOR_PALETTE[:len(artists)]
    for artist, color in zip(artists, colors):
        row = df_features[df_features["artist"] == artist]
        if row.empty:
            continue
        vals = row[radar_features].values.flatten().tolist()
        vals += [vals[0]]  # close the polygon
        fig.add_trace(go.Scatterpolar(
            r=vals,
            theta=radar_features + [radar_features[0]],
            name=artist,
            line=dict(color=color, width=2),
            fill="toself",
            fillcolor=color.replace(")", ", 0.15)").replace("rgb", "rgba") if "rgb" in color else color,
            opacity=0.8,
        ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        polar=dict(
            bgcolor=CARD_BG,
            radialaxis=dict(visible=True, range=[0, 1], color="rgba(255,255,255,0.3)"),
            angularaxis=dict(color="rgba(255,255,255,0.5)"),
        ),
        title=dict(text="🕸️ Artist Audio Profile Comparison", font=dict(size=18)),
    )
    return fig


# ── Pie / donut ────────────────────────────────────────────────────────────────

def donut_mood_distribution(df_mood: pd.DataFrame) -> go.Figure:
    """Donut chart of mood quadrant distribution."""
    fig = px.pie(
        df_mood, names="mood", values="count",
        hole=0.55,
        color_discrete_sequence=COLOR_PALETTE,
    )
    fig.update_traces(textposition="outside", textinfo="label+percent")
    return plotly_fig(fig, "🎭 Mood Distribution")


# ── Box plots ─────────────────────────────────────────────────────────────────

def boxplot_feature_by_artist(df: pd.DataFrame, feature: str, top_n: int = 12) -> go.Figure:
    """Box plot of *feature* distribution across top artists."""
    top_artists = df["artist"].value_counts().head(top_n).index.tolist()
    fdf = df[df["artist"].isin(top_artists)]
    fig = px.box(
        fdf, x="artist", y=feature,
        color="artist",
        color_discrete_sequence=COLOR_PALETTE,
        points="outliers",
    )
    fig.update_xaxes(tickangle=-35)
    fig.update_layout(**PLOTLY_LAYOUT, showlegend=False,
                      title=dict(text=f"📦 {feature.capitalize()} Distribution by Artist", font=dict(size=18)))
    return fig
