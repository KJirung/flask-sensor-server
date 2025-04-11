from flask import Flask, request, jsonify
import logging
import sys
from datetime import datetime

# Flask 앱 초기화
app = Flask(__name__)

# 로그 설정 (stdout으로 출력)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

@app.route("/sensor", methods=["POST"])
def receive_data():
    data = request.get_json()

    # 수신 시간과 함께 로그 출력
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    app.logger.info(f"[{timestamp}] 📦 받은 센서 데이터:\n{data}")

    return jsonify({"status": "received"})
