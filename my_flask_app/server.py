from flask import Flask, request, jsonify, render_template
import csv
import os
from datetime import datetime, timedelta
import pandas as pd
import firebase_admin
from firebase_admin import credentials, messaging

app = Flask(__name__)

# Firebase Admin SDK 초기화
cred = credentials.Certificate("service_account_file.json")  # 경로에 맞게 수정
firebase_admin.initialize_app(cred)

# 디렉토리 경로 설정
LOG_DIR = "logs"
FEEDBACK_DIR = "feedback"
MAPPING_DIR = "mapping"
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(FEEDBACK_DIR, exist_ok=True)
os.makedirs(MAPPING_DIR, exist_ok=True)

# 유저 정보 저장을 위한 파일 경로
USER_FILE = os.path.join(MAPPING_DIR, "mapping_user.csv")

# 센서 및 행동 데이터 헤더 정의
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
    "top_app",
    "audio_isWiredHeadsetOn",
    "audio_isBluetoothHeadsetConnected",
    "audio_isBluetoothA2dpOutput",
    "audio_isSpeakerOn",
    "audio_ringerMode",
    "audio_mediaVolume",
    "audio_connectedBluetoothDevices",
    "unlock",
    "notif_pkg",
    "notif_removed",
    "screen_check",
    "notif_count",
    "step_count"  # 🆕 step_count 추가
]

def sanitize(value):
    """데이터의 공백, 줄 바꿈, 탭 등을 처리하고 안전하게 반환"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.replace('\n', '').replace('\r', '').strip()
    if isinstance(value, list):
        return "|".join([sanitize(str(v)) for v in value])
    return str(value)

@app.route("/", methods=["GET"])
def health_check():
    return "OK", 200

@app.route("/register", methods=["POST"])
def register_user():
    data = request.get_json()
    if not data or "device_id" not in data or "name" not in data or "birth" not in data or "gender" not in data or "device_token" not in data:
        return jsonify({"status": "error", "message": "Missing fields"}), 400

    name = sanitize(data.get("name"))
    birth = sanitize(data.get("birth"))
    gender = sanitize(data.get("gender"))
    device_token = sanitize(data.get("device_token"))

    if not name or not birth or not gender or not device_token:
        return jsonify({"status": "error", "message": "All fields must be filled"}), 400

    try:
        write_header = not os.path.exists(USER_FILE)
        with open(USER_FILE, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["device_id", "name", "birth", "gender", "device_token", "timestamp"])
            if write_header:
                writer.writeheader()
            writer.writerow({
                "device_id": sanitize(data["device_id"]),
                "name": name,
                "birth": birth,
                "gender": gender,
                "device_token": device_token,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

        return jsonify({"status": "success", "message": "User registered successfully"}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": "Registration failed"}), 500

@app.route("/sensor", methods=["POST"])
def receive_data():
    raw_data = request.get_json()
    if not raw_data or "device_id" not in raw_data:
        return jsonify({"status": "error", "message": "Missing device_id"}), 400

    data = {h: sanitize(raw_data.get(h)) for h in headers}
    if all((v is None or str(v).strip() == "") for k, v in data.items() if k != "device_id"):
        return jsonify({"status": "skipped", "message": "empty data"}), 200

    device_id = data["device_id"]
    filename = os.path.join(LOG_DIR, f"{device_id}.csv")
    write_header = not os.path.exists(filename)

    try:
        with open(filename, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            if write_header:
                writer.writeheader()
            writer.writerow(data)
        return jsonify({"status": "success"}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"센서/행동 데이터 저장 실패: {str(e)}"}), 500

@app.route("/feedback", methods=["POST"])
def receive_feedback():
    data = request.get_json()
    if not data or "device_id" not in data or "top_app" not in data or "purpose" not in data:
        return jsonify({"status": "error", "message": "Missing fields"}), 400

    feedback_file = os.path.join(FEEDBACK_DIR, f"{data['device_id']}.csv")
    write_header = not os.path.exists(feedback_file)

    try:
        with open(feedback_file, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["device_id", "timestamp", "top_app", "purpose"])
            if write_header:
                writer.writeheader()
            writer.writerow({
                "device_id": sanitize(data["device_id"]),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "top_app": sanitize(data["top_app"]),
                "purpose": sanitize(data["purpose"])
            })

        return jsonify({"status": "success"}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"피드백 저장 실패: {str(e)}"}), 500

@app.route("/monitor")
def monitor():
    devices_status = []
    now = datetime.now()
    files = os.listdir(LOG_DIR)
    user_files = [f for f in files if f.endswith(".csv") and f != "feedback.csv"]

    for filename in user_files:
        device_id = filename.replace(".csv", "")
        filepath = os.path.join(LOG_DIR, filename)

        try:
            df = pd.read_csv(filepath, encoding="utf-8-sig")
            if df.empty or "timestamp" not in df.columns:
                status = "no data"
                last_time_str = "-"
            else:
                last_time_str = df.iloc[-1]["timestamp"]
                last_time = datetime.strptime(last_time_str, "%Y-%m-%d %H:%M:%S")
                delta = now - last_time
                status = "connected" if delta <= timedelta(minutes=2) else "disconnected"
        except Exception as e:
            status = "error"
            last_time_str = str(e)

        devices_status.append({
            "device_id": device_id,
            "last_time": last_time_str,
            "status": status
        })

    return render_template("monitor.html", devices=devices_status)

@app.route("/notify_disconnected", methods=["POST"])
def notify_disconnected_users():
    now = datetime.now()
    files = os.listdir(LOG_DIR)
    user_files = [f for f in files if f.endswith(".csv") and f != "feedback.csv"]

    for filename in user_files:
        device_id = filename.replace(".csv", "")
        filepath = os.path.join(LOG_DIR, filename)

        try:
            df = pd.read_csv(filepath)
            if df.empty or "timestamp" not in df.columns:
                status = "no data"
                last_time_str = "-"
            else:
                last_time_str = df.iloc[-1]["timestamp"]
                last_time = datetime.strptime(last_time_str, "%Y-%m-%d %H:%M:%S")
                delta = now - last_time
                status = "connected" if delta <= timedelta(minutes=1) else "disconnected"

            if status == "disconnected":
                device_token = get_device_token(device_id)
                if device_token:
                    title = "연결 해제 알림"
                    body = "데이터 수집이 중단되었습니다. 앱을 다시 실행해 주세요."
                    send_push_notification(device_token, title, body)

        except Exception as e:
            app.logger.error(f"{device_id} → 오류 발생: {e}")

    return jsonify({"status": "success", "message": "알림 전송이 완료되었습니다."}), 200

def get_device_token(device_id):
    with open(USER_FILE, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["device_id"] == device_id:
                return row["device_token"]
    return None

def send_push_notification(device_token, title, body):
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        token=device_token,
    )
    return messaging.send(message)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
