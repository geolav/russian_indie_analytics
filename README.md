# 🎸 Russian Indie Music Analytics

> A production-grade data analytics project exploring the sounds, moods, and trends of Russian indie music — built with Python, Spotify API, Last.fm, and Streamlit.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.29+-red?logo=streamlit)
![Plotly](https://img.shields.io/badge/Plotly-5.18+-purple?logo=plotly)

[//]: # (![License]&#40;https://img.shields.io/badge/License-MIT-green&#41;)

---

## 📸 Screenshots

| Overview Dashboard | Mood Map |
|---|---|
| ![Overview](screenshots/overview_grid.png) | Scatter: Energy × Valence |

| Artist Radar | Network Graph |
|---|---|
| Radar chart comparing artists | Artist similarity network |

---

## 🎯 What This Project Does

- **Collects** data from Spotify (audio features, popularity), Last.fm (listeners, tags), and Genius (lyrics snippets) for ~30 Russian indie artists
- **Processes** it with a full cleaning + feature-engineering pipeline
- **Analyses** distributions, correlations, temporal trends, mood clustering, and sentiment
- **Visualises** everything in a multi-tab interactive Streamlit dashboard with 10+ chart types
- **Works offline** with a built-in demo data generator when no API keys are available

---

## 🗂️ Project Structure

```
russian_indie_analytics/
├── api_clients/            # Spotify, Last.fm, Genius API wrappers
│   ├── spotify_client.py
│   ├── lastfm_client.py
│   └── genius_client.py
├── data/
│   ├── models.py           # TrackRecord / ArtistRecord dataclasses
│   ├── raw/                # Raw API output CSVs (git-ignored)
│   ├── processed/          # Cleaned DataFrames (git-ignored)
│   └── cache/              # JSON request cache (git-ignored)
├── services/
│   ├── collector.py        # Data collection orchestrator
│   ├── preprocessor.py     # Cleaning + feature engineering
│   └── demo_data.py        # Synthetic data generator
├── analytics/
│   ├── eda.py              # EDA functions (pure DataFrame transformations)
│   └── clustering.py       # KMeans + PCA track clustering
├── visualization/
│   ├── style.py            # Shared dark theme (matplotlib + plotly)
│   ├── charts.py           # All Plotly chart factories
│   ├── network.py          # NetworkX + Plotly artist network
│   └── static_charts.py    # Matplotlib/Seaborn PNG export
├── dashboard/
│   └── app.py              # Streamlit multi-tab dashboard
├── config/
│   └── settings.py         # Centralised config + env loading
├── utils/
│   ├── logger.py           # Logging factory
│   ├── cache.py            # File-based TTL cache
│   └── helpers.py          # retry(), clean_text(), etc.
├── screenshots/            # Auto-generated PNG outputs
├── main.py                 # CLI pipeline runner
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/yourusername/russian-indie-analytics
cd russian-indie-analytics
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure API Keys (optional)

```bash
cp .env.example .env
# Edit .env with your Spotify / Last.fm / Genius credentials
```

> **No API keys?** No problem — the project ships with a realistic synthetic data generator.

### 3. Run the Pipeline

```bash
# Demo mode (no API keys needed)
python main.py --mode demo

# Real data collection (requires API keys in .env)
python main.py --mode collect
```

### 4. Launch the Dashboard

```bash
streamlit run dashboard/app.py
```

Open [http://localhost:8501](http://localhost:8501) 🎉

---

## 📊 Analytics Features

### Exploratory Data Analysis
- Top artists by popularity & follower count
- Genre frequency distribution
- Audio feature distributions (violin plots, histograms)
- Popularity trends over time

### Audio Feature Analysis
- Pearson correlation heatmap
- Per-artist feature comparison heatmap
- Box plots per artist for any feature

### Mood Analysis
- Energy × Valence scatter (mood map)
- KMeans clustering into 4 mood archetypes
- PCA 2-D cluster projection
- Mood quadrant distribution donut chart

### Temporal Trends
- Multi-feature trend lines by release year
- Decade breakdown statistics

### Artist Comparison
- Radar / spider chart for up to 6 artists
- Side-by-side mean feature table
- Sentiment score comparison

### Network Analysis
- Artist similarity network (Spotify related-artists)
- Node size = connections; hover tooltips

### Tracks Explorer
- Full filterable + sortable table
- Search by title / artist
- Visual progress bars for key metrics

---

## 🛠️ Tech Stack

| Layer | Libraries |
|---|---|
| Data Collection | `requests`, `python-dotenv` |
| Data Processing | `pandas`, `numpy` |
| Machine Learning | `scikit-learn` (KMeans, PCA, StandardScaler) |
| Visualisation | `plotly`, `matplotlib`, `seaborn` |
| Network Analysis | `networkx` |
| Dashboard | `streamlit` |
| NLP | `nltk`, `textblob` |

---

## 🔑 API Setup Guide

### Spotify
1. Go to [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)
2. Create a new app → copy **Client ID** and **Client Secret**

### Last.fm
1. Go to [last.fm/api/account/create](https://www.last.fm/api/account/create)
2. Copy your **API key**

### Genius
1. Go to [genius.com/api-clients](https://genius.com/api-clients)
2. Create a client → copy **Client Access Token**

---

## 🎤 Tracked Artists

The seed list includes ~30 artists spanning Russian indie subgenres:

| Genre | Artists |
|---|---|
| Post-Punk / Darkwave | Shortparis, Молчат Дома, IC3PEAK, Motorama |
| Indie Pop | Монеточка, Лауд, Дора, Антоха МС |
| Indie Rock | Земфира, Нервы, Порнофильмы, Сансара |
| Electropop / Synth | Tesla Boy, Therr Maitz, Pompeya, Kate NV |
| Experimental | Аигел, Kedr Livanskiy, Flёur |

---

## 🧪 Running Tests

```bash
pytest tests/ -v --cov=. --cov-report=term-missing
```

---

## 📄 License

MIT — see [LICENSE](LICENSE)

---

## 🙏 Acknowledgements

- [Spotify Web API](https://developer.spotify.com/documentation/web-api)
- [Last.fm API](https://www.last.fm/api)
- [Genius API](https://docs.genius.com)
- Built with ❤️ for Russian indie music
