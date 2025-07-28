from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
import os
from threading import Thread
from google import genai
from google.genai.errors import APIError
import gspread
from google.oauth2.service_account import Credentials
import json

# Carga variables de entorno
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

# Inicializa Gemini GenAI SDK (nuevo)
client_gemini = genai.Client()  # Usará GEMINI_API_KEY automáticamente desde el entorno
MODEL_NAME = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')  # Puedes usar 'gemini-2.5-flash' por default

# === Sheets ===
def get_preferred_name(slack_id):
    creds_json = os.getenv("MY_GOOGLE_CREDS")
    if not creds_json:
        print("MY_GOOGLE_CREDS not set")
        return None
    creds_dict = json.loads(creds_json)
    credentials = Credentials.from_service_account_info(creds_dict, scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ])
    gc = gspread.authorize(credentials)
    sheet_id = os.getenv("SHEET_ID")
    if not sheet_id:
        print("SHEET_ID not set")
        return None
    sh = gc.open_by_key(sheet_id)
    worksheet = sh.sheet1  # Cambia esto si usas otra pestaña/tab
    records = worksheet.get_all_records()
    # Revisa headers para debug si no encuentra nada
    # print("Headers:", worksheet.row_values(1))
    for row in records:
        sheet_slack_id = str(row.get("Slack ID", ""))
        # Solo compara la parte final
        if sheet_slack_id.endswith(slack_id):
            # Preferred name si existe, sino Name (first)
            pref = row.get("Name (pref)", "").strip()
            if pref:
                return pref
            first = row.get("Name (first)", "").strip()
            if first:
                return first
            return None
    return None

app = Flask(__name__)

processed_ids = set()
sent_ts = set()

def get_gemini_response(text):
    try:
        response = client_gemini.models.generate_content(
            model=MODEL_NAME,
            contents=text,
        )
        # Normalmente response.text, pero revisa si cambia el output (puede ser candidates[] en algunas versiones)
        return response.text
    except APIError as e:
        print(f"Gemini API error: {e.message}")
        return "Ocurrió un error con el servicio de Gemini. Intenta de nuevo."
    except Exception as e:
        print(f"Unexpected error: {e}")
        return "Ocurrió un error inesperado. Intenta de nuevo."

def handle_event(data):
    event = data["event"]
    event_type = event.get("type")
    event_ts = event.get("ts")
    user = event.get("user")
    bot_id = event.get("bot_id")
    subtype = event.get("subtype")
    thread_ts = event.get("thread_ts") or event_ts

    # Ignora mensajes de bots o duplicados
    if (
        event_ts in sent_ts
        or user == BOT_USER_ID
        or bot_id is not None
        or subtype == "bot_message"
    ):
        return

    # Saludo personalizado solo al primer mensaje del thread (no respondas dos veces)
    if event_type == "message" and subtype is None:
        if event["channel"].startswith('D') or event.get("channel_type") in ['im', 'app_home']:
            if thread_ts == event_ts:
                name = get_preferred_name(user)
                if name:
                    saludo = f"Hola {name}, ¿cómo te puedo ayudar hoy?"
                else:
                    saludo = "Hola, ¿cómo te puedo ayudar hoy?"
                try:
                    client.chat_postMessage(
                        channel=event["channel"],
                        text=saludo,
                        mrkdwn=True,
                        thread_ts=thread_ts
                    )
                    sent_ts.add(event_ts)
                except SlackApiError as e:
                    print(f"Error posting saludo: {e.response['error']}")
                return

            # Continuación del hilo: responde usando Gemini
            textout = get_gemini_response(event["text"])
            try:
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

    # Si es mención a la app en canal
    if event_type == "app_mention" and event.get("client_msg_id") not in processed_ids:
        if user == BOT_USER_ID:
            return
        textout = get_gemini_response(event["text"])
        try:
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

def handle_event_async(data):
    Thread(target=handle_event, args=(data,), daemon=True).start()

@app.route('/gemini', methods=['GET'])
def helloworld():
    return get_gemini_response("Hi")

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
