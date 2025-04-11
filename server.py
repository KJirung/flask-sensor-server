from flask import Flask, request, jsonify
import logging

app = Flask(__name__)

@app.route("/sensor", methods=["POST"])
def receive_data():
    data = request.get_json()
    
    # 로그 출력
    print("받은 데이터:", data)
    
    # 또는 logging 사용
    app.logger.info(f"센서 수신: {data}")

    return jsonify({"status": "received"})
