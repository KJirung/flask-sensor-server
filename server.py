from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/sensor", methods=["POST"])
def sensor_data():
    data = request.get_json()
    print("받은 데이터:", data)
    return jsonify({"status": "received"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
