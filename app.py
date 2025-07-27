from flask import Flask, request
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_bolt import App
import google.generativeai as genai
import os

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
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

@app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
