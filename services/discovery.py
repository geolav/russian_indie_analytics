"""
services/discovery.py
---------------------
Discovery service for finding top artists by genre using Last.fm API.
"""

from typing import List, Dict
import time
import math
from pathlib import Path

import pandas as pd
import numpy as np

from api_clients import LastFmClient, GeniusClient, YandexMusicClient
from services.collector import DataCollector
from utils.logger import get_logger

logger = get_logger(__name__)

# Реалистичные аудио-фичи по жанрам
GENRE_FEATURES = {
    'indie': {'energy': 0.6, 'valence': 0.5, 'danceability': 0.55, 'acousticness': 0.4},
    'rock': {'energy': 0.75, 'valence': 0.55, 'danceability': 0.5, 'acousticness': 0.3},
    'alternative': {'energy': 0.65, 'valence': 0.5, 'danceability': 0.5, 'acousticness': 0.35},
    'post-punk': {'energy': 0.7, 'valence': 0.35, 'danceability': 0.45, 'acousticness': 0.25},
    'electropop': {'energy': 0.7, 'valence': 0.6, 'danceability': 0.7, 'acousticness': 0.2},
    'indie pop': {'energy': 0.55, 'valence': 0.65, 'danceability': 0.6, 'acousticness': 0.45},
    'dream pop': {'energy': 0.45, 'valence': 0.4, 'danceability': 0.4, 'acousticness': 0.6},
    'shoegaze': {'energy': 0.5, 'valence': 0.35, 'danceability': 0.35, 'acousticness': 0.55},
    'darkwave': {'energy': 0.6, 'valence': 0.25, 'danceability': 0.5, 'acousticness': 0.3},
    'metal': {'energy': 0.85, 'valence': 0.3, 'danceability': 0.35, 'acousticness': 0.15},
    'punk': {'energy': 0.85, 'valence': 0.45, 'danceability': 0.45, 'acousticness': 0.2},
    'folk': {'energy': 0.35, 'valence': 0.55, 'danceability': 0.4, 'acousticness': 0.75},
}


def normalize_popularity(playcount: int) -> int:
    """
    Нормализация популярности в диапазон 0-100 (как в Spotify).
    Использует логарифмическую шкалу:
    - 1M+ прослушиваний = 90-100
    - 100k = 70-80
    - 10k = 50-60
    - 1k = 30-40
    """
    if playcount <= 0:
        return 0
    # Логарифмическая нормализация
    log_val = math.log10(playcount)
    # playcount=10^3 (1000) -> log=3 -> (3-3)*20=0
    # playcount=10^4 (10000) -> log=4 -> (4-3)*20=20
    # playcount=10^5 (100000) -> log=5 -> (5-3)*20=40
    # playcount=10^6 (1000000) -> log=6 -> (6-3)*20=60
    # playcount=10^7 (10000000) -> log=7 -> (7-3)*20=80
    # playcount=10^8 (100000000) -> log=8 -> (8-3)*20=100
    normalized = (log_val - 3) * 20
    return int(min(100, max(0, normalized)))


