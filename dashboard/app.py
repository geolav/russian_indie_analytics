"""
dashboard/app.py
----------------
Russian Indie Music Analytics — Streamlit Dashboard

Run with:
    streamlit run dashboard/app.py
"""

import sys
from pathlib import Path

# Ensure project root is on the path when running directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
import numpy as np

# ── Page config (MUST be first Streamlit call) ─────────────────────────────────
st.set_page_config(
    page_title="Russian Indie Analytics",
    page_icon="🎸",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Project imports ─────────────────────────────────────────────────────────────
from services.preprocessor import load_processed_tracks, load_processed_artists
from services.demo_data import save_demo_data
from analytics import (
    top_artists_by_popularity, genre_distribution, feature_correlation,
    audio_features_by_artist, popularity_by_year, feature_trends_by_year,
    mood_distribution, sentiment_by_artist, top_tracks_table,
    primary_genre_popularity, cluster_tracks, pca_projection,
)
from visualization import (
    bar_top_artists, bar_genre_distribution,
    line_popularity_trend, line_feature_trends,
    scatter_energy_valence, scatter_pca_clusters,
    heatmap_correlation, heatmap_artist_features,
    histogram_popularity, radar_artist_comparison,
    donut_mood_distribution, boxplot_feature_by_artist,
    artist_network_figure,
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Dark theme overrides */
    .main { background-color: #0D1117; }
    .stMetric { background: #161B22; border-radius: 10px; padding: 12px; border: 1px solid #21262D; }
    .stMetric label { color: #8B949E !important; font-size: 0.78rem !important; }
    .stMetric [data-testid="metric-container"] > div:nth-child(2) { color: #E6EDF3 !important; font-size: 1.6rem !important; }
    .block-container { padding-top: 1.5rem; }
    h1, h2, h3 { color: #E6EDF3; }
    .stSelectbox label, .stMultiselect label, .stSlider label { color: #8B949E; }
    div[data-testid="stSidebarNav"] { background: #161B22; }
    .stTabs [data-baseweb="tab"] { color: #8B949E; }
    .stTabs [aria-selected="true"] { color: #E63946 !important; border-bottom-color: #E63946 !important; }
</style>
""", unsafe_allow_html=True)


# ── Data loading ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner="Loading analytics data…")
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load or generate processed data."""
    tracks = load_processed_tracks()
    artists = load_processed_artists()

    if tracks.empty or artists.empty:
        # No real data — generate demo dataset
        from services.demo_data import generate_tracks, generate_artists
        from services.preprocessor import DataPreprocessor
        tracks_raw = generate_tracks()
        artists_raw = generate_artists()
        pre = DataPreprocessor(tracks_raw, artists_raw)
        tracks = pre.process_tracks()
        artists = pre.process_artists()

    return tracks, artists


@st.cache_data(show_spinner="Clustering tracks…")
def get_clustered_df(tracks_hash: int) -> pd.DataFrame:
    """Cluster tracks (cached by data hash)."""
    tracks, _ = load_data()
    df = cluster_tracks(tracks)
    return pca_projection(df)


# ── Sidebar ────────────────────────────────────────────────────────────────────

def render_sidebar(df: pd.DataFrame) -> dict:
    """Render sidebar filters and return filter dict."""
    with st.sidebar:
        st.markdown("## 🎸 Russian Indie\n### Music Analytics")
        st.markdown("---")

        st.markdown("### 🔍 Filters")

        # Artist filter
        artists_available = sorted(df["artist"].dropna().unique().tolist())
        selected_artists = st.multiselect(
            "Artists", artists_available,
            placeholder="All artists…",
        )

        # Genre filter
        genre_options = (
            df["primary_genre"].dropna().unique().tolist()
            if "primary_genre" in df.columns else []
        )
        genre_options = sorted(set(g for g in genre_options if g != "unknown"))
        selected_genre = st.selectbox("Genre", ["All"] + genre_options)

        # Year range
        if "release_year" in df.columns:
            years = df["release_year"].dropna().astype(int)
            year_min, year_max = int(years.min()), int(years.max())
            year_range = st.slider("Release Year", year_min, year_max, (year_min, year_max))
        else:
            year_range = (2000, 2024)

        # Popularity filter
        pop_min = st.slider("Min Popularity", 0, 100, 0)

        st.markdown("---")
        st.markdown("### ℹ️ About")
        st.caption(
            "Data sourced from Spotify & Last.fm APIs.\n\n"
            "Demo mode uses synthetic data calibrated to real Russian indie patterns.\n\n"
            "[GitHub](https://github.com) | Built with Streamlit"
        )

    return {
        "artists": selected_artists,
        "genre": selected_genre if selected_genre != "All" else None,
        "year_min": year_range[0],
        "year_max": year_range[1],
        "pop_min": pop_min,
    }


def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """Apply sidebar filters to DataFrame."""
    fdf = df.copy()
    if filters["artists"]:
        fdf = fdf[fdf["artist"].isin(filters["artists"])]
    if filters["genre"]:
        fdf = fdf[fdf["genres"].str.contains(filters["genre"], na=False, case=False)]
    if "release_year" in fdf.columns:
        fdf = fdf[
            (fdf["release_year"] >= filters["year_min"]) &
            (fdf["release_year"] <= filters["year_max"])
        ]
    fdf = fdf[fdf["popularity"] >= filters["pop_min"]]
    return fdf


# ── KPI metrics ────────────────────────────────────────────────────────────────

def render_kpis(df: pd.DataFrame, df_artists: pd.DataFrame) -> None:
    cols = st.columns(5)
    metrics = [
        ("🎵 Total Tracks", f"{len(df):,}"),
        ("🎤 Artists", f"{df['artist'].nunique():,}"),
        ("⭐ Avg Popularity", f"{df['popularity'].mean():.1f}"),
        ("⚡ Avg Energy", f"{df['energy'].mean():.2f}" if "energy" in df.columns else "N/A"),
        ("💿 Albums", f"{df['album'].nunique():,}" if "album" in df.columns else "N/A"),
    ]
    for col, (label, value) in zip(cols, metrics):
        col.metric(label, value)


# ── Tab: Overview ──────────────────────────────────────────────────────────────

def tab_overview(df: pd.DataFrame, df_artists: pd.DataFrame) -> None:
    st.markdown("## 📊 Overview")
    render_kpis(df, df_artists)
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        top_a = top_artists_by_popularity(df)
        if not top_a.empty:
            st.plotly_chart(bar_top_artists(top_a), use_container_width=True)
    with col2:
        genres = genre_distribution(df)
        if not genres.empty:
            st.plotly_chart(bar_genre_distribution(genres), use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        pop_year = popularity_by_year(df)
        if not pop_year.empty:
            st.plotly_chart(line_popularity_trend(pop_year), use_container_width=True)
    with col4:
        st.plotly_chart(histogram_popularity(df), use_container_width=True)


# ── Tab: Audio Features ────────────────────────────────────────────────────────

def tab_audio_features(df: pd.DataFrame) -> None:
    st.markdown("## 🎛️ Audio Features")

    col1, col2 = st.columns([2, 1])
    with col1:
        corr = feature_correlation(df)
        st.plotly_chart(heatmap_correlation(corr), use_container_width=True)
    with col2:
        feat_choice = st.selectbox("Feature histogram", [
            "danceability", "energy", "valence", "acousticness",
            "instrumentalness", "speechiness", "tempo",
        ])
        if feat_choice in df.columns:
            from visualization.charts import histogram_feature
            st.plotly_chart(histogram_feature(df, feat_choice), use_container_width=True)

    st.plotly_chart(
        heatmap_artist_features(audio_features_by_artist(df)),
        use_container_width=True,
    )

    feature_choices = ["danceability", "energy", "valence", "acousticness"]
    selected_feature = st.selectbox("Box plot feature", feature_choices)
    st.plotly_chart(
        boxplot_feature_by_artist(df, selected_feature), use_container_width=True
    )


# ── Tab: Mood & Clusters ───────────────────────────────────────────────────────

def tab_mood(df: pd.DataFrame) -> None:
    st.markdown("## 🎭 Mood Analysis & Clustering")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.plotly_chart(scatter_energy_valence(df), use_container_width=True)
    with col2:
        mood_dist = mood_distribution(df)
        if not mood_dist.empty:
            st.plotly_chart(donut_mood_distribution(mood_dist), use_container_width=True)

    # Cluster scatter
    st.markdown("### 🔵 Track Clustering (KMeans + PCA)")
    with st.spinner("Running clustering…"):
        df_c = cluster_tracks(df)
        df_c = pca_projection(df_c)

    if "pca_x" in df_c.columns:
        st.plotly_chart(scatter_pca_clusters(df_c), use_container_width=True)

    # Cluster stats
    if "cluster_label" in df_c.columns:
        st.markdown("**Cluster Summary**")
        cluster_summary = (
            df_c.groupby("cluster_label")
            .agg(
                count=("title", "count"),
                avg_popularity=("popularity", "mean"),
                avg_energy=("energy", "mean"),
                avg_valence=("valence", "mean"),
            )
            .round(2)
            .reset_index()
        )
        st.dataframe(cluster_summary, use_container_width=True)


# ── Tab: Trends ────────────────────────────────────────────────────────────────

def tab_trends(df: pd.DataFrame) -> None:
    st.markdown("## 📈 Temporal Trends")

    feat_trend = feature_trends_by_year(df)
    if not feat_trend.empty:
        st.plotly_chart(line_feature_trends(feat_trend), use_container_width=True)

    # Decade breakdown
    if "decade" in df.columns:
        st.markdown("### 📅 By Decade")
        decade_stats = (
            df.groupby("decade")[["popularity", "energy", "valence", "danceability"]]
            .mean()
            .round(2)
            .reset_index()
        )
        st.dataframe(decade_stats, use_container_width=True)


# ── Tab: Artist Comparison ─────────────────────────────────────────────────────

def tab_artist_comparison(df: pd.DataFrame) -> None:
    st.markdown("## 🎤 Artist Comparison")

    artists_list = sorted(df["artist"].dropna().unique().tolist())
    default_artists = artists_list[:4] if len(artists_list) >= 4 else artists_list

    selected = st.multiselect(
        "Select artists to compare (2–6)",
        artists_list,
        default=default_artists,
    )

    if len(selected) < 2:
        st.info("Select at least 2 artists to compare.")
        return

    features_df = audio_features_by_artist(df)
    st.plotly_chart(radar_artist_comparison(features_df, selected), use_container_width=True)

    # Side by side stats
    compare_cols = ["popularity", "danceability", "energy", "valence", "acousticness"]
    compare_cols = [c for c in compare_cols if c in df.columns]
    cmp = (
        df[df["artist"].isin(selected)]
        .groupby("artist")[compare_cols]
        .mean()
        .round(3)
    )
    st.markdown("**Mean Feature Comparison**")
    st.dataframe(cmp, use_container_width=True)

    # Sentiment
    sent = sentiment_by_artist(df)
    sent_filtered = sent[sent["artist"].isin(selected)] if not sent.empty else pd.DataFrame()
    if not sent_filtered.empty:
        st.markdown("**Sentiment Score (valence proxy)**")
        import plotly.express as px
        fig = px.bar(
            sent_filtered.sort_values("mean_sentiment", ascending=False),
            x="artist", y="mean_sentiment",
            color="mean_sentiment",
            color_continuous_scale=["#264653", "#E63946"],
        )
        from visualization.style import plotly_fig
        st.plotly_chart(plotly_fig(fig, "😊 Mean Sentiment by Artist"), use_container_width=True)


# ── Tab: Tracks Table ─────────────────────────────────────────────────────────

def tab_tracks(df: pd.DataFrame, filters: dict) -> None:
    st.markdown("## 💿 Tracks Explorer")

    display_df = top_tracks_table(
        df,
        top_n=200,
        artist=filters["artists"][0] if len(filters["artists"]) == 1 else None,
        genre=filters["genre"],
        year_min=filters["year_min"],
        year_max=filters["year_max"],
    )

    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("🔍 Search track title or artist", "")
    with col2:
        sort_col = st.selectbox("Sort by", ["popularity", "energy", "valence", "release_year"])

    if search:
        mask = (
            display_df["title"].str.contains(search, case=False, na=False) |
            display_df["artist"].str.contains(search, case=False, na=False)
        )
        display_df = display_df[mask]

    display_df = display_df.sort_values(sort_col, ascending=False)

    st.dataframe(
        display_df,
        use_container_width=True,
        height=520,
        column_config={
            "popularity": st.column_config.ProgressColumn("popularity", min_value=0, max_value=100),
            "energy": st.column_config.ProgressColumn("energy", min_value=0, max_value=1),
            "valence": st.column_config.ProgressColumn("valence", min_value=0, max_value=1),
        },
    )
    st.caption(f"Showing {len(display_df)} tracks")


# ── Tab: Network ──────────────────────────────────────────────────────────────

def tab_network(df_artists: pd.DataFrame) -> None:
    st.markdown("## 🕸️ Artist Similarity Network")

    highlight = st.selectbox(
        "Highlight artist",
        ["None"] + sorted(df_artists["name"].dropna().unique().tolist())
        if "name" in df_artists.columns else ["None"],
    )
    h = None if highlight == "None" else highlight

    fig = artist_network_figure(df_artists, highlight_artist=h)
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Nodes represent artists; edges connect similar artists based on Spotify's "
        "related-artists data. Node size = number of connections."
    )


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    # Header
    st.markdown(
        "<h1 style='color:#E63946; margin-bottom:0'>🎸 Russian Indie Music Analytics</h1>"
        "<p style='color:#8B949E; margin-top:4px'>Exploring the sounds, trends & moods of Russian indie music</p>",
        unsafe_allow_html=True,
    )

    tracks_df, artists_df = load_data()

    # Demo badge
    from config.settings import RAW_DIR
    if not (RAW_DIR / "tracks.csv").exists():
        st.info("📊 Running in **demo mode** with synthetic data. Add API keys in `.env` for real data.")

    filters = render_sidebar(tracks_df)
    filtered_df = apply_filters(tracks_df, filters)

    if filtered_df.empty:
        st.warning("No tracks match the current filters. Try broadening your selection.")
        return

    # Navigation tabs
    tabs = st.tabs([
        "📊 Overview",
        "🎛️ Audio Features",
        "🎭 Mood & Clusters",
        "📈 Trends",
        "🎤 Artist Comparison",
        "💿 Tracks",
        "🕸️ Network",
    ])

    with tabs[0]:
        tab_overview(filtered_df, artists_df)
    with tabs[1]:
        tab_audio_features(filtered_df)
    with tabs[2]:
        tab_mood(filtered_df)
    with tabs[3]:
        tab_trends(filtered_df)
    with tabs[4]:
        tab_artist_comparison(filtered_df)
    with tabs[5]:
        tab_tracks(filtered_df, filters)
    with tabs[6]:
        tab_network(artists_df)


if __name__ == "__main__":
    main()
