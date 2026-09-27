"""Génération de graphiques 'propres', style académique (mémoire/thèse) :
titre, N, source, axes légendés, palette sobre."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import io

sns.set_theme(style="whitegrid", font_scale=1.0)
PALETTE = "Blues_d"
COLOR_MAIN = "#2563EB"


def _finalize(fig, title, source_note, xlabel=None, ylabel=None, ax=None):
    if ax is not None:
        if xlabel:
            ax.set_xlabel(xlabel, fontsize=11)
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=11)
    fig.suptitle(title, fontsize=13, fontweight="bold", y=1.02)
    if source_note:
        fig.text(0.01, -0.04, source_note, ha="left", fontsize=8, style="italic", color="#555")
    fig.tight_layout()
    return fig


def bar_chart(freq_df, cat_col="Modalité", val_col="Effectif", title="Répartition", source_note=""):
    fig, ax = plt.subplots(figsize=(6, 4))
    sns.barplot(data=freq_df, x=cat_col, y=val_col, color=COLOR_MAIN, ax=ax)
    for i, v in enumerate(freq_df[val_col]):
        ax.text(i, v, str(v), ha="center", va="bottom", fontsize=9)
    plt.xticks(rotation=25, ha="right")
    return _finalize(fig, title, source_note, xlabel="", ylabel="Effectif", ax=ax)


def pie_chart(freq_df, cat_col="Modalité", val_col="Effectif", title="Répartition", source_note=""):
    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    colors = sns.color_palette("Blues", len(freq_df))
    ax.pie(freq_df[val_col], labels=freq_df[cat_col], autopct="%1.1f%%",
           colors=colors, startangle=90, wedgeprops={"edgecolor": "white"})
    ax.axis("equal")
    return _finalize(fig, title, source_note)


def histogram(series, title="Distribution", xlabel="", source_note=""):
    fig, ax = plt.subplots(figsize=(6, 4))
    sns.histplot(series.dropna(), kde=True, color=COLOR_MAIN, ax=ax)
    return _finalize(fig, title, source_note, xlabel=xlabel, ylabel="Fréquence", ax=ax)


def boxplot_groups(numeric, group, title="Comparaison de groupes", xlabel="", ylabel="", source_note=""):
    fig, ax = plt.subplots(figsize=(6, 4))
    df = pd.DataFrame({"y": numeric, "g": group}).dropna()
    sns.boxplot(data=df, x="g", y="y", hue="g", palette="Blues", ax=ax, legend=False)
    sns.stripplot(data=df, x="g", y="y", color="black", alpha=0.3, size=3, ax=ax)
    return _finalize(fig, title, source_note, xlabel=xlabel, ylabel=ylabel, ax=ax)


def scatter_with_fit(x, y, title="Nuage de points", xlabel="", ylabel="", source_note=""):
    fig, ax = plt.subplots(figsize=(6, 4))
    df = pd.DataFrame({"x": x, "y": y}).dropna()
    sns.regplot(data=df, x="x", y="y", color=COLOR_MAIN,
                scatter_kws={"alpha": 0.6, "s": 25}, line_kws={"color": "#DC2626"}, ax=ax)
    return _finalize(fig, title, source_note, xlabel=xlabel, ylabel=ylabel, ax=ax)


def heatmap_corr(corr_df, title="Matrice de corrélation", source_note=""):
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(corr_df, annot=True, cmap="Blues", vmin=-1, vmax=1, fmt=".2f", ax=ax,
                cbar_kws={"label": "Coefficient"})
    return _finalize(fig, title, source_note, ax=ax)


def fig_to_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    buf.seek(0)
    return buf
