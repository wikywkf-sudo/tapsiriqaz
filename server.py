from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({
        "project": "TapsiriqAZ",
        "status": "online",
        "message": "Server işləyir"
    })

@app.route("/postback", methods=["GET", "POST"])
def postback():
    data = request.args.to_dict() if request.method == "GET" else request.form.to_dict()
    print("Postback sorğusu alındı:", data, flush=True)
    return jsonify({"received": True}), 200

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
