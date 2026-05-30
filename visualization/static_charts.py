"""
visualization/static_charts.py
--------------------------------
High-quality static charts saved to PNG for README screenshots
and offline reports.  Uses matplotlib + seaborn.
"""

from __future__ import annotations
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
import numpy as np
import pandas as pd

from config.settings import AUDIO_FEATURES, COLOR_PALETTE
from visualization.style import apply_style, DARK_BG, CARD_BG, TEXT_COLOR, ACCENT

SCREENSHOTS_DIR = Path(__file__).parent.parent / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)


def save_overview_grid(df: pd.DataFrame, path: Path | None = None) -> Path:
    """
    Save a 2×3 overview grid with key distributions.
    Returns the file path.
    """
    apply_style()
    out = path or SCREENSHOTS_DIR / "overview_grid.png"

    fig = plt.figure(figsize=(18, 12), facecolor=DARK_BG)
    fig.suptitle("Russian Indie Music — Analytics Overview", fontsize=22,
                 color=TEXT_COLOR, fontweight="bold", y=1.01)

    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.45, wspace=0.35)

    # 1. Popularity histogram
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_facecolor(CARD_BG)
    if "popularity" in df.columns:
        ax1.hist(df["popularity"].dropna(), bins=30, color=ACCENT, edgecolor="none", alpha=0.85)
        ax1.set_title("Popularity Distribution", color=TEXT_COLOR)
        ax1.set_xlabel("Popularity Score", color=TEXT_COLOR)

    # 2. Energy vs Valence scatter
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_facecolor(CARD_BG)
    if {"energy", "valence"}.issubset(df.columns):
        scatter = ax2.scatter(
            df["valence"], df["energy"],
            c=df["popularity"] if "popularity" in df.columns else ACCENT,
            cmap="RdYlBu_r", alpha=0.6, s=20, linewidths=0,
        )
        ax2.axhline(0.5, ls="--", color="white", alpha=0.2)
        ax2.axvline(0.5, ls="--", color="white", alpha=0.2)
        ax2.set_title("Mood Map (Energy × Valence)", color=TEXT_COLOR)
        ax2.set_xlabel("Valence →", color=TEXT_COLOR)
        ax2.set_ylabel("Energy →", color=TEXT_COLOR)
        plt.colorbar(scatter, ax=ax2, label="Popularity")

    # 3. Top artists
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.set_facecolor(CARD_BG)
    if "artist" in df.columns and "popularity" in df.columns:
        top = df.groupby("artist")["popularity"].mean().nlargest(10)
        colors_bar = [COLOR_PALETTE[i % len(COLOR_PALETTE)] for i in range(len(top))]
        bars = ax3.barh(top.index[::-1], top.values[::-1], color=colors_bar[::-1])
        ax3.set_title("Top Artists by Popularity", color=TEXT_COLOR)
        ax3.set_xlabel("Mean Popularity", color=TEXT_COLOR)

    # 4. Audio feature violin
    ax4 = fig.add_subplot(gs[1, :2])
    ax4.set_facecolor(CARD_BG)
    feat_cols = [c for c in ["danceability", "energy", "valence", "acousticness"] if c in df.columns]
    if feat_cols:
        data_for_violin = [df[c].dropna().values for c in feat_cols]
        parts = ax4.violinplot(data_for_violin, positions=range(len(feat_cols)),
                               showmedians=True, showextrema=False)
        for pc, color in zip(parts["bodies"], COLOR_PALETTE):
            pc.set_facecolor(color)
            pc.set_alpha(0.75)
        parts["cmedians"].set_colors("white")
        ax4.set_xticks(range(len(feat_cols)))
        ax4.set_xticklabels([c.capitalize() for c in feat_cols], color=TEXT_COLOR)
        ax4.set_title("Audio Feature Distributions", color=TEXT_COLOR)

    # 5. Correlation heatmap
    ax5 = fig.add_subplot(gs[1, 2])
    ax5.set_facecolor(CARD_BG)
    feat_for_corr = [c for c in AUDIO_FEATURES if c in df.columns]
    if len(feat_for_corr) >= 3:
        corr = df[feat_for_corr].corr()
        mask = np.zeros_like(corr, dtype=bool)
        mask[np.triu_indices_from(mask)] = True
        sns.heatmap(
            corr, mask=mask, ax=ax5, cmap="RdBu_r",
            vmin=-1, vmax=1, linewidths=0.3,
            annot=True, fmt=".1f", annot_kws={"size": 7},
            cbar_kws={"shrink": 0.8},
        )
        ax5.set_title("Feature Correlations", color=TEXT_COLOR)
        ax5.tick_params(axis="x", rotation=45, labelcolor=TEXT_COLOR)
        ax5.tick_params(axis="y", labelcolor=TEXT_COLOR)

    plt.savefig(out, dpi=120, bbox_inches="tight", facecolor=DARK_BG)
    plt.close(fig)
    return out
