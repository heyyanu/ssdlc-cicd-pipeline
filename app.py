from flask import Flask, jsonify
import os

app = Flask(__name__)


@app.get("/")
def home():
    return jsonify({
        "app": "SSDLC Pipeline App",
        "status": "running",
        "version": "1.0.0",
    }), 200


@app.get("/health")
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    # Bind to all interfaces inside the container so Docker port publishing works.
    app.run(host="0.0.0.0", port=port, debug=False)
