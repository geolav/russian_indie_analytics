"""
services/demo_data.py
---------------------
Generates realistic synthetic data for demonstration / testing
when real API credentials are not available.
All distributions are calibrated to match real Russian indie music patterns.
"""

from __future__ import annotations

import random
import numpy as np
import pandas as pd
from pathlib import Path

from config.settings import RAW_DIR, SEED_ARTISTS
from utils.logger import get_logger

logger = get_logger(__name__)

RNG = np.random.default_rng(42)


# Mood archetypes: (danceability, energy, valence, acousticness) mean ± std
MOOD_PROFILES = {
    "melancholic":  dict(danceability=(0.35, 0.10), energy=(0.35, 0.10), valence=(0.22, 0.08), acousticness=(0.65, 0.15)),
    "energetic":    dict(danceability=(0.72, 0.08), energy=(0.82, 0.08), valence=(0.55, 0.12), acousticness=(0.15, 0.10)),
    "dreamy":       dict(danceability=(0.50, 0.10), energy=(0.45, 0.10), valence=(0.48, 0.12), acousticness=(0.55, 0.15)),
    "angry":        dict(danceability=(0.55, 0.10), energy=(0.78, 0.10), valence=(0.20, 0.08), acousticness=(0.12, 0.10)),
}

GENRES_BY_ARTIST = {
    "Земфира":         ["russian indie rock", "alternative rock", "russian rock"],
    "IC3PEAK":         ["russian darkwave", "electropop", "post-punk"],
    "Монеточка":       ["russian indie pop", "indie pop", "folk pop"],
    "Shortparis":      ["russian post-punk", "art rock", "new wave"],
    "Молчат Дома":     ["post-punk", "darkwave", "cold wave"],
    "Аигел":           ["russian hip-hop", "electropop", "experimental"],
    "Kate NV":         ["art pop", "experimental", "electronic"],
    "Порнофильмы":     ["russian alternative rock", "indie rock"],
    "Лауд":            ["russian indie pop", "bedroom pop"],
    "Антоха МС":       ["russian indie folk", "lo-fi", "indie pop"],
    "Нервы":           ["russian indie rock", "pop rock"],
    "Therr Maitz":     ["nu-disco", "electropop", "indie dance"],
    "Tesla Boy":       ["synthpop", "new wave", "electropop"],
    "Kedr Livanskiy":  ["russian techno", "electronic", "ambient"],
    "Motorama":        ["post-punk", "russian indie", "new wave"],
    "Сансара":         ["russian indie rock", "folk rock"],
    "Дора":            ["russian indie pop", "electropop"],
    "Хаски":           ["russian hip-hop", "spoken word", "alternative"],
    "Flёur":           ["russian dream pop", "folk", "chamber pop"],
    "Сплин":           ["russian rock", "alternative rock"],
    "Би-2":            ["russian rock", "alternative", "post-grunge"],
    "Мумий Тролль":    ["russian indie pop", "art rock"],
    "Звери":           ["russian pop rock", "alternative"],
    "Иван Дорн":       ["nu-disco", "soul", "electropop"],
    "Pompeya":         ["dream pop", "shoegaze", "indie dance"],
}

