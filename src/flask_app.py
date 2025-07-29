from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
import os
from src.handlers import handle_event_async
from utils.slack_utils import normalize_slack_id  # Si necesitas en futuro
from agent.gemini import genai_client, model_name  # Para helloworld

# Globals (sets y caches que eran globales)
processed_ids = set()
sent_ts = set()
processed_event_ids = set()
greeted_threads = set()  # (channel_id:thread_ts) ya saludados

# Configuración inicial (mueve de main)
load_dotenv()

slack_token = os.getenv('SLACK_BOT_TOKEN')
if not slack_token:
    raise RuntimeError('SLACK_BOT_TOKEN is not set')
client = WebClient(token=slack_token)

BOT_USER_ID = os.getenv('BOT_USER_ID')
if not BOT_USER_ID:
    try:
        auth_info = client.auth_test()
        BOT_USER_ID = auth_info.get("user_id")
    except SlackApiError as e:
        print(f"Failed to fetch bot user ID: {e.response['error']}")

# Google Gemini (setup movido a agent/gemini.py, importamos client)

app = Flask(__name__)

@app.route('/gemini', methods=['GET'])
def helloworld():
    try:
        response = genai_client.models.generate_content(
            model=model_name,
            contents="Hi",
        )
        return response.text
    except Exception as e:  # Generalizado, como en original
        return f"Unexpected error: {e}", 500

@app.route("/", methods=["POST"])
def slack_events():
    data = request.json
    if "challenge" in data:
        return jsonify({"challenge": data["challenge"]})
    if "event" in data or data.get("type") == "assistant_thread_started":
        handle_event_async(data)
    return "", 200
