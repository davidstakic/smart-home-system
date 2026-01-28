from flask import Flask
from mqtt_client import start_mqtt

app = Flask(__name__)


@app.route("/")
def health():
    return {"status": "Server running (MQTT → InfluxDB)"}


if __name__ == "__main__":
    start_mqtt()
    app.run(host="0.0.0.0", port=5001)