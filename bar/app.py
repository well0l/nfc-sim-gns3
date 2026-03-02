from flask import Flask, request, jsonify, render_template_string
import requests, os, hmac, hashlib, time

app = Flask(__name__)
BACKEND    = os.environ.get("BACKEND_URL",  "http://10.10.100.10:8080")
DEVICE_ID  = os.environ.get("DEVICE_ID",   "bar")
SECRET_KEY = os.environ.get("HMAC_SECRET", "change_me_in_production")

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Bar POS</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { 
            font-family: sans-serif; 
            max-width: 420px; 
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
            margin-bottom: 14px;
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
            user-select: none;
        }
        .key:active {
            background: #e9ecef;
            transform: scale(0.95);
        }
        .key.zero { grid-column: span 2; }
        .key.clear { background: #ffc107; border-color: #ffc107; color: white; }

        button {
            width: 100%;
            padding: 18px;
            font-size: 1.1em;
            font-weight: bold;
            background: #28a745;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
            margin-top: 10px;
        }
        button.secondary { background: #6c757d; }
        button:disabled { background: #adb5bd; cursor: not-allowed; }

        .result {
            margin-top: 16px;
            padding: 16px;
            border-radius: 8px;
            font-weight: bold;
            text-align: center;
        }
        .ok { background: #d4edda; color: #155724; }
        .error { background: #f8d7da; color: #721c24; }
        .info { background: #e2e8f0; color: #0f172a; }

        .disabled {
            opacity: 0.45;
            pointer-events: none;
        }
    </style>
</head>
<body>
    <div class="pos">
        <div class="device-id">📟 {{ device_id }}</div>
        <h2>🍸 Bar POS</h2>

        <div class="display" id="display">€0.00</div>

        <div class="keypad" id="keypad">
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

        <button id="confirmBtn" onclick="confirmAmount()">Conferma importo e attendi NFC</button>
        <button id="cancelBtn" class="secondary" onclick="cancelWait()" disabled>Annulla attesa</button>

        <div id="result"></div>
    </div>

    <script>
        let amount = "";      // centesimi come stringa
        let waiting = false;  // true quando aspettiamo NFC
        let charging = false;

        function addDigit(d) {
            if (waiting || charging) return;
            amount += d;
            updateDisplay();
        }

        function clearDisplay() {
            if (waiting || charging) return;
            amount = "";
            updateDisplay();
        }

        function updateDisplay() {
            const cents = parseInt(amount || "0");
            const euro = (cents / 100).toFixed(2);
            document.getElementById("display").textContent = "€" + euro;
        }

        function show(msg, kind) {
            const cls = kind || 'info';
            document.getElementById("result").innerHTML = `<div class="result ${cls}">${msg}</div>`;
        }

        function setWaitingUI(on) {
            waiting = on;
            document.getElementById("confirmBtn").disabled = on;
            document.getElementById("cancelBtn").disabled = !on;
            document.getElementById("keypad").classList.toggle('disabled', on);
        }

        function confirmAmount() {
            const cents = parseInt(amount || "0");
            if (cents === 0) {
                show("❌ Inserisci un importo", 'error');
                return;
            }
            setWaitingUI(true);
            const euro = (cents / 100).toFixed(2);
            show(`📶 Avvicina la carta NFC… (importo €${euro})`, 'info');
        }

        function cancelWait() {
            setWaitingUI(false);
            show("Attesa annullata.", 'info');
        }

        async function doCharge(uid) {
            if (charging) return;
            charging = true;

            const cents = parseInt(amount || "0");
            const euro = (cents / 100).toFixed(2);

            try {
                const r = await fetch("action/charge", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({uid, amount: euro})
                });
                const d = await r.json();

                if (d.result === "ok") {
                    show(`✅ Pagamento €${euro} completato!`, 'ok');
                    amount = "";
                    updateDisplay();
                } else if (d.result === "denied_notfound") {
                    show(`❌ Carta non trovata: ${uid}`, 'error');
                } else if (d.result === "denied_blocked" || d.result === "denied_blocked_auto") {
                    show(`❌ Carta bloccata: ${uid}`, 'error');
                } else if (d.result === "denied_funds") {
                    show(`❌ Saldo insufficiente (richiesti €${euro})`, 'error');
                } else if (d.result === "denied_ratelimit") {
                    show(`⛔ Troppi tentativi, riprova tra poco`, 'error');
                } else if (d.result === "denied_velocity") {
                    show(`⚠️ Transazione sospetta: carta usata su device multipli`, 'error');
                } else {
                    show(`❌ Errore: ${JSON.stringify(d)}`, 'error');
                }
            } catch (e) {
                show(`❌ Errore rete: ${e}`, 'error');
            } finally {
                charging = false;
                setWaitingUI(false);
            }
        }

        // Chiamata dal wrapper Android (o dal parent frame) quando legge una carta.
        window.__onNfcUid = function(uid) {
            if (!waiting) return;
            doCharge(String(uid || "").trim());
        }

        // Fallback: se arriva via postMessage dal parent.
        window.addEventListener('message', (ev) => {
            try {
                if (ev && ev.data && ev.data.type === 'nfc_uid') {
                    window.__onNfcUid(ev.data.uid);
                }
            } catch (e) {}
        });

        updateDisplay();
    </script>
</body>
</html>
"""


def to_cents(value):
    return int(round(float(str(value).replace(",", ".")), 2) * 100)


def generate_token(uid: str, amount_cents: int, device_id: str) -> dict:
    """Genera un token HMAC-SHA256 con nonce e timestamp per una singola richiesta."""
    ts    = int(time.time())
    nonce = os.urandom(8).hex()
    payload = f"{uid}:{amount_cents}:{device_id}:{ts}:{nonce}"
    sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return {"ts": ts, "nonce": nonce, "sig": sig}


@app.route("/")
def index():
    return render_template_string(HTML, device_id=DEVICE_ID)


@app.route("/action/charge", methods=["POST"])
def charge():
    data = request.json
    uid    = data.get("uid")
    amount = data.get("amount")

    try:
        amount_cents = to_cents(amount)
    except (ValueError, TypeError):
        return jsonify({"result": "error_invalid_amount"}), 400

    token = generate_token(uid, amount_cents, DEVICE_ID)

    r = requests.post(f"{BACKEND}/api/purchase", json={
        "card_uid":  uid,
        "amount":    amount,
        "device_id": DEVICE_ID,
        "token":     token
    })
    return jsonify(r.json())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=True)
