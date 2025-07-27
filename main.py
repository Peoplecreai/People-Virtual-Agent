from flask import Flask, request, jsonify
from slack_bot import slack_app, handler

app = Flask(__name__)


@app.route("/", methods=["POST"])
def slack_events():
    if request.json and "challenge" in request.json:
        return jsonify({"challenge": request.json["challenge"]})
    return handler.handle(request)


@app.route("/healthz", methods=["GET"])
def health_check():
    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
