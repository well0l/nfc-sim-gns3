from flask import Flask, request, jsonify, render_template_string
import requests, os

app = Flask(__name__)
BACKEND = os.environ.get("BACKEND_URL", "http://10.10.100.10:8080")
DEVICE_ID = os.environ.get("DEVICE_ID", "bar")

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Bar POS</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { 
            font-family: sans-serif; 
            max-width: 400px; 
            margin: 0 auto; 
            padding: 20px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .pos {
            background: white;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }
        h2 { 
            margin: 0 0 20px 0; 
            color: #333; 
            text-align: center;
        }
        .device-id {
            background: #667eea;
            color: white;
            padding: 8px;
            border-radius: 8px;
            text-align: center;
            margin-bottom: 20px;
            font-size: 0.9em;
        }
        .display {
            background: #f8f9fa;
            border: 3px solid #e9ecef;
            border-radius: 12px;
            padding: 20px;
            text-align: right;
            font-size: 2.5em;
            font-weight: bold;
            color: #333;
            margin-bottom: 20px;
            min-height: 60px;
            font-family: 'Courier New', monospace;
        }
        .keypad {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-bottom: 20px;
        }
        .key {
            background: #f8f9fa;
            border: 2px solid #dee2e6;
            padding: 20px;
            font-size: 1.5em;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.1s;
            font-weight: bold;
        }
        .key:active {
            background: #e9ecef;
            transform: scale(0.95);
        }
        .key.zero { grid-column: span 2; }
        .key.clear { background: #ffc107; border-color: #ffc107; color: white; }
        input {
            width: 100%;
            padding: 16px;
            font-size: 1.1em;
            border: 2px solid #dee2e6;
            border-radius: 8px;
            box-sizing: border-box;
            margin-bottom: 12px;
        }
        button {
            width: 100%;
            padding: 18px;
            font-size: 1.2em;
            font-weight: bold;
            background: #28a745;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }
        button:hover { background: #218838; }
        button:active { transform: scale(0.98); }
        button:disabled { background: #6c757d; cursor: not-allowed; }
        .result {
            margin-top: 16px;
            padding: 16px;
            border-radius: 8px;
            font-weight: bold;
            text-align: center;
        }
        .ok { background: #d4edda; color: #155724; }
        .error { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <div class="pos">
        <div class="device-id">📟 {{ device_id }}</div>
        <h2>🍸 Bar POS</h2>
        
        <div class="display" id="display">0.00</div>
        
        <div class="keypad">
            <div class="key" onclick="addDigit('1')">1</div>
            <div class="key" onclick="addDigit('2')">2</div>
            <div class="key" onclick="addDigit('3')">3</div>
            <div class="key" onclick="addDigit('4')">4</div>
            <div class="key" onclick="addDigit('5')">5</div>
            <div class="key" onclick="addDigit('6')">6</div>
            <div class="key" onclick="addDigit('7')">7</div>
            <div class="key" onclick="addDigit('8')">8</div>
            <div class="key" onclick="addDigit('9')">9</div>
            <div class="key clear" onclick="clearDisplay()">C</div>
            <div class="key zero" onclick="addDigit('0')">0</div>
        </div>
        
        <input id="card_uid" placeholder="UID Carta cliente" />
        <button onclick="charge()">💳 Addebita</button>
        
        <div id="result"></div>
    </div>

    <script>
        let amount = "";

        function addDigit(d) {
            amount += d;
            updateDisplay();
        }

        function clearDisplay() {
            amount = "";
            updateDisplay();
        }

        function updateDisplay() {
            const cents = parseInt(amount || "0");
            const euro = (cents / 100).toFixed(2);
            document.getElementById("display").textContent = "€" + euro;
        }

        function show(msg, ok) {
            document.getElementById("result").innerHTML =
                `<div class="result ${ok ? 'ok' : 'error'}">${msg}</div>`;
        }

        async function charge() {
            const uid = document.getElementById("card_uid").value.trim();
            const cents = parseInt(amount || "0");
            
            if (!uid) {
                show("❌ Inserisci la carta del cliente", false);
                return;
            }
            if (cents === 0) {
                show("❌ Inserisci un importo", false);
                return;
            }

            const euro = (cents / 100).toFixed(2);
            const r = await fetch("/action/charge", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({uid, amount: euro})
            });
            const d = await r.json();
            
            if (d.result === "ok") {
                show(`✅ Pagamento €${euro} completato!`, true);
                amount = "";
                updateDisplay();
                document.getElementById("card_uid").value = "";
            } else if (d.result === "denied_notfound") {
                show(`❌ Carta non trovata: ${uid}`, false);
            } else if (d.result === "denied_blocked") {
                show(`❌ Carta bloccata: ${uid}`, false);
            } else if (d.result === "denied_funds") {
                show(`❌ Saldo insufficiente (richiesti €${euro})`, false);
            } else {
                show(`❌ Errore: ${JSON.stringify(d)}`, false);
            }
        }

        updateDisplay();
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML, device_id=DEVICE_ID)

@app.route("/action/charge", methods=["POST"])
def charge():
    data = request.json
    r = requests.post(f"{BACKEND}/api/purchase", json={
        "card_uid": data.get("uid"),
        "amount": data.get("amount"),
        "device_id": DEVICE_ID
    })
    return jsonify(r.json())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=True)
