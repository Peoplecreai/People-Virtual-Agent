from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
import os
from threading import Thread
from google import genai
import gspread
from google.oauth2.service_account import Credentials
import json

# ========== Configuración ==========
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

# Google Gemini
google_api_key = os.getenv('GEMINI_API_KEY')
if not google_api_key:
    raise RuntimeError('GEMINI_API_KEY is not set')
model_name = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
genai_client = genai.Client(api_key=google_api_key)

# Normaliza posibles formatos de identificadores de Slack
def normalize_slack_id(value: str) -> str:
    """Extrae el ID puro desde menciones o links de Slack."""
    if not value:
        return ""
    value = str(value).strip()
    if value.startswith("<@") and value.endswith(">"):
        value = value[2:-1]
        if "|" in value:
            value = value.split("|")[0]
    if value.startswith("https://"):
        value = value.rstrip("/").split("/")[-1]
    return value

# ========== Acceso Google Sheets ==========
def get_preferred_name(slack_id):
    creds_json = os.getenv("MY_GOOGLE_CREDS")
    if not creds_json:
        print("[ERROR] MY_GOOGLE_CREDS not set")
        return None
    creds_dict = json.loads(creds_json)
    credentials = Credentials.from_service_account_info(creds_dict, scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ])
    gc = gspread.authorize(credentials)
    sheet_id = os.getenv("SHEET_ID")
    if not sheet_id:
        print("[ERROR] SHEET_ID not set")
        return None
    sh = gc.open_by_key(sheet_id)
    worksheet = sh.sheet1
    records = worksheet.get_all_records()
    for row in records:
        sheet_slack_id = normalize_slack_id(row.get("Slack ID"))
        if sheet_slack_id == slack_id:
            pref = row.get("Name (pref)", "").strip()
            if pref:
                return pref
            first = row.get("Name (first)", "").strip()
            if first:
                return first
            return None
    return None

# Fallback a perfil de Slack cuando no hay nombre en el Sheet
def get_slack_name(slack_id):
    try:
        info = client.users_info(user=slack_id)
        profile = info.get("user", {}).get("profile", {})
        return profile.get("display_name") or profile.get("real_name")
    except SlackApiError as e:
        print(f"Failed to fetch Slack profile: {e.response['error']}")
    except Exception as e:
        print(f"Unexpected error fetching Slack profile: {e}")
    return None

# Resolución de nombre (Slack -> Sheet preferido sobrescribe) con caché simple
_name_cache = {}
def resolve_name(slack_id):
    if slack_id in _name_cache:
        return _name_cache[slack_id]
    name = get_slack_name(slack_id)
    pref = get_preferred_name(slack_id)
    if pref:
        name = pref
    if name:
        _name_cache[slack_id] = name
    return name

# Detecta si es DM top-level (primer mensaje del hilo)
def is_top_level_dm(event: dict) -> bool:
    ch = event.get("channel", "")
    ch_type = event.get("channel_type")
    is_dm = ch.startswith("D") or ch_type == "im"
    thread_ts = event.get("thread_ts")
    ts = event.get("ts")
    is_top = (thread_ts is None) or (thread_ts == ts)
    return is_dm and is_top

# ========== Flask app y Slack handler ==========
app = Flask(__name__)
processed_ids = set()
sent_ts = set()
processed_event_ids = set()

def handle_event(data):
    # Evita reprocesar el mismo evento por reintentos de Slack
    eid = data.get("event_id")
    if eid and eid in processed_event_ids:
        return
    if eid:
        processed_event_ids.add(eid)

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

    # DM: Saludo personalizado solo en el primer mensaje del hilo
    if event_type == "message" and subtype is None:
        if event.get("channel", "").startswith('D') or event.get("channel_type") in ['im', 'app_home']:
            if is_top_level_dm(event):
                name = resolve_name(user)
                if name:
                    saludo = f"Hola {name}, ¿cómo te puedo ayudar hoy?"
                else:
                    saludo = "¡Hola! ¿Cómo estás? ¿En qué puedo ayudarte hoy?"
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

            # No es el primer mensaje del hilo → responde con Gemini
            try:
                response = genai_client.models.generate_content(
                    model=model_name,
                    contents=event.get("text", ""),
                )
                textout = (response.text or "").replace("**", "*")
                resp = client.chat_postMessage(
                    channel=event["channel"],
                    text=textout or "¿Puedes repetir tu mensaje?",
                    mrkdwn=True,
                    thread_ts=thread_ts
                )
                sent_ts.add(resp.get("ts"))
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
            response = genai_client.models.generate_content(
                model=model_name,
                contents=event.get("text", ""),
            )
            textout = (response.text or "").replace("**", "*")
            resp = client.chat_postMessage(
                channel=event["channel"],
                text=textout or "",
                mrkdwn=True,
                thread_ts=thread_ts
            )
            sent_ts.add(resp.get("ts"))
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
        response = genai_client.models.generate_content(
            model=model_name,
            contents="Hi",
        )
        return response.text
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
