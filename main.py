from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
import os
from threading import Thread
import google.generativeai as genai

import google.auth
from google.cloud import secretmanager
from google.oauth2 import service_account
from googleapiclient.discovery import build
import base64
import json

# Load environment variables
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

GOOGLE_PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_CRED_SECRET = os.getenv("GOOGLE_CRED_SECRET", "MY_GOOGLE_CRED")  # default

app = Flask(__name__)

processed_ids = set()
sent_ts = set()


# ================== GOOGLE SHEETS ACCESS VIA SECRET MANAGER =====================

def get_google_creds():
    # Usa la librería de Google Cloud Secret Manager
    client_secret = secretmanager.SecretManagerServiceClient()
    name = f"projects/{GOOGLE_PROJECT_ID}/secrets/{GOOGLE_CRED_SECRET}/versions/latest"
    response = client_secret.access_secret_version(name=name)
    service_account_info = json.loads(response.payload.data.decode("UTF-8"))
    creds = service_account.Credentials.from_service_account_info(service_account_info, scopes=[
        "https://www.googleapis.com/auth/spreadsheets.readonly"
    ])
    return creds

def get_user_info_from_sheet(slack_id):
    creds = get_google_creds()
    service = build("sheets", "v4", credentials=creds)
    sheet = service.spreadsheets()
    result = sheet.values().get(
        spreadsheetId=GOOGLE_SHEET_ID,
        range="A1:H100"  # ajusta si tienes más filas
    ).execute()
    values = result.get("values", [])
    if not values or len(values) < 2:
        return None

    headers = [col.strip() for col in values[0]]
    slack_col_idx = headers.index("Slack ID") if "Slack ID" in headers else None
    name_pref_idx = headers.index("Name (pref)") if "Name (pref)" in headers else None
    name_first_idx = headers.index("Name (first)") if "Name (first)" in headers else None
    seniority_idx = headers.index("Seniority") if "Seniority" in headers else None

    for row in values[1:]:
        if slack_col_idx is not None and len(row) > slack_col_idx:
            # Busca por coincidencia exacta del ID completo
            if row[slack_col_idx].strip() == slack_id:
                # Saca los nombres según prefiera
                name = ""
                if name_pref_idx is not None and len(row) > name_pref_idx and row[name_pref_idx]:
                    name = row[name_pref_idx]
                elif name_first_idx is not None and len(row) > name_first_idx:
                    name = row[name_first_idx]
                else:
                    name = "usuario"
                seniority = row[seniority_idx] if seniority_idx is not None and len(row) > seniority_idx else ""
                return {"name": name, "seniority": seniority}
    return None

# ================== SLACK EVENT HANDLER =====================

def handle_event(data):
    event = data["event"]
    event_ts = event.get("ts")
    event_type = event.get("type")
    user = event.get("user")
    bot_id = event.get("bot_id")
    subtype = event.get("subtype")
    text = event.get("text", "")

    # Ignora mensajes enviados previamente por este bot o por cualquier otro bot
    if (
        event_ts in sent_ts
        or user == BOT_USER_ID
        or bot_id is not None
        or subtype == "bot_message"
    ):
        return

    # Si es mensaje directo
    if event_type == "message" and event.get("subtype") is None and (event["channel"].startswith('D') or event.get("channel_type") == 'im'):
        # Busca nombre en Google Sheets usando el Slack ID
        user_info = get_user_info_from_sheet(user)
        if user_info and text.strip().lower() in ["hola", "hello", "buenas", "hey"]:
            saludo = f"Hola {user_info['name']} ¿cómo te puedo ayudar hoy?"
            client.chat_postMessage(
                channel=event["channel"],
                text=saludo,
                mrkdwn=True
            )
            sent_ts.add(event_ts)
            return

        # Si no es un saludo básico, procesa como consulta a Gemini
        try:
            gemini = model.generate_content(text)
            textout = gemini.text.replace("**", "*")
            client.chat_postMessage(
                channel=event["channel"],
                text=textout,
                mrkdwn=True
            )
            sent_ts.add(event_ts)
        except SlackApiError as e:
            print(f"Error posting message: {e.response['error']}")

    # Si es una mención a la app
    elif event_type == "app_mention" and event.get("client_msg_id") not in processed_ids:
        if user == BOT_USER_ID:
            return
        # Aquí también puedes saludar con nombre si quieres
        user_info = get_user_info_from_sheet(user)
        if user_info and text.strip().lower() in ["hola", "hello", "buenas", "hey"]:
            saludo = f"Hola {user_info['name']} ¿cómo te puedo ayudar hoy?"
            client.chat_postMessage(
                channel=event["channel"],
                text=saludo,
                mrkdwn=True
            )
            processed_ids.add(event.get("client_msg_id"))
            sent_ts.add(event_ts)
            return
        try:
            gemini = model.generate_content(text)
            textout = gemini.text.replace("**", "*")
            client.chat_postMessage(
                channel=event["channel"],
                text=textout,
                mrkdwn=True
            )
            sent_ts.add(event_ts)
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
