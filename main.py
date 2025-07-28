from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
import os
from threading import Thread
import google.generativeai as genai

# Load environment variables
load_dotenv()

slack_token = os.getenv('SLACK_BOT_TOKEN')
client = WebClient(token=slack_token)
BOT_USER_ID = os.getenv('BOT_USER_ID')

google_api_key = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=google_api_key)
model = genai.GenerativeModel('gemini-2.0-flash')

app = Flask(__name__)

processed_ids = set()

def handle_event(data):
    event = data["event"]
    event_type = event.get("type")
    user = event.get("user")
    bot_id = event.get("bot_id")
    subtype = event.get("subtype")

    # Si el mensaje es del bot (o de cualquier bot), ignóralo
    if user == BOT_USER_ID or bot_id is not None or subtype == "bot_message":
        return

    # Mensaje directo o en canal (sin subtipo)
    if event_type == "message" and event.get("subtype") is None:
        if event["channel"].startswith('D') or event.get("channel_type") == 'im':
            try:
                gemini = model.generate_content(event["text"])
                textout = gemini.text.replace("**", "*")
                client.chat_postMessage(
                    channel=event["channel"],
                    text=textout,
                    mrkdwn=True
                )
            except SlackApiError as e:
                print(f"Error posting message: {e.response['error']}")

    # Si es una mención a la app
    elif event_type == "app_mention" and event.get("client_msg_id") not in processed_ids:
        # También ignora mensajes que ya procesaste o sean del bot
        if user == BOT_USER_ID:
            return
        try:
            gemini = model.generate_content(event["text"])
            textout = gemini.text.replace("**", "*")
            client.chat_postMessage(
                channel=event["channel"],
                text=textout,
                mrkdwn=True
            )
            processed_ids.add(event.get("client_msg_id"))
        except SlackApiError as e:
            print(f"Error posting message: {e.response['error']}")

def handle_event_async(data):
    Thread(target=handle_event, args=(data,), daemon=True).start()

@app.route('/gemini', methods=['GET']) 
def helloworld(): 
    gemini = model.generate_content("Hi")
    return gemini.text

@app.route("/", methods=["POST"])
def slack_events():
    data = request.json
    if "challenge" in data:
        return jsonify({"challenge": data["challenge"]})
    if "event" in data:
        handle_event_async(data)
    return "", 200

if __name__ == "__main__":
    app.run(debug=True)
