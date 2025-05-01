from flask import Flask, request, jsonify
import csv
import os
from datetime import datetime

app = Flask(__name__)
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

headers = [
    "device_id", "timestamp",
    "acc_x", "acc_y", "acc_z",
    "gyro_x", "gyro_y", "gyro_z",
    "gravity_x", "gravity_y", "gravity_z",
    "lux",
    "lin_x", "lin_y", "lin_z",
    "mag_x", "mag_y", "mag_z",
    "battery", "battery_status",
    "screen_state", "network_type",
    "pressure", "proximity",
    "latitude", "longitude",
    "top_app"
]

@app.route("/sensor", methods=["POST"])
def receive_data():
    data = request.get_json()
    if not data or "device_id" not in data:
        return jsonify({"status": "error", "message": "Missing device_id"}), 400

    for h in headers:
        if h not in data:
            data[h] = None

    device_id = data["device_id"]
    filename = os.path.join(LOG_DIR, f"{device_id}.csv")
    write_header = not os.path.exists(filename)

    try:
        with open(filename, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            if write_header:
                writer.writeheader()
            writer.writerow(data)

        app.logger.info(f"{device_id} → 저장 완료")
        return jsonify({"status": "success"}), 200

    except Exception as e:
        app.logger.error(f"저장 실패: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
