from flask import Flask, request
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_bolt import App
from google.cloud import aiplatform

import os

# Configura tus tokens
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]
PROJECT_ID = os.environ["GOOGLE_PROJECT_ID"]
LOCATION = os.environ.get("GOOGLE_LOCATION", "us-central1")
GEMINI_MODEL = "gemini-1.5-pro" # O el modelo que vayas a usar

slack_app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)
handler = SlackRequestHandler(slack_app)
app = Flask(__name__)

@slack_app.event("app_mention")
def handle_app_mention(body, say):
    user_msg = body["event"]["text"]
    response = get_gemini_response(user_msg)
    say(response)

def get_gemini_response(user_msg):
    # Inicializa el cliente (requiere auth configurada en Cloud Run)
    aiplatform.init(project=PROJECT_ID, location=LOCATION)
    model = aiplatform.TextGenerationModel(GEMINI_MODEL)
    resp = model.predict(user_msg)
    return resp.text

@app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