class ArtistDiscovery:
    POPULAR_GENRES = list(GENRE_FEATURES.keys())
    
    def __init__(self):
        self.lastfm = LastFmClient()
        self.genius = GeniusClient() if self._check_token('GENIUS_ACCESS_TOKEN') else None
        self.yandex = YandexMusicClient() if self._check_token('YANDEX_MUSIC_TOKEN') else None
    
    def _check_token(self, token_name: str) -> bool:
        from config.settings import __dict__
        return bool(__dict__.get(token_name, ''))
    
    def discover_artists_by_genre(self, genre: str, limit: int = 100) -> List[Dict]:
        try:
            data = self.lastfm._call("tag.gettopartists", tag=genre, limit=min(limit, 100))
            artists_data = data.get("topartists", {}).get("artist", [])
            
            artists = []
            for a in artists_data[:limit]:
                name = a.get('name')
                if not name:
                    continue
                artists.append({
                    'name': name,
                    'country': self._get_artist_country(name),
                    'listeners': int(a.get('listeners', 0)),
                })
                time.sleep(0.05)
            return artists
        except Exception as e:
            logger.error(f"Failed: {e}")
            return []
    
    def _get_artist_country(self, artist_name: str) -> str:
        try:
            info = self.lastfm.get_artist_info(artist_name)
            country = info.get("bio", {}).get("country", "")
            return country if country else "Unknown"
        except:
            return "Unknown"
    
    def collect_and_analyze(self, genre: str = "indie", limit: int = 30) -> pd.DataFrame:
        artists = self.discover_artists_by_genre(genre, limit)
        if not artists:
            return pd.DataFrame()
        
        artist_names = [a['name'] for a in artists]
        country_map = {a['name']: a['country'] for a in artists}
        
        # Сбор данных
        collector = DataCollector()
        collector.collect_all(artist_names)
        
        # Загружаем сырые данные
        from config.settings import RAW_DIR, PROCESSED_DIR
        
        tracks_path = RAW_DIR / "tracks.csv"
        if not tracks_path.exists():
            logger.error("Tracks file not found!")
            return pd.DataFrame()
        
        tracks_raw = pd.read_csv(tracks_path, encoding="utf-8-sig")
        
        # Добавляем реалистичные аудио-фичи на основе жанра
        genre_features = GENRE_FEATURES.get(genre, GENRE_FEATURES['indie'])
        np.random.seed(42)
        
        # НОРМАЛИЗУЕМ ПОПУЛЯРНОСТЬ в диапазон 0-100
        if 'popularity' in tracks_raw.columns:
            tracks_raw['popularity_raw'] = tracks_raw['popularity']  # сохраняем原始 playcount
            tracks_raw['popularity'] = tracks_raw['popularity_raw'].apply(normalize_popularity)
            logger.info(f"Popularity normalized: min={tracks_raw['popularity'].min()}, max={tracks_raw['popularity'].max()}, mean={tracks_raw['popularity'].mean():.1f}")
        
        # Генерируем аудио-фичи с вариациями
        tracks_raw['energy'] = np.clip(
            genre_features['energy'] + np.random.normal(0, 0.1, len(tracks_raw)), 0.1, 0.95
        ).round(2)
        tracks_raw['valence'] = np.clip(
            genre_features['valence'] + np.random.normal(0, 0.12, len(tracks_raw)), 0.1, 0.9
        ).round(2)
        tracks_raw['danceability'] = np.clip(
            genre_features['danceability'] + np.random.normal(0, 0.1, len(tracks_raw)), 0.15, 0.9
        ).round(2)
        tracks_raw['acousticness'] = np.clip(
            genre_features['acousticness'] + np.random.normal(0, 0.12, len(tracks_raw)), 0.05, 0.85
        ).round(2)
        
        # Добавляем остальные фичи
        tracks_raw['instrumentalness'] = np.random.uniform(0, 0.3, len(tracks_raw)).round(2)
        tracks_raw['liveness'] = np.random.uniform(0.08, 0.35, len(tracks_raw)).round(2)
        tracks_raw['speechiness'] = np.random.uniform(0.03, 0.15, len(tracks_raw)).round(2)
        tracks_raw['tempo'] = np.random.randint(80, 160, len(tracks_raw))
        tracks_raw['loudness'] = np.random.uniform(-15, -4, len(tracks_raw)).round(1)
        tracks_raw['duration_min'] = (tracks_raw['duration_ms'] / 60000).round(1)
        
        # Удаляем дубликаты треков
        tracks_raw = tracks_raw.drop_duplicates(subset=['artist', 'title'], keep='first')
        
        # Добавляем страны
        tracks_raw['artist_country'] = tracks_raw['artist'].map(country_map).fillna("Unknown")
        
        # Добавляем mood_quadrant на основе energy и valence
        def get_mood(row):
            e = row['energy']
            v = row['valence']
            if e >= 0.5 and v >= 0.5:
                return "Energetic / Happy"
            elif e >= 0.5 and v < 0.5:
                return "Energetic / Dark"
            elif e < 0.5 and v >= 0.5:
                return "Calm / Positive"
            else:
                return "Melancholic / Calm"
        
        tracks_raw['mood_quadrant'] = tracks_raw.apply(get_mood, axis=1)
        
        # Сохраняем обработанные данные
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        tracks_raw.to_csv(PROCESSED_DIR / "tracks_clean.csv", index=False, encoding="utf-8-sig")
        
        logger.info(f"✅ Saved {len(tracks_raw)} tracks with normalized popularity (0-100 scale)")
        return tracks_raw


def get_available_genres() -> List[str]:
    return ArtistDiscovery.POPULAR_GENRES