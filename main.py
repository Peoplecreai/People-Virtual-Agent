from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
import os
from threading import Thread
import google.generativeai as genai

# Carga variables de entorno
load_dotenv()

slack_token = os.getenv('SLACK_BOT_TOKEN')
client = WebClient(token=slack_token)
BOT_USER_ID = os.getenv('BOT_USER_ID')
if not BOT_USER_ID:
    try:
        auth_info = client.auth_test()
        BOT_USER_ID = auth_info.get("user_id")
    except SlackApiError as e:
        print(f"Failed to fetch bot user ID: {e.response['error']}")

google_api_key = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=google_api_key)
model = genai.GenerativeModel('gemini-2.0-flash')

app = Flask(__name__)

processed_ids = set()
sent_ts = set()

def handle_event(data):
    event = data["event"]
    event_type = event.get("type")
    event_ts = event.get("ts")
    user = event.get("user")
    bot_id = event.get("bot_id")
    subtype = event.get("subtype")
    thread_ts = event.get("thread_ts") or event_ts  # Usa thread_ts o el propio ts si es inicio

    # Ignora mensajes de bots o duplicados
    if (
        event_ts in sent_ts
        or user == BOT_USER_ID
        or bot_id is not None
        or subtype == "bot_message"
    ):
        return

    # Responde cuando inicia un nuevo thread de agente AI
    if event_type == "assistant_thread_started":
        try:
            # Puedes personalizar el mensaje de bienvenida o agregar prompts sugeridos aquí
            welcome = "Hola 👋 Soy tu asistente Gemini. Escríbeme cualquier pregunta."
            client.chat_postMessage(
                channel=event["channel"],
                text=welcome,
                mrkdwn=True,
                thread_ts=thread_ts
            )
        except SlackApiError as e:
            print(f"Error posting welcome message: {e.response['error']}")
        return

    # Responde mensajes directos (DMs, container lateral) o app mentions
    if event_type == "message" and subtype is None:
        if event["channel"].startswith('D') or event.get("channel_type") == 'im' or event.get("channel_type") == "app_home":
            try:
                gemini = model.generate_content(event["text"])
                textout = gemini.text.replace("**", "*")
                response = client.chat_postMessage(
                    channel=event["channel"],
                    text=textout,
                    mrkdwn=True,
                    thread_ts=thread_ts
                )
                sent_ts.add(response.get("ts"))
            except SlackApiError as e:
                print(f"Error posting message: {e.response['error']}")
        return

    if event_type == "app_mention" and event.get("client_msg_id") not in processed_ids:
        if user == BOT_USER_ID:
            return
        try:
            gemini = model.generate_content(event["text"])
            textout = gemini.text.replace("**", "*")
            response = client.chat_postMessage(
                channel=event["channel"],
                text=textout,
                mrkdwn=True,
                thread_ts=thread_ts
            )
            sent_ts.add(response.get("ts"))
            processed_ids.add(event.get("client_msg_id"))
        except SlackApiError as e:
            print(f"Error posting message: {e.response['error']}")
        return

    # Si quieres manejar assistant_thread_context_changed, aquí va el código

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
