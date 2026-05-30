"""
data/models.py
--------------
Pydantic-free dataclass models that act as typed contracts between
the collection, analytics, and visualization layers.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ArtistRecord:
    """Represents a single artist's consolidated metadata."""

    spotify_id: str
    name: str
    genres: list[str] = field(default_factory=list)
    popularity: int = 0                  # Spotify 0-100
    followers: int = 0
    lastfm_listeners: int = 0
    lastfm_playcount: int = 0
    lastfm_tags: list[str] = field(default_factory=list)
    related_artists: list[str] = field(default_factory=list)
    image_url: str = ""


@dataclass
class TrackRecord:
    """Represents a single track with all collected features."""

    track_id: str
    title: str
    artist: str
    artist_id: str
    album: str = ""
    release_date: str = ""
    release_year: Optional[int] = None
    popularity: int = 0                  # Spotify 0-100
    duration_ms: int = 0
    duration_min: float = 0.0
    explicit: bool = False
    preview_url: str = ""
    spotify_url: str = ""

    # Audio features
    danceability: float = 0.0
    energy: float = 0.0
    valence: float = 0.0
    acousticness: float = 0.0
    instrumentalness: float = 0.0
    liveness: float = 0.0
    speechiness: float = 0.0
    tempo: float = 0.0
    loudness: float = 0.0
    key: int = 0
    mode: int = 0                        # 1=major, 0=minor
    time_signature: int = 4

    # Supplementary
    lyrics_snippet: str = ""
    genius_pageviews: int = 0
    mood_cluster: Optional[int] = None
    sentiment_score: Optional[float] = None
