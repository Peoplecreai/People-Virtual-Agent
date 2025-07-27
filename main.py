from flask import Flask, request, jsonify
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_bolt import App
import google.generativeai as genai
import os


def require_env_var(name: str) -> str:
    """Return the value of an environment variable or raise an error."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is required")
    return value


SLACK_BOT_TOKEN = require_env_var("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = require_env_var("SLACK_SIGNING_SECRET")
GEMINI_API_KEY = require_env_var("GEMINI_API_KEY")
MODEL = "gemini-2.0-flash"

slack_app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)
handler = SlackRequestHandler(slack_app)
app = Flask(__name__)

genai.configure(api_key=GEMINI_API_KEY)

def get_gemini_response(user_msg):
    model = genai.GenerativeModel(MODEL)
    response = model.generate_content(user_msg)
    return response.text

@slack_app.event("app_mention")
def handle_app_mention(body, say):
    user_msg = body["event"]["text"]
    response = get_gemini_response(user_msg)
    say(response)


@slack_app.event("message")
def handle_message_events(body, say, logger):
    event = body.get("event", {})
    if event.get("channel_type") == "im" and "bot_id" not in event:
        logger.info(body)
        user_msg = event.get("text", "")
        response = get_gemini_response(user_msg)
        say(response)

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
