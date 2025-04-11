from flask import Flask, request, jsonify
import logging
import os
import json
from datetime import datetime

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# 저장 폴더 생성 (없으면 자동 생성)
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

@app.route("/sensor", methods=["POST"])
def receive_data():
    data = request.get_json()

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = os.path.join(LOG_DIR, f"sensor_{timestamp}.json")

    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        app.logger.info(f"저장 완료: {filename}")
    except Exception as e:
        app.logger.error(f"저장 실패: {e}")

    return jsonify({"status": "received"})
