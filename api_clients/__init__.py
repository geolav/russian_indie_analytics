# Временно отключаем Spotify клиент, так как используем Yandex Music
# from .spotify_client import SpotifyClient
from .lastfm_client import LastFmClient
from .genius_client import GeniusClient
from .yandex_client import YandexMusicClient

# SpotifyClient временно недоступен
# __all__ = ["SpotifyClient", "LastFmClient", "GeniusClient", "YandexMusicClient"]
__all__ = ["LastFmClient", "GeniusClient", "YandexMusicClient"]