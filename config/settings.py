"""
config/settings.py
------------------
Centralized configuration management using environment variables.
All API keys and project-level constants are loaded here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# ─── API Credentials ───────────────────────────────────────────────────────────
SPOTIFY_CLIENT_ID: str = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET: str = os.getenv("SPOTIFY_CLIENT_SECRET", "")

LASTFM_API_KEY: str = os.getenv("LASTFM_API_KEY", "")
LASTFM_BASE_URL: str = "http://ws.audioscrobbler.com/2.0/"

GENIUS_ACCESS_TOKEN: str = os.getenv("GENIUS_ACCESS_TOKEN", "")
GENIUS_BASE_URL: str = "https://api.genius.com"

# ─── Paths ─────────────────────────────────────────────────────────────────────
DATA_DIR: Path = BASE_DIR / "data"
RAW_DIR: Path = DATA_DIR / "raw"
PROCESSED_DIR: Path = DATA_DIR / "processed"
CACHE_DIR: Path = DATA_DIR / "cache"

for d in [RAW_DIR, PROCESSED_DIR, CACHE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ─── Data Collection Settings ──────────────────────────────────────────────────
# Russian indie artists seed list for data collection
SEED_ARTISTS: list[str] = [
    "Земфира", "IC3PEAK", "Монеточка", "Shortparis", "Молчат Дома",
    "Аигел", "Kate NV", "Порнофильмы", "Лауд", "Антоха МС",
    "Нервы", "Therr Maitz", "Tesla Boy", "Kedr Livanskiy",
    "Motorama", "Synth Romancer", "Сансара", "Дора", "Хаски",
    "Flёur", "Сплин", "Би-2", "Мумий Тролль", "Звери",
    "Markscheider Kunst", "Starcow", "Mayak", "Boulevard Depo",
    "Иван Дорн", "Pompeya",
]

INDIE_GENRES: list[str] = [
    "russian indie", "russian alternative", "russian post-punk",
    "indie pop", "dream pop", "shoegaze", "post-punk",
    "russian electropop", "russian emo", "slacker rock",
]

# Spotify market for Russian music
SPOTIFY_MARKET: str = "RU"
MAX_TRACKS_PER_ARTIST: int = 20
REQUEST_DELAY: float = 0.3   # seconds between API calls (rate-limit safety)
CACHE_TTL_HOURS: int = 24

# ─── Analytics Settings ────────────────────────────────────────────────────────
AUDIO_FEATURES: list[str] = [
    "danceability", "energy", "valence", "acousticness",
    "instrumentalness", "liveness", "speechiness", "tempo",
]
MOOD_CLUSTERS: int = 4
RANDOM_STATE: int = 42

# ─── Visualization ─────────────────────────────────────────────────────────────
PLOT_STYLE: str = "dark_background"
COLOR_PALETTE: list[str] = [
    "#E63946", "#457B9D", "#A8DADC", "#F4A261",
    "#2A9D8F", "#E9C46A", "#264653", "#9B2226",
]
FIGURE_DPI: int = 150

# ─── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
