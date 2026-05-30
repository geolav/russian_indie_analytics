"""
main.py
-------
CLI entry point for the data collection and processing pipeline.

Usage:
    python main.py --mode demo          # Generate demo data and run full pipeline
    python main.py --mode collect       # Collect real data via APIs (requires .env)
    python main.py --mode process       # Re-process already collected raw data
    python main.py --mode all           # Collect → process → export screenshots
"""

import argparse
import sys
from pathlib import Path

# Ensure the project root is importable from anywhere
sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils.logger import get_logger
from config.settings import RAW_DIR, PROCESSED_DIR, SPOTIFY_CLIENT_ID

logger = get_logger("main")


def run_demo() -> None:
    """Generate realistic synthetic data and run the full processing pipeline."""
    logger.info("=== Running DEMO pipeline ===")
    from services.demo_data import save_demo_data
    tracks_path, artists_path = save_demo_data()
    logger.info("Demo data saved: %s, %s", tracks_path, artists_path)
    _run_process()


def run_collect() -> None:
    """Collect real data from Spotify + Last.fm + Genius APIs."""
    if not SPOTIFY_CLIENT_ID:
        logger.error("SPOTIFY_CLIENT_ID is not set. Add it to your .env file.")
        sys.exit(1)
    logger.info("=== Running COLLECT pipeline ===")
    from services.collector import DataCollector
    collector = DataCollector()
    collector.collect_all()
    _run_process()


def _run_process() -> None:
    """Load raw CSVs, clean them, and save processed versions."""
    logger.info("=== Processing raw data ===")
    import pandas as pd
    from services.preprocessor import DataPreprocessor

    tracks_csv = RAW_DIR / "tracks.csv"
    artists_csv = RAW_DIR / "artists.csv"

    if not tracks_csv.exists():
        logger.error("tracks.csv not found at %s. Run --mode demo or --mode collect first.", RAW_DIR)
        sys.exit(1)

    tracks_raw = pd.read_csv(tracks_csv, encoding="utf-8-sig")
    artists_raw = pd.read_csv(artists_csv, encoding="utf-8-sig") if artists_csv.exists() else pd.DataFrame()

    pre = DataPreprocessor(tracks_raw, artists_raw)
    tracks_clean = pre.process_tracks()
    artists_clean = pre.process_artists() if not artists_raw.empty else None

    logger.info("Processing complete. %d clean tracks.", len(tracks_clean))
    _run_analytics(tracks_clean)


def _run_analytics(df) -> None:
    """Run clustering + export overview screenshot."""
    logger.info("=== Running analytics ===")
    from analytics import cluster_tracks, pca_projection
    from visualization.static_charts import save_overview_grid
    from services.preprocessor import load_processed_artists

    df = cluster_tracks(df)
    df = pca_projection(df)

    out = save_overview_grid(df)
    logger.info("Overview screenshot saved → %s", out)
    logger.info("=== Pipeline complete ===")
    logger.info("Launch dashboard:  streamlit run dashboard/app.py")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Russian Indie Music Analytics — pipeline runner"
    )
    parser.add_argument(
        "--mode",
        choices=["demo", "collect", "process", "all"],
        default="demo",
        help="Pipeline mode (default: demo)",
    )
    args = parser.parse_args()

    if args.mode == "demo":
        run_demo()
    elif args.mode == "collect":
        run_collect()
    elif args.mode == "process":
        _run_process()
    elif args.mode == "all":
        if SPOTIFY_CLIENT_ID:
            run_collect()
        else:
            logger.warning("No API keys found, falling back to demo mode.")
            run_demo()


if __name__ == "__main__":
    main()
