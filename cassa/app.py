import os
from flask import Flask, render_template

app = Flask(__name__)

BACKEND_URL = os.environ.get("BACKEND_URL", "http://10.10.100.10:8080")
DEVICE_ID = os.environ.get("DEVICE_ID", "cassa")

@app.route("/")
def admin_panel():
    return render_template("admin.html", backend_url=BACKEND_URL, device_id=DEVICE_ID)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
