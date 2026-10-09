from flask import Flask, render_template_string
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import json

#pip install flask flask-socketio paho-mqtt

# ==== MQTT ====
MQTT_BROKER = "54.196.116.14"        # seu broker
MQTT_PORT   = 1883
MQTT_KEEPALIVE = 60
MQTT_TOPIC  = "/TEF/device001/attrs/p"  # seu tópico

# ==== Flask / SocketIO ====
app = Flask(__name__)
socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")

ultimo_valor = None

# ---- Callbacks MQTT (API V1) ----
def on_connect(client, userdata, flags, rc):
    print("[MQTT] Conectado. rc =", rc)
    client.subscribe(MQTT_TOPIC)
    print(f"[MQTT] Subscribed: {MQTT_TOPIC}")

def on_message(client, userdata, msg):
    global ultimo_valor
    raw = msg.payload  # bytes
    valor = None

    # Tente JSON -> número -> texto
    try:
        decoded = raw.decode("utf-8", errors="replace").strip()
        try:
            # Ex.: {"value": 42} ou {"l": 42} ou {"valor": 42}
            obj = json.loads(decoded)
            if isinstance(obj, dict):
                # tente chaves comuns
                for k in ("value", "l", "valor", "data", "v"):
                    if k in obj:
                        valor = obj[k]
                        break
                if valor is None:
                    # se o payload for um dict simples, mande ele todo
                    valor = obj
            else:
                valor = obj
        except json.JSONDecodeError:
            # não é JSON; pode ser "42" ou "1"
            try:
                valor = float(decoded)
            except ValueError:
                valor = decoded  # mantenha como string
    except Exception as e:
        print("[MQTT] Erro ao processar payload:", e)
        valor = None

    ultimo_valor = valor
    socketio.emit("novo_dado", {"valor": ultimo_valor})
    print(f"[MQTT] Mensagem em {msg.topic}: {ultimo_valor}")

# ---- Configura cliente MQTT em API V1 explicitamente ----
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
client.on_connect = on_connect
client.on_message = on_message
# Se tiver usuário/senha:
# client.username_pw_set("usuario", "senha")

client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
client.loop_start()

# ---- Página ----
@app.route("/")
def index():
    return render_template_string("""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Potenciômetro</title>
  <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
  <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
  <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0"></script>
  <style>
    canvas { max-width: 400px; margin: auto; }
    #valor-potenciometro { font-size: 48px; font-weight: bold; text-align:center; }
    .container { max-width: 600px; }
  </style>
</head>
<body>
  <div class="container">
    <h1 class="mt-5 text-center">Potenciômetro</h1>
    <canvas id="gauge" width="400" height="400"></canvas>
    <div id="valor-potenciometro" class="mt-3">Aguardando dados...</div>
  </div>

  <script>
    const ctx = document.getElementById('gauge').getContext('2d');
    const gaugeChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Valor', 'Restante'],
        datasets: [{
          label: 'Valor do Potenciômetro',
          data: [0, 100],
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        cutout: '70%',   // Chart.js v4 (substitui cutoutPercentage)
        animation: { animateRotate: true }
      }
    });

    $(function() {
      const socket = io({ transports: ['websocket', 'polling'] });
      socket.on('novo_dado', (data) => {
        let v = data && data.valor;

        // Se vier objeto { ... }, tente extrair 'value'/'l'/'valor'
        if (v && typeof v === 'object') {
          v = v.value ?? v.l ?? v.valor ?? NaN;
        }

        // Converta para número, se possível
        let num = Number(v);
        if (!Number.isFinite(num)) {
          $('#valor-potenciometro').text('Medição: ' + (data ? JSON.stringify(data.valor) : '—'));
          return;
        }

        // Limite entre 0 e 100 (ajuste conforme seu range real)
        num = Math.max(0, Math.min(100, num));

        $('#valor-potenciometro').text('Medição: ' + num);

        gaugeChart.data.datasets[0].data[0] = num;
        gaugeChart.data.datasets[0].data[1] = 100 - num;
        gaugeChart.update();
      });
    });
  </script>
</body>
</html>
    """)

if __name__ == "__main__":
    # host='0.0.0.0' se for acessar de outra máquina
    socketio.run(app, debug=True)
