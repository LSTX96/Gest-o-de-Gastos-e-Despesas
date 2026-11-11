"""Gráficos travados: mostram os dados, sem zoom, arraste ou cliques que alterem a visualização."""
import plotly.graph_objects as go

BOTOES_REMOVIDOS = [
    "zoom2d", "pan2d", "select2d", "lasso2d", "zoomIn2d", "zoomOut2d",
    "autoScale2d", "resetScale2d", "toImage", "hoverClosestCartesian",
    "hoverCompareCartesian", "toggleSpikelines", "hoverClosestPie",
]


def travar(fig: go.Figure) -> go.Figure:
    """Deixa o gráfico só de leitura. O cursor continua mostrando os valores."""
    fig.update_layout(
        dragmode=False,
        modebar=dict(
            remove=BOTOES_REMOVIDOS,
            bgcolor="rgba(0,0,0,0)",
            color="rgba(0,0,0,0)",
            activecolor="rgba(0,0,0,0)",
        ),
        legend=dict(itemclick=False, itemdoubleclick=False),
    )
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig