import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import requests
from datetime import datetime
import pytz
import json

#pip install dash plotly requests pytz

# ================== Config ==================
IP_ADDRESS   = "54.196.116.14"
PORT_STH     = 8666
FIWARE_SVC   = "smart"
FIWARE_SSP   = "/"
ENTITY_ID    = "urn:ngsi-ld:device:001"  # dispositivo 001
ATTR         = "p"
lastN        = 20          # quantos pontos buscar a cada ciclo
MAX_POINTS   = 500         # janela deslizante (histórico máximo)
REFRESH_MS   = 5_000       # intervalo de atualização (ms)
DASH_HOST    = "127.0.0.1" # use "0.0.0.0" para expor na rede
DASH_PORT    = 8050

TZ_SP = pytz.timezone("America/Sao_Paulo")

# ================== Data fetch ==================
def get_attr_values(lastN: int):
    """Busca últimos N pontos do STH-Comet. Retorna lista de tuplas (iso_ts_UTC, float_val)."""
    url = (f"http://{IP_ADDRESS}:{PORT_STH}/STH/v1/contextEntities/"
           f"type/device/id/{ENTITY_ID}/attributes/{ATTR}?lastN={lastN}")
    headers = {"fiware-service": FIWARE_SVC, "fiware-servicepath": FIWARE_SSP}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        r.raise_for_status()
        data = r.json()
        values = data["contextResponses"][0]["contextElement"]["attributes"][0]["values"]

        out = []
        for e in values:
            # recvTime vem em ISO UTC: 'YYYY-MM-DDTHH:MM:SS(.fff)Z'
            ts_raw = e["recvTime"]
            ts_iso_utc = ts_raw.replace("Z", "+00:00")  # ISO com offset explícito
            try:
                v = float(e["attrValue"])
            except (ValueError, TypeError):
                continue
            out.append((ts_iso_utc, v))
        return out
    except Exception as exc:
        print(f"[WARN] Falha no fetch: {exc}")
        return []

# ================== App ==================
app = dash.Dash(__name__)

CARD_STYLE = {
    "padding": "12px 16px",
    "borderRadius": "12px",
    "boxShadow": "0 2px 10px rgba(0,0,0,0.06)",
    "background": "#ffffff",
    "border": "1px solid #e7e7e7",
    "minWidth": "180px"
}

app.layout = html.Div(
    [
        # Banner de alarme
        html.Div(
            id="alarm-banner",
            children="—",
            style={
                "textAlign": "center",
                "padding": "10px 16px",
                "fontWeight": "700",
                "color": "#fff",
                "borderRadius": "0 0 8px 8px",
                "marginBottom": "16px",
            },
        ),

        # Cabeçalho
        html.Div(
            [
                html.Div(
                    [
                        html.H2("Painel de Operação — Sensor", style={"margin": 0}),
                        html.Div("Monitoramento contínuo da máquina", style={"color": "#6b7280"}),
                    ],
                ),
                html.Div(
                    [
                        html.Label("Limite (threshold):"),
                        dcc.Input(
                            id="threshold",
                            type="number",
                            value=80,
                            step=1,
                            debounce=True,
                            style={"width": "120px", "marginLeft": "8px", "marginRight": "12px"}
                        ),
                        html.Span(
                            id="status-badge",
                            children="—",
                            style={
                                "padding": "6px 10px",
                                "borderRadius": "999px",
                                "fontWeight": "700",
                                "color": "#fff",
                                "display": "inline-block",
                                "minWidth": "160px",
                                "textAlign": "center"
                            }
                        ),
                    ],
                    style={"display": "flex", "alignItems": "center", "gap": "8px"}
                ),
            ],
            style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "12px"}
        ),

        # KPIs
        html.Div(
            [
                html.Div(
                    [html.Div("Último valor do sensor", style={"color": "#6b7280", "fontSize": "12px"}),
                     html.Div(id="kpi-last", style={"fontSize": "22px", "fontWeight": "700"})],
                    style=CARD_STYLE
                ),
                html.Div(
                    [html.Div("Limite configurado", style={"color": "#6b7280", "fontSize": "12px"}),
                     html.Div(id="kpi-thr", style={"fontSize": "22px", "fontWeight": "700"})],
                    style=CARD_STYLE
                ),
                html.Div(
                    [html.Div("Última atualização (São Paulo)", style={"color": "#6b7280", "fontSize": "12px"}),
                     html.Div(id="kpi-ts", style={"fontSize": "22px", "fontWeight": "700"})],
                    style=CARD_STYLE
                ),
            ],
            style={"display": "flex", "gap": "12px", "flexWrap": "wrap", "marginBottom": "10px"}
        ),

        # Gráfico
        html.Div(
            dcc.Graph(id="fig"),
            style={"background": "#fff", "border": "1px solid #e7e7e7", "borderRadius": "12px",
                   "boxShadow": "0 2px 10px rgba(0,0,0,0.06)"}
        ),

        # Store e timer
        dcc.Store(id="store", data={"ts": [], "y": []}),
        dcc.Interval(id="tick", interval=REFRESH_MS, n_intervals=0),
    ],
    style={"maxWidth": 1000, "margin": "0 auto", "fontFamily": "system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
           "padding": "8px 12px", "background": "#f6f7fb"}
)

