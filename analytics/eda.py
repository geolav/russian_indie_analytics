"""
analytics/eda.py
----------------
Exploratory Data Analysis module.
All functions are pure transformations: DataFrame in → summary DataFrame out.
No side effects; visualization is handled in the visualization layer.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Optional

from config.settings import AUDIO_FEATURES
from utils.logger import get_logger

logger = get_logger(__name__)


# ── Artist-level ────────────────────────────────────────────────────────────────

def top_artists_by_popularity(df: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    """Return top *top_n* artists ranked by mean track popularity."""
    return (
        df.groupby("artist")["popularity"]
        .agg(mean_popularity="mean", track_count="count", max_popularity="max")
        .sort_values("mean_popularity", ascending=False)
        .head(top_n)
        .reset_index()
    )


def top_artists_by_followers(df_artists: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    """Return top artists by Spotify follower count."""
    if "followers" not in df_artists.columns:
        return pd.DataFrame()
    return (
        df_artists[["name", "followers", "popularity", "primary_genre"]]
        .sort_values("followers", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )


def artist_track_counts(df: pd.DataFrame) -> pd.DataFrame:
    """Return number of tracks per artist."""
    return (
        df.groupby("artist")
        .size()
        .rename("track_count")
        .sort_values(ascending=False)
        .reset_index()
    )


# ── Genre analysis ─────────────────────────────────────────────────────────────

def genre_distribution(df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    """
    Explode pipe-delimited genre strings and return genre frequency table.
    """
    if "genres" not in df.columns:
        return pd.DataFrame(columns=["genre", "count"])
    exploded = df["genres"].dropna().str.split("|").explode().str.strip()
    exploded = exploded[exploded != "unknown"]
    return (
        exploded.value_counts()
        .head(top_n)
        .rename_axis("genre")
        .reset_index(name="count")
    )


def primary_genre_popularity(df: pd.DataFrame) -> pd.DataFrame:
    """Mean popularity and track count per primary genre."""
    if "primary_genre" not in df.columns:
        return pd.DataFrame()
    return (
        df.groupby("primary_genre")
        .agg(
            mean_popularity=("popularity", "mean"),
            track_count=("popularity", "count"),
            mean_energy=("energy", "mean"),
            mean_valence=("valence", "mean"),
        )
        .sort_values("mean_popularity", ascending=False)
        .reset_index()
    )


# ── Audio features ─────────────────────────────────────────────────────────────

def audio_feature_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Descriptive statistics for all audio features."""
    cols = [c for c in AUDIO_FEATURES if c in df.columns]
    return df[cols].describe().T.round(4)


def feature_correlation(df: pd.DataFrame) -> pd.DataFrame:
    """Pearson correlation matrix for audio features + popularity."""
    cols = [c for c in AUDIO_FEATURES + ["popularity"] if c in df.columns]
    return df[cols].corr().round(3)


def audio_features_by_artist(df: pd.DataFrame) -> pd.DataFrame:
    """Mean audio features per artist (for radar charts)."""
    cols = [c for c in AUDIO_FEATURES if c in df.columns]
    return df.groupby("artist")[cols].mean().round(4).reset_index()


# ── Temporal trends ─────────────────────────────────────────────────────────────

def popularity_by_year(df: pd.DataFrame) -> pd.DataFrame:
    """Mean track popularity per release year."""
    if "release_year" not in df.columns:
        return pd.DataFrame()
    return (
        df.dropna(subset=["release_year"])
        .groupby("release_year")
        .agg(
            mean_popularity=("popularity", "mean"),
            track_count=("popularity", "count"),
            mean_energy=("energy", "mean"),
            mean_valence=("valence", "mean"),
            mean_danceability=("danceability", "mean"),
        )
        .sort_index()
        .reset_index()
    )


def feature_trends_by_year(df: pd.DataFrame) -> pd.DataFrame:
    """Mean audio features grouped by release year for trend analysis."""
    if "release_year" not in df.columns:
        return pd.DataFrame()
    cols = [c for c in ["release_year"] + AUDIO_FEATURES if c in df.columns]
    return (
        df[cols]
        .dropna(subset=["release_year"])
        .groupby("release_year")
        .mean()
        .round(4)
        .reset_index()
    )


# ── Mood & Sentiment ────────────────────────────────────────────────────────────

def mood_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Track count per mood quadrant."""
    if "mood_quadrant" not in df.columns:
        return pd.DataFrame()
    return (
        df["mood_quadrant"]
        .value_counts()
        .rename_axis("mood")
        .reset_index(name="count")
    )


def sentiment_by_artist(df: pd.DataFrame) -> pd.DataFrame:
    """Mean sentiment score per artist."""
    if "sentiment_score" not in df.columns:
        return pd.DataFrame()
    return (
        df.groupby("artist")["sentiment_score"]
        .mean()
        .round(4)
        .sort_values(ascending=False)
        .rename_axis("artist")
        .reset_index(name="mean_sentiment")
    )


# ── Popular tracks table ────────────────────────────────────────────────────────

def top_tracks_table(
    df: pd.DataFrame,
    top_n: int = 50,
    artist: Optional[str] = None,
    genre: Optional[str] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
) -> pd.DataFrame:
    """
    Return a filtered table of top tracks for dashboard display.
    All filters are optional.
    """
    fdf = df.copy()
    if artist:
        fdf = fdf[fdf["artist"] == artist]
    if genre:
        fdf = fdf[fdf["genres"].str.contains(genre, na=False, case=False)]
    if year_min and "release_year" in fdf.columns:
        fdf = fdf[fdf["release_year"] >= year_min]
    if year_max and "release_year" in fdf.columns:
        fdf = fdf[fdf["release_year"] <= year_max]

    display_cols = [c for c in [
        "title", "artist", "album", "release_year", "popularity",
        "duration_min", "energy", "valence", "danceability",
        "mood_quadrant", "primary_genre",
    ] if c in fdf.columns]

    return (
        fdf[display_cols]
        .sort_values("popularity", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )
