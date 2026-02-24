import os
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

BACKEND = os.environ.get("BACKEND_URL", "http://10.10.100.10:8080")
DEVICE_ID = os.environ.get("DEVICE_ID", "cassa")

@app.route("/")
def admin_panel():
    return render_template("admin.html", device_id=DEVICE_ID)

@app.route("/api/stats")
def proxy_stats():
    r = requests.get(f"{BACKEND}/api/stats")
    return jsonify(r.json())

@app.route("/api/cards/all")
def proxy_cards_all():
    r = requests.get(f"{BACKEND}/api/cards/all")
    return jsonify(r.json())

@app.route("/api/cards", methods=["POST"])
def proxy_create_card():
    r = requests.post(f"{BACKEND}/api/cards", json=request.json)
    return jsonify(r.json())

@app.route("/api/cards/<uid>/status", methods=["PUT"])
def proxy_card_status(uid):
    r = requests.put(f"{BACKEND}/api/cards/{uid}/status", json=request.json)
    return jsonify(r.json())

@app.route("/api/cards/<uid>", methods=["DELETE"])
def proxy_delete_card(uid):
    r = requests.delete(f"{BACKEND}/api/cards/{uid}")
    return jsonify(r.json())

@app.route("/api/topup", methods=["POST"])
def proxy_topup():
    r = requests.post(f"{BACKEND}/api/topup", json=request.json)
    return jsonify(r.json())

@app.route("/api/events")
def proxy_events():
    r = requests.get(f"{BACKEND}/api/events")
    return jsonify(r.json())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
