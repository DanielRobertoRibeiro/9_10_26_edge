import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import requests
from datetime import datetime
import json

# pip install dash plotly requests

# ================== Config ==================
IP_ADDRESS   = "54.196.116.14"
PORT_STH     = 8666
FIWARE_SVC   = "smart"
FIWARE_SSP   = "/"
ENTITY_ID    = "urn:ngsi-ld:device:001"
ATTR         = "p"
lastN        = 20          # quantos pontos buscar a cada ciclo
MAX_POINTS   = 500         # janela deslizante (histórico máximo)
REFRESH_MS   = 5_000       # intervalo de atualização (ms)
DASH_HOST    = "127.0.0.1" # use "0.0.0.0" para expor na rede
DASH_PORT    = 8050

# ================== Data fetch ==================
def get_attr_values(lastN: int):
    """Busca últimos N pontos do STH-Comet. Retorna lista de tuplas (iso_ts_str, float_val)."""
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
            # recvTime já vem em ISO UTC: 'YYYY-MM-DDTHH:MM:SS(.fff)Z'
            ts_raw = e["recvTime"]
            # normaliza para ISO sem 'Z' para o Plotly (ambos funcionam, mas padronizamos)
            ts_iso = ts_raw.replace("Z", "+00:00")
            try:
                v = float(e["attrValue"])
            except (ValueError, TypeError):
                continue
            out.append((ts_iso, v))
        return out
    except Exception as exc:
        print(f"[WARN] Falha no fetch: {exc}")
        return []

# ================== App ==================
app = dash.Dash(__name__)

app.layout = html.Div(
    [
        html.H3("Potenciômetro — série temporal"),
        dcc.Graph(id="fig"),
        dcc.Store(id="store", data={"ts": [], "y": []}),
        dcc.Interval(id="tick", interval=REFRESH_MS, n_intervals=0),
    ],
    style={"maxWidth": 900, "margin": "0 auto", "fontFamily": "sans-serif"},
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

    # de-dup por timestamp (strings ISO), append dos novos
    seen = set(store["ts"])
    for ts_iso, val in batch:
        if ts_iso not in seen:
            store["ts"].append(ts_iso)
            store["y"].append(val)
            seen.add(ts_iso)

    # ordena por tempo
    paired = list(zip(store["ts"], store["y"]))
    paired.sort(key=lambda p: p[0])  # string ISO ordena corretamente

    # aplica janela deslizante
    if len(paired) > MAX_POINTS:
        paired = paired[-MAX_POINTS:]

    ts_sorted, y_sorted = zip(*paired) if paired else ([], [])
    return {"ts": list(ts_sorted), "y": list(y_sorted)}

@app.callback(
    Output("fig", "figure"),
    Input("store", "data"),
)
def draw_figure(store):
    ts = store["ts"]
    y  = store["y"]
    if not ts or not y:
        return go.Figure()

    trace = go.Scatter(
        x=ts,
        y=y,
        mode="lines",             # só linhas (menos poluição visual)
        name="Potenciômetro",
        line=dict(width=1.8),
    )

    fig = go.Figure([trace])
    fig.update_layout(
        title="Valores do potenciômetro (tempo real)",
        xaxis_title="Tempo (UTC)",
        yaxis_title="Valor",
        template="plotly_white",
        margin=dict(l=40, r=30, t=40, b=40),
        hovermode="x unified",
        uirevision="fixed",       # evita 'pulos' a cada atualização
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

# ================== Main ==================
if __name__ == "__main__":
    app.run(debug=True, host=DASH_HOST, port=DASH_PORT)
