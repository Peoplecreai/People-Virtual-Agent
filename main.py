from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import os
from dotenv import load_dotenv
import google.generativeai as genai
from threading import Thread

processed_ids = set()

# Carga variables de entorno desde .env
load_dotenv()

# Llaves de API y configuración de modelos
google_api_key = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=google_api_key)
model = genai.GenerativeModel('gemini-2.0-flash')

slack_token = os.getenv('SLACK_BOT_TOKEN')
client = WebClient(token=slack_token)
BOT_USER_ID = os.getenv('BOT_USER_ID')
app = Flask(__name__)

def handle_event_async(data):
    thread = Thread(target=handle_event, args=(data,), daemon=True)
    thread.start()

def handle_event(data):
    event = data["event"]

    # Filtra mensajes sin usuario o del propio bot (evita loop)
    if not event.get("user") or event.get("user") == BOT_USER_ID:
        return

    # Mensaje directo sin subtipo (solo mensajes normales de usuarios)
    if event["type"] == "message" and event.get("subtype") is None:
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

    # Menciones al bot en canales públicos/privados
    elif event["type"] == "app_mention" and event.get("client_msg_id") not in processed_ids:
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
