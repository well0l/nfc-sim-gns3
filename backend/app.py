import os
import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB = os.environ.get("DB_PATH", "./data/nfc.db")

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS cards (
            uid TEXT PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active'
        );
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_uid TEXT,
            type TEXT,
            amount INTEGER,
            device_id TEXT,
            result TEXT,
            ts DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()

def to_cents(value):
    return int(round(float(str(value).replace(",", ".")), 2) * 100)

@app.route("/api/cards", methods=["POST"])
def create_card():
    data = request.json
    uid = data.get("uid")
    balance = 0
    if data.get("balance"):
        try:
            balance = to_cents(data.get("balance"))
        except:
            pass
    if not uid:
        return jsonify({"error": "uid required"}), 400
    conn = get_db()
    try:
        conn.execute("INSERT INTO cards(uid, balance, status) VALUES(?,?,?)", (uid, balance, "active"))
        conn.commit()
        result = {"result": "ok", "uid": uid}
    except sqlite3.IntegrityError:
        result = {"error": "card already exists"}
    conn.close()
    return jsonify(result)

@app.route("/api/cards/<uid>", methods=["DELETE"])
def delete_card(uid):
    conn = get_db()
    card = conn.execute("SELECT * FROM cards WHERE uid=?", (uid,)).fetchone()
    if not card:
        conn.close()
        return jsonify({"error": "card not found"}), 404
    conn.execute("DELETE FROM cards WHERE uid=?", (uid,))
    conn.commit()
    conn.close()
    return jsonify({"result": "ok", "uid": uid})

@app.route("/api/purchase", methods=["POST"])
def purchase():
    data = request.json
    uid = data.get("card_uid")
    device_id = data.get("device_id", "unknown")
    try:
        amount = to_cents(data.get("amount", 0))
    except (ValueError, TypeError):
        return jsonify({"result": "error_invalid_amount"}), 400
    conn = get_db()
    card = conn.execute("SELECT * FROM cards WHERE uid=?", (uid,)).fetchone()
    if not card:
        result = "denied_notfound"
    elif card["status"] != "active":
        result = "denied_blocked"
    elif card["balance"] < amount:
        result = "denied_funds"
    else:
        conn.execute("UPDATE cards SET balance=balance-? WHERE uid=?", (amount, uid))
        result = "ok"
    conn.execute("INSERT INTO events(card_uid,type,amount,device_id,result) VALUES(?,?,?,?,?)",
                 (uid, "purchase", amount, device_id, result))
    conn.commit()
    conn.close()
    return jsonify({"result": result})

@app.route("/api/topup", methods=["POST"])
def topup():
    data = request.json
    uid = data.get("card_uid")
    device_id = data.get("device_id", "cassa")
    try:
        amount = to_cents(data.get("amount", 0))
    except (ValueError, TypeError):
        return jsonify({"result": "error_invalid_amount"}), 400
    conn = get_db()
    card = conn.execute("SELECT * FROM cards WHERE uid=?", (uid,)).fetchone()
    if not card:
        result = "denied_notfound"
    else:
        conn.execute("UPDATE cards SET balance=balance+? WHERE uid=?", (amount, uid))
        result = "ok"
    conn.execute("INSERT INTO events(card_uid,type,amount,device_id,result) VALUES(?,?,?,?,?)",
                 (uid, "topup", amount, device_id, result))
    conn.commit()
    conn.close()
    return jsonify({"result": result})

@app.route("/api/balance/<uid>")
def balance(uid):
    conn = get_db()
    card = conn.execute("SELECT * FROM cards WHERE uid=?", (uid,)).fetchone()
    conn.close()
    if not card:
        return jsonify({"error": "not found"}), 404
    return jsonify({
        "uid": uid,
        "balance_cents": card["balance"],
        "balance_euro": round(card["balance"] / 100, 2),
        "status": card["status"]
    })

@app.route("/api/events")
def events():
    conn = get_db()
    rows = conn.execute("SELECT * FROM events ORDER BY ts DESC LIMIT 50").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/cards/all")
def list_all_cards():
    conn = get_db()
    cards = conn.execute("SELECT * FROM cards ORDER BY uid").fetchall()
    conn.close()
    return jsonify([{
        "uid": c["uid"],
        "balance_cents": c["balance"],
        "balance_euro": round(c["balance"] / 100, 2),
        "status": c["status"]
    } for c in cards])

@app.route("/api/cards/<uid>/status", methods=["PUT"])
def update_card_status(uid):
    data = request.json
    new_status = data.get("status")
    if new_status not in ["active", "blocked"]:
        return jsonify({"error": "status must be 'active' or 'blocked'"}), 400
    conn = get_db()
    card = conn.execute("SELECT * FROM cards WHERE uid=?", (uid,)).fetchone()
    if not card:
        conn.close()
        return jsonify({"error": "card not found"}), 404
    conn.execute("UPDATE cards SET status=? WHERE uid=?", (new_status, uid))
    conn.commit()
    conn.close()
    return jsonify({"result": "ok", "uid": uid, "new_status": new_status})

@app.route("/api/stats")
def get_stats():
    conn = get_db()
    stats = {}
    stats["total_cards"] = conn.execute("SELECT COUNT(*) as cnt FROM cards").fetchone()["cnt"]
    stats["active_cards"] = conn.execute("SELECT COUNT(*) as cnt FROM cards WHERE status='active'").fetchone()["cnt"]
    stats["blocked_cards"] = conn.execute("SELECT COUNT(*) as cnt FROM cards WHERE status='blocked'").fetchone()["cnt"]
    total_balance = conn.execute("SELECT SUM(balance) as total FROM cards").fetchone()["total"]
    stats["total_balance_cents"] = total_balance if total_balance else 0
    stats["total_balance_euro"] = round((total_balance if total_balance else 0) / 100, 2)
    conn.close()
    return jsonify(stats)

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8080, debug=True)
