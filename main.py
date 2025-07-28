from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
import os
from threading import Thread
import google.genai as genai
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

google_api_key = os.getenv('GEMINI_API_KEY')
if not google_api_key:
    raise RuntimeError('GEMINI_API_KEY is not set')
model_name = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')
genai_client = genai.Client(api_key=google_api_key)

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
            # fallback genérico
            return None
    return None

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
    thread_ts = event.get("thread_ts") or event_ts

    # Ignora mensajes de bots o duplicados
    if (
        event_ts in sent_ts
        or user == BOT_USER_ID
        or bot_id is not None
        or subtype == "bot_message"
    ):
        return

    # Saludo personalizado solo al primer mensaje del thread
    if event_type == "message" and subtype is None:
        # DM o lateral/app_home
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

            # Si ya es continuación del hilo, responde usando Gemini (o tu lógica actual)
            try:
                gemini = genai_client.models.generate_content(
                    model=model_name,
                    contents=event["text"],
                )
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
            except genai.errors.APIError as e:
                print(f"Gemini API error: {e.message}")
            except Exception as e:
                print(f"Unexpected error: {e}")
        return

    # Si es mención a la app en canal
    if event_type == "app_mention" and event.get("client_msg_id") not in processed_ids:
        if user == BOT_USER_ID:
            return
        try:
            gemini = genai_client.models.generate_content(
                model=model_name,
                contents=event["text"],
            )
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
        except genai.errors.APIError as e:
            print(f"Gemini API error: {e.message}")
        except Exception as e:
            print(f"Unexpected error: {e}")
        return

def handle_event_async(data):
    Thread(target=handle_event, args=(data,), daemon=True).start()

@app.route('/gemini', methods=['GET'])
def helloworld():
    try:
        gemini = genai_client.models.generate_content(
            model=model_name,
            contents="Hi",
        )
        return gemini.text
    except genai.errors.APIError as e:
        return f"Gemini API error: {e.message}", 500
    except Exception as e:
        return f"Unexpected error: {e}", 500

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
