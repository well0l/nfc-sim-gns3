from flask import Flask, request, jsonify, render_template_string
import requests, os

app = Flask(__name__)
BACKEND = os.environ.get("BACKEND_URL", "http://localhost:8080")
DEVICE_ID = os.environ.get("DEVICE_ID", "vending_unknown")

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Distributore NFC</title>
    <style>
        body { font-family: sans-serif; max-width: 500px; margin: 40px auto; padding: 0 20px; background: #f5f5f5; }
        h2 { color: #c00; }
        .product { background: white; padding: 16px; margin: 12px 0; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .product button { background: #c00; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-size: 1em; }
        .product button:hover { background: #a00; }
        input { display: block; width: 100%; margin: 12px 0; padding: 12px; font-size: 1em; box-sizing: border-box; border: 2px solid #ccc; border-radius: 4px; }
        .result { margin-top: 16px; padding: 12px; border-radius: 4px; font-weight: bold; }
        .ok { background: #d4edda; color: #155724; }
        .error { background: #f8d7da; color: #721c24; }
        .device-id { background: #333; color: white; padding: 8px; border-radius: 4px; text-align: center; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="device-id">🤖 {{ device_id }}</div>
    <h2>🥤 Distributore Automatico</h2>

    <input id="card_uid" placeholder="Avvicina carta (es. CARD001)" />

    <div class="product">
        <span>☕ Caffè — €1.00</span>
        <button onclick="tap('1.00')">Acquista</button>
    </div>

    <div class="product">
        <span>🥤 Coca Cola — €1.50</span>
        <button onclick="tap('1.50')">Acquista</button>
    </div>

    <div class="product">
        <span>🍫 Snickers — €1.20</span>
        <button onclick="tap('1.20')">Acquista</button>
    </div>

    <div class="product">
        <span>🥪 Panino — €3.50</span>
        <button onclick="tap('3.50')">Acquista</button>
    </div>

    <div id="result"></div>

    <script>
        function show(msg, ok) {
            document.getElementById("result").innerHTML =
                `<div class="result ${ok ? 'ok' : 'error'}">${msg}</div>`;
        }

        async function tap(price) {
            const uid = document.getElementById("card_uid").value.trim();
            if (!uid) {
                show("❌ Inserisci l'UID della carta", false);
                return;
            }
            const r = await fetch("/action/purchase", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({uid, amount: price})
            });
            const d = await r.json();
            
            if (d.result === "ok") {
                show(`✅ Acquisto completato! Carta: ${uid} — Importo: €${price}`, true);
            } else if (d.result === "denied_notfound") {
                show(`❌ Carta non trovata: ${uid}`, false);
            } else if (d.result === "denied_blocked") {
                show(`❌ Carta bloccata: ${uid}`, false);
            } else if (d.result === "denied_funds") {
                show(`❌ Saldo insufficiente: ${uid}`, false);
            } else {
                show(`❌ Errore: ${JSON.stringify(d)}`, false);
            }
        }
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML, device_id=DEVICE_ID)

@app.route("/action/purchase", methods=["POST"])
def purchase():
    data = request.json
    r = requests.post(f"{BACKEND}/api/purchase", json={
        "card_uid": data.get("uid"),
        "amount": data.get("amount"),
        "device_id": DEVICE_ID
    })
    return jsonify(r.json())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
