"""
services/preprocessor.py
------------------------
Cleans and enriches raw collected data before analytics:
- Type casting & missing value imputation
- Feature engineering (mood labels, decade buckets, etc.)
- Sentiment analysis of lyric snippets
- Saves processed CSV to data/processed/
"""

from __future__ import annotations

import re
import pandas as pd
import numpy as np
from pathlib import Path

from config.settings import PROCESSED_DIR
from utils.logger import get_logger

logger = get_logger(__name__)

PROCESSED_TRACKS = PROCESSED_DIR / "tracks_clean.csv"
PROCESSED_ARTISTS = PROCESSED_DIR / "artists_clean.csv"


class DataPreprocessor:
    """
    Transforms raw DataFrames into analysis-ready form.

    Usage:
        pre = DataPreprocessor(tracks_df, artists_df)
        tracks_clean = pre.process_tracks()
        artists_clean = pre.process_artists()
    """

    def __init__(self, tracks_df: pd.DataFrame, artists_df: pd.DataFrame) -> None:
        self.raw_tracks = tracks_df.copy()
        self.raw_artists = artists_df.copy()

    # ── Tracks ─────────────────────────────────────────────────────────────────

    def process_tracks(self) -> pd.DataFrame:
        """
        Full cleaning + feature engineering pipeline for tracks.
        Returns the cleaned DataFrame and saves it to CSV.
        """
        df = self.raw_tracks.copy()
        logger.info("Processing %d raw tracks …", len(df))

        df = self._cast_types(df)
        df = self._impute_missing(df)
        df = self._add_engineered_features(df)
        df = self._add_mood_label(df)
        df = self._add_sentiment(df)
        df = self._deduplicate(df)

        df.to_csv(PROCESSED_TRACKS, index=False, encoding="utf-8-sig")
        logger.info("Saved %d clean tracks → %s", len(df), PROCESSED_TRACKS)
        return df

    def process_artists(self) -> pd.DataFrame:
        """Clean and enrich the artists DataFrame."""
        df = self.raw_artists.copy()
        logger.info("Processing %d raw artists …", len(df))

        # Ensure numeric columns
        for col in ["popularity", "followers", "lastfm_listeners", "lastfm_playcount"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

        # Parse pipe-delimited genre strings
        if "genres" in df.columns:
            df["primary_genre"] = df["genres"].apply(
                lambda g: str(g).split("|")[0] if pd.notna(g) and g else "unknown"
            )
            df["genre_count"] = df["genres"].apply(
                lambda g: len(str(g).split("|")) if pd.notna(g) and g else 0
            )

        df.to_csv(PROCESSED_ARTISTS, index=False, encoding="utf-8-sig")
        logger.info("Saved %d clean artists → %s", len(df), PROCESSED_ARTISTS)
        return df

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _cast_types(df: pd.DataFrame) -> pd.DataFrame:
        """Ensure correct dtypes for all known columns."""
        int_cols = ["popularity", "duration_ms", "release_year", "key",
                    "mode", "time_signature", "genius_pageviews"]
        float_cols = ["danceability", "energy", "valence", "acousticness",
                      "instrumentalness", "liveness", "speechiness",
                      "tempo", "loudness", "duration_min"]
        bool_cols = ["explicit"]

        for col in int_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        for col in float_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        for col in bool_cols:
            if col in df.columns:
                df[col] = df[col].astype(bool)

        return df

    @staticmethod
    def _impute_missing(df: pd.DataFrame) -> pd.DataFrame:
        """Fill NaN values with sensible defaults."""
        # Audio features → median imputation
        audio_features = ["danceability", "energy", "valence", "acousticness",
                          "instrumentalness", "liveness", "speechiness"]
        for col in audio_features:
            if col in df.columns:
                df[col] = df[col].fillna(df[col].median())

        if "tempo" in df.columns:
            df["tempo"] = df["tempo"].fillna(120.0)
        if "loudness" in df.columns:
            df["loudness"] = df["loudness"].fillna(-8.0)

        # Categorical → "unknown"
        for col in ["album", "release_date", "genres", "lyrics_snippet"]:
            if col in df.columns:
                df[col] = df[col].fillna("unknown")

        if "popularity" in df.columns:
            df["popularity"] = df["popularity"].fillna(0)

        return df

    @staticmethod
    def _add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
        """Derive new columns useful for analysis."""
        # Decade bucket
        if "release_year" in df.columns:
            def to_decade(y) -> str:
                try:
                    y = int(y)
                    return f"{(y // 10) * 10}s"
                except (ValueError, TypeError):
                    return "unknown"
            df["decade"] = df["release_year"].apply(to_decade)

        # Duration bucket
        if "duration_min" in df.columns:
            df["duration_bucket"] = pd.cut(
                df["duration_min"],
                bins=[0, 2.5, 3.5, 4.5, 100],
                labels=["Short (<2.5m)", "Medium (2.5-3.5m)", "Long (3.5-4.5m)", "Very long (>4.5m)"],
            )

        # Mode label
        if "mode" in df.columns:
            df["mode_label"] = df["mode"].map({1: "Major", 0: "Minor"})

        # Key label
        KEY_NAMES = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
        if "key" in df.columns:
            df["key_label"] = df["key"].apply(
                lambda k: KEY_NAMES[int(k)] if pd.notna(k) and 0 <= int(k) <= 11 else "?"
            )

        # Primary genre from pipe-delimited string
        if "genres" in df.columns:
            df["primary_genre"] = df["genres"].apply(
                lambda g: str(g).split("|")[0].strip() if pd.notna(g) and g != "unknown" else "unknown"
            )

        return df

    @staticmethod
    def _add_mood_label(df: pd.DataFrame) -> pd.DataFrame:
        """
        Assign a human-readable mood label based on energy × valence quadrant.
        This is a rule-based approximation; clustering overwrites this later.
        """
        if "energy" not in df.columns or "valence" not in df.columns:
            return df

        def quadrant(row) -> str:
            e, v = row["energy"], row["valence"]
            if e >= 0.5 and v >= 0.5:
                return "Energetic / Happy"
            elif e >= 0.5 and v < 0.5:
                return "Energetic / Dark"
            elif e < 0.5 and v >= 0.5:
                return "Calm / Positive"
            else:
                return "Melancholic / Calm"

        df["mood_quadrant"] = df.apply(quadrant, axis=1)
        return df

    @staticmethod
    def _add_sentiment(df: pd.DataFrame) -> pd.DataFrame:
        """
        Approximate sentiment score using valence as a proxy when lyrics
        are not available. If lyrics exist, use a simple positive/negative
        word count heuristic (TextBlob not always available in CIS locale).
        """
        if "lyrics_snippet" in df.columns and "valence" in df.columns:
            def score(row) -> float:
                lyrics = str(row.get("lyrics_snippet", ""))
                if lyrics and lyrics != "unknown":
                    # Very simple heuristic: positive / negative word presence
                    pos_words = ["любовь", "счастье", "свет", "радость", "жизнь", "красота"]
                    neg_words = ["смерть", "боль", "тьма", "страх", "конец", "ненависть"]
                    pos = sum(w in lyrics.lower() for w in pos_words)
                    neg = sum(w in lyrics.lower() for w in neg_words)
                    if pos + neg == 0:
                        return float(row.get("valence", 0.5))
                    return (pos - neg) / (pos + neg)
                return float(row.get("valence", 0.5))

            df["sentiment_score"] = df.apply(score, axis=1)
        return df

    @staticmethod
    def _deduplicate(df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate tracks by (artist, title), keeping highest popularity."""
        if "artist" in df.columns and "title" in df.columns:
            df = df.sort_values("popularity", ascending=False)
            df = df.drop_duplicates(subset=["artist", "title"], keep="first")
        return df.reset_index(drop=True)


def load_processed_tracks() -> pd.DataFrame:
    if PROCESSED_TRACKS.exists():
        return pd.read_csv(PROCESSED_TRACKS, encoding="utf-8-sig")
    return pd.DataFrame()


def load_processed_artists() -> pd.DataFrame:
    if PROCESSED_ARTISTS.exists():
        return pd.read_csv(PROCESSED_ARTISTS, encoding="utf-8-sig")
    return pd.DataFrame()
