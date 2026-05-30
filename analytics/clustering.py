"""
analytics/clustering.py
-----------------------
KMeans clustering of tracks by audio features to discover
natural mood/sound groupings.  Also provides PCA for 2-D projection.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score

from config.settings import MOOD_CLUSTERS, RANDOM_STATE, AUDIO_FEATURES
from utils.logger import get_logger

logger = get_logger(__name__)

CLUSTER_LABELS = {
    0: "🌙 Melancholic",
    1: "⚡ High Energy",
    2: "☀️ Uplifting",
    3: "🎵 Acoustic / Mellow",
}


def _feature_matrix(df: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray, StandardScaler]:
    """
    Return (feature_df, scaled_matrix, scaler) for clustering.
    Only rows without NaN in audio features are kept.
    """
    cols = [c for c in AUDIO_FEATURES if c in df.columns]
    feature_df = df[cols].dropna()
    scaler = StandardScaler()
    X = scaler.fit_transform(feature_df)
    return feature_df, X, scaler


def cluster_tracks(df: pd.DataFrame, n_clusters: int = MOOD_CLUSTERS) -> pd.DataFrame:
    """
    Run KMeans clustering on audio features.

    Adds a 'mood_cluster' (int) and 'cluster_label' (str) column.
    Returns a copy of *df* with the new columns.
    """
    logger.info("Running KMeans clustering (k=%d) …", n_clusters)
    feature_df, X, _ = _feature_matrix(df)

    kmeans = KMeans(n_clusters=n_clusters, random_state=RANDOM_STATE, n_init=10)
    labels = kmeans.fit_predict(X)

    sil = silhouette_score(X, labels)
    logger.info("Silhouette score: %.3f", sil)

    df = df.copy()
    df.loc[feature_df.index, "mood_cluster"] = labels

    # Assign human labels based on cluster centroids
    scaler_mean = X.mean(axis=0)
    ordered = _order_clusters(kmeans.cluster_centers_)
    label_map = {old: CLUSTER_LABELS.get(new, f"Cluster {new}") for new, old in ordered.items()}
    df["cluster_label"] = df["mood_cluster"].map(label_map).fillna("Unknown")
    return df


def pca_projection(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a DataFrame with pca_x, pca_y columns for 2-D scatter plotting.
    Preserves original index alignment.
    """
    feature_df, X, _ = _feature_matrix(df)
    pca = PCA(n_components=2, random_state=RANDOM_STATE)
    components = pca.fit_transform(X)

    proj = pd.DataFrame(
        components,
        index=feature_df.index,
        columns=["pca_x", "pca_y"],
    )
    explained = pca.explained_variance_ratio_
    logger.info(
        "PCA variance explained: PC1=%.1f%%, PC2=%.1f%%",
        explained[0] * 100, explained[1] * 100,
    )
    return df.join(proj, how="left")


def elbow_analysis(df: pd.DataFrame, max_k: int = 10) -> pd.DataFrame:
    """
    Return inertia values for k=2..max_k.
    Useful for determining the optimal number of clusters.
    """
    _, X, _ = _feature_matrix(df)
    results = []
    for k in range(2, max_k + 1):
        km = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=10)
        km.fit(X)
        results.append({"k": k, "inertia": km.inertia_})
    return pd.DataFrame(results)


def _order_clusters(centers: np.ndarray) -> dict[int, int]:
    """
    Map raw cluster ids to semantic order by energy level.
    Returns {semantic_order: raw_cluster_id}.
    """
    # energy is typically index 1 in AUDIO_FEATURES
    energy_idx = AUDIO_FEATURES.index("energy") if "energy" in AUDIO_FEATURES else 1
    order = np.argsort(centers[:, energy_idx])  # ascending energy
    return {semantic: int(raw) for semantic, raw in enumerate(order)}