ALBUMS_BY_ARTIST: dict[str, list[str]] = {
    "Земфира":     ["Земфира", "Прости меня моя любовь", "14 недель тишины", "Спасибо"],
    "IC3PEAK":     ["Сладкая жизнь", "ПЛАК", "Сказка"],
    "Монеточка":   ["Раньше было лучше", "Сделано в России", "Знаки препинания"],
    "Shortparis":  ["Пасха", "Так закалялась сталь", "Яблоневый сад"],
    "Молчат Дома": ["Этажи", "Монумент", "Люди как реки"],
}


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def generate_tracks(n_per_artist: int = 15) -> pd.DataFrame:
    """
    Generate *n_per_artist* synthetic tracks per seed artist.
    Returns a DataFrame with the same columns as the real collector output.
    """
    rows = []
    artist_names = list(GENRES_BY_ARTIST.keys())
    moods = list(MOOD_PROFILES.keys())

    for artist in artist_names:
        genres = GENRES_BY_ARTIST.get(artist, ["indie"])

        # Weight mood profile by genre feel
        if any(g in genres for g in ["post-punk", "darkwave", "cold wave", "dark"]):
            mood_weights = [0.50, 0.10, 0.20, 0.20]
        elif any(g in genres for g in ["electropop", "nu-disco", "techno", "dance"]):
            mood_weights = [0.10, 0.50, 0.25, 0.15]
        elif any(g in genres for g in ["folk", "acoustic", "dream pop", "chamber"]):
            mood_weights = [0.25, 0.15, 0.45, 0.15]
        else:
            mood_weights = [0.25, 0.25, 0.25, 0.25]

        for i in range(n_per_artist):
            mood = random.choices(moods, weights=mood_weights)[0]
            profile = MOOD_PROFILES[mood]

            year = int(np.clip(RNG.normal(2017, 4), 2005, 2024))
            month = random.randint(1, 12)
            day = random.randint(1, 28)
            release_date = f"{year}-{month:02d}-{day:02d}"

            def feat(key: str) -> float:
                mu, sigma = profile[key]
                return _clamp(float(RNG.normal(mu, sigma)))

            tempo = float(np.clip(RNG.normal(122, 22), 60, 200))
            loudness = float(np.clip(RNG.normal(-8, 4), -30, 0))

            # Popularity: older tracks slightly lower, post-punk artists slightly lower
            base_pop = 45 + random.randint(0, 30)
            if year < 2012:
                base_pop -= 10
            if "post-punk" in genres or "darkwave" in genres:
                base_pop -= 5
            popularity = int(np.clip(base_pop + RNG.normal(0, 8), 0, 99))

            albums = ALBUMS_BY_ARTIST.get(artist, [f"{artist} LP {year}"])
            album = random.choice(albums)

            title_templates = [
                f"Трек {i+1}", f"Песня о {['любви','городе','ночи','себе','море'][i % 5]}",
                f"{'ABCDEF'[i % 6]}-Side", f"Opus {i+1}", f"Без названия {i+1}",
            ]
            title = random.choice(title_templates)

            rows.append({
                "track_id":        f"demo_{artist[:4]}_{i:03d}",
                "title":           title,
                "artist":          artist,
                "artist_id":       f"demo_id_{artist[:6].replace(' ','_')}",
                "album":           album,
                "release_date":    release_date,
                "release_year":    year,
                "popularity":      popularity,
                "duration_ms":     int(RNG.uniform(120_000, 330_000)),
                "duration_min":    round(float(RNG.uniform(2.0, 5.5)), 2),
                "explicit":        random.random() < 0.12,
                "preview_url":     "",
                "spotify_url":     "",
                "danceability":    round(feat("danceability"), 4),
                "energy":          round(feat("energy"), 4),
                "valence":         round(feat("valence"), 4),
                "acousticness":    round(feat("acousticness"), 4),
                "instrumentalness":round(_clamp(float(RNG.exponential(0.12))), 4),
                "liveness":        round(_clamp(float(RNG.normal(0.18, 0.08))), 4),
                "speechiness":     round(_clamp(float(RNG.exponential(0.07))), 4),
                "tempo":           round(tempo, 2),
                "loudness":        round(loudness, 3),
                "key":             random.randint(0, 11),
                "mode":            random.choice([0, 1]),
                "time_signature":  random.choice([3, 4, 4, 4, 4]),
                "lyrics_snippet":  "",
                "genius_pageviews":int(RNG.exponential(5000)),
                "mood_cluster":    None,
                "sentiment_score": None,
                "genres":          "|".join(genres),
            })

    df = pd.DataFrame(rows)
    logger.info("Generated %d demo tracks for %d artists", len(df), len(artist_names))
    return df


def generate_artists() -> pd.DataFrame:
    """Generate synthetic artist-level records."""
    rows = []
    for artist, genres in GENRES_BY_ARTIST.items():
        followers_base = int(np.clip(RNG.lognormal(12, 1.5), 5_000, 5_000_000))
        rows.append({
            "spotify_id":        f"demo_id_{artist[:6].replace(' ','_')}",
            "name":              artist,
            "genres":            "|".join(genres),
            "popularity":        int(np.clip(RNG.normal(55, 18), 5, 99)),
            "followers":         followers_base,
            "lastfm_listeners":  int(followers_base * RNG.uniform(0.4, 2.5)),
            "lastfm_playcount":  int(followers_base * RNG.uniform(10, 80)),
            "lastfm_tags":       "|".join(genres[:3]),
            "related_artists":   "",
            "image_url":         "",
        })
    df = pd.DataFrame(rows)
    logger.info("Generated %d demo artists", len(df))
    return df


def save_demo_data() -> tuple[Path, Path]:
    """Save demo data to the raw data directory and return (tracks_path, artists_path)."""
    tracks_path = RAW_DIR / "tracks.csv"
    artists_path = RAW_DIR / "artists.csv"

    generate_tracks().to_csv(tracks_path, index=False, encoding="utf-8-sig")
    generate_artists().to_csv(artists_path, index=False, encoding="utf-8-sig")
    logger.info("Demo data saved to %s", RAW_DIR)
    return tracks_path, artists_path
