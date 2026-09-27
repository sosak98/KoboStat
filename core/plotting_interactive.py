"""Graphiques interactifs (Plotly) pour le dashboard web, avec export en image
statique (PNG) pour les rapports Word/PDF."""
import plotly.express as px
import plotly.graph_objects as go

TEMPLATE = "plotly_white"
COLOR_MAIN = "#2563EB"


def _finalize(fig, title, source_note=""):
    fig.update_layout(
        template=TEMPLATE,
        title={"text": f"<b>{title}</b>", "x": 0.02},
        margin=dict(l=40, r=20, t=60, b=60),
        font=dict(size=13),
    )
    if source_note:
        fig.add_annotation(
            text=source_note, xref="paper", yref="paper", x=0, y=-0.18,
            showarrow=False, font=dict(size=10, color="#666"), align="left",
        )
    return fig


def bar_chart(freq_df, cat_col="Modalité", val_col="Effectif", title="Répartition", source_note=""):
    fig = px.bar(freq_df, x=cat_col, y=val_col, text=val_col, color_discrete_sequence=[COLOR_MAIN])
    fig.update_traces(textposition="outside")
    return _finalize(fig, title, source_note)


def pie_chart(freq_df, cat_col="Modalité", val_col="Effectif", title="Répartition", source_note=""):
    fig = px.pie(freq_df, names=cat_col, values=val_col, color_discrete_sequence=px.colors.sequential.Blues_r)
    return _finalize(fig, title, source_note)


def histogram(series, title="Distribution", xlabel="", source_note=""):
    fig = px.histogram(series.dropna(), nbins=15, color_discrete_sequence=[COLOR_MAIN])
    fig.update_layout(xaxis_title=xlabel, yaxis_title="Fréquence", showlegend=False)
    return _finalize(fig, title, source_note)


def boxplot_groups(df, num_col, group_col, title="Comparaison de groupes", source_note=""):
    fig = px.box(df, x=group_col, y=num_col, points="all", color=group_col,
                 color_discrete_sequence=px.colors.sequential.Blues_r)
    fig.update_layout(showlegend=False)
    return _finalize(fig, title, source_note)


def scatter_with_fit(df, x_col, y_col, title="Nuage de points", source_note=""):
    fig = px.scatter(df, x=x_col, y=y_col, trendline="ols", color_discrete_sequence=[COLOR_MAIN])
    return _finalize(fig, title, source_note)


def heatmap_corr(corr_df, title="Matrice de corrélation", source_note=""):
    fig = go.Figure(data=go.Heatmap(
        z=corr_df.values, x=list(corr_df.columns), y=list(corr_df.index),
        colorscale="Blues", zmin=-1, zmax=1, text=corr_df.round(2).values,
        texttemplate="%{text}",
    ))
    return _finalize(fig, title, source_note)


def crosstab_bar(long_df, x_col, hue_col, y_col="Effectif", title="", source_note=""):
    fig = px.bar(long_df, x=x_col, y=y_col, color=hue_col, barmode="group",
                 color_discrete_sequence=px.colors.qualitative.Set2)
    return _finalize(fig, title, source_note)


def fig_to_html_div(fig) -> str:
    """Pour l'intégrer directement dans un template Django (interactif)."""
    return fig.to_html(full_html=False, include_plotlyjs=False, config={"displaylogo": False})