# ================== Callbacks ==================
@app.callback(
    Output("store", "data"),
    Input("tick", "n_intervals"),
    State("store", "data"),
)
def on_tick(_, store):
    batch = get_attr_values(lastN)
    if not batch:
        return store

    # de-dup por timestamp
    seen = set(store["ts"])
    for ts_iso_utc, val in batch:
        if ts_iso_utc not in seen:
            store["ts"].append(ts_iso_utc)
            store["y"].append(val)
            seen.add(ts_iso_utc)

    # ordena por tempo (ISO com offset ordena corretamente)
    paired = list(zip(store["ts"], store["y"]))
    paired.sort(key=lambda p: p[0])

    # janela deslizante
    if len(paired) > MAX_POINTS:
        paired = paired[-MAX_POINTS:]

    ts_sorted, y_sorted = zip(*paired) if paired else ([], [])
    return {"ts": list(ts_sorted), "y": list(y_sorted)}

@app.callback(
    Output("fig", "figure"),
    Input("store", "data"),
    Input("threshold", "value"),
)
def draw_figure(store, threshold):
    ts_utc = store["ts"]
    y      = store["y"]
    fig = go.Figure()

    # Converte eixo X para horário de São Paulo
    x_sp = []
    for s in ts_utc:
        try:
            dt_utc = datetime.fromisoformat(s)  # timezone-aware por causa do +00:00
            x_sp.append(dt_utc.astimezone(TZ_SP))
        except Exception:
            x_sp.append(s)  # fallback

    if x_sp and y:
        fig.add_trace(go.Scatter(
            x=x_sp,
            y=y,
            mode="lines",
            name="Sensor",
            line=dict(width=1.8),
        ))

    # Linha limite (threshold)
    if threshold is not None:
        fig.add_hline(
            y=float(threshold),
            line_width=2,
            line_dash="dash",
            annotation_text=f"Limite = {threshold}",
            annotation_position="top left"
        )

    fig.update_layout(
        title="Leituras do sensor (tempo real)",
        xaxis_title="Tempo (São Paulo)",
        yaxis_title="Valor",
        template="plotly_white",
        margin=dict(l=40, r=30, t=40, b=40),
        hovermode="x unified",
        uirevision="fixed",
        font=dict(size=12),
    )
    fig.update_xaxes(
        rangeslider=dict(visible=True),
        showspikes=True,
        spikemode="across",
        spikesnap="cursor",
    )
    fig.update_yaxes(showspikes=True)
    return fig

@app.callback(
    Output("status-badge", "children"),
    Output("status-badge", "style"),
    Output("alarm-banner", "children"),
    Output("alarm-banner", "style"),
    Output("kpi-last", "children"),
    Output("kpi-thr", "children"),
    Output("kpi-ts", "children"),
    Input("store", "data"),
    Input("threshold", "value"),
)
def compute_status(store, threshold):
    base_badge = {
        "padding": "6px 10px",
        "borderRadius": "999px",
        "fontWeight": "700",
        "color": "#fff",
        "display": "inline-block",
        "minWidth": "160px",
        "textAlign": "center"
    }
    base_banner = {
        "textAlign": "center",
        "padding": "10px 16px",
        "fontWeight": "700",
        "color": "#fff",
        "borderRadius": "0 0 8px 8px",
        "marginBottom": "16px",
    }

    ts_list = store.get("ts", [])
    y_list  = store.get("y", [])
    thr     = float(threshold) if threshold is not None else None

    if not ts_list or not y_list or thr is None:
        badge_text = "Aguardando dados"
        badge_style = {**base_badge, "background": "#9CA3AF"}
        banner_text = "Aguardando dados do sensor"
        banner_style = {**base_banner, "background": "#9CA3AF"}
        return badge_text, badge_style, banner_text, banner_style, "—", str(thr) if thr else "—", "—"

    last_val = y_list[-1]
    last_ts_iso_utc = ts_list[-1]

    # Converte timestamp UTC -> America/Sao_Paulo para exibir no KPI
    try:
        dt_utc = datetime.fromisoformat(last_ts_iso_utc)
        dt_sp  = dt_utc.astimezone(TZ_SP)
        last_ts_fmt = dt_sp.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        last_ts_fmt = last_ts_iso_utc

    # Lógica de alarme
    if last_val > thr:
        # ERRO
        badge_text = "Erro de Operação"
        badge_style = {**base_badge, "background": "#DC2626"}  # vermelho
        banner_text = "⚠️ Erro de Operação — valor do sensor acima do limite"
        banner_style = {**base_banner, "background": "#DC2626"}
    else:
        # OK
        badge_text = "Sistema OK"
        badge_style = {**base_badge, "background": "#16A34A"}  # verde
        banner_text = "✅ Sistema OK — valor do sensor dentro do limite"
        banner_style = {**base_banner, "background": "#16A34A"}

    # KPIs
    kpi_last = f"{last_val:.2f}"
    kpi_thr  = f"{thr:.2f}"
    kpi_ts   = last_ts_fmt

    return badge_text, badge_style, banner_text, banner_style, kpi_last, kpi_thr, kpi_ts

# ================== Main ==================
if __name__ == "__main__":
    app.run(debug=True, host=DASH_HOST, port=DASH_PORT)
