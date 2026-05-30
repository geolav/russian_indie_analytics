"""
visualization/style.py
-----------------------
Shared matplotlib / seaborn / plotly styling utilities.
All chart-creating modules import from here to ensure visual consistency.
"""

from __future__ import annotations
import matplotlib.pyplot as plt
import matplotlib as mpl
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px

from config.settings import COLOR_PALETTE, FIGURE_DPI

# ── Matplotlib global style ────────────────────────────────────────────────────

DARK_BG = "#0D1117"
CARD_BG = "#161B22"
TEXT_COLOR = "#E6EDF3"
GRID_COLOR = "#21262D"
ACCENT = "#E63946"

MPL_PARAMS: dict = {
    "figure.facecolor":    DARK_BG,
    "axes.facecolor":      CARD_BG,
    "axes.edgecolor":      GRID_COLOR,
    "axes.labelcolor":     TEXT_COLOR,
    "axes.titlecolor":     TEXT_COLOR,
    "axes.titlesize":      14,
    "axes.labelsize":      11,
    "xtick.color":         TEXT_COLOR,
    "ytick.color":         TEXT_COLOR,
    "text.color":          TEXT_COLOR,
    "grid.color":          GRID_COLOR,
    "grid.linestyle":      "--",
    "grid.alpha":          0.5,
    "figure.dpi":          FIGURE_DPI,
    "savefig.facecolor":   DARK_BG,
    "savefig.bbox":        "tight",
    "font.family":         "DejaVu Sans",
}


def apply_style() -> None:
    """Apply dark-themed matplotlib rcParams globally."""
    mpl.rcParams.update(MPL_PARAMS)
    sns.set_palette(COLOR_PALETTE)


def fig_and_ax(figsize=(12, 6), **kwargs):
    """Convenience wrapper: apply_style then return (fig, ax)."""
    apply_style()
    fig, ax = plt.subplots(figsize=figsize, **kwargs)
    ax.grid(True, alpha=0.3)
    return fig, ax


# ── Plotly template ────────────────────────────────────────────────────────────

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(22,27,34,1)",
    font=dict(color=TEXT_COLOR, family="Inter, system-ui, sans-serif", size=12),
    xaxis=dict(gridcolor=GRID_COLOR, showline=True, linecolor=GRID_COLOR),
    yaxis=dict(gridcolor=GRID_COLOR, showline=True, linecolor=GRID_COLOR),
    hoverlabel=dict(bgcolor=CARD_BG, font_color=TEXT_COLOR),
    colorway=COLOR_PALETTE,
    margin=dict(l=50, r=30, t=60, b=50),
)


def plotly_fig(fig: go.Figure, title: str = "") -> go.Figure:
    """Apply the shared Plotly layout to *fig*."""
    fig.update_layout(title=dict(text=title, font=dict(size=18)), **PLOTLY_LAYOUT)
    return fig
