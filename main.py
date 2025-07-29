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

# -------- Utilidades ----------
def normalize_slack_id(value: str) -> str:
    """Devuelve el ID de usuario Slack en formato UXXXXXXXXX a partir de:
       <@U…|alias>, URLs, o 'T……-U……' (team-user)."""
    if not value:
        return ""
    v = str(value).strip()

    # <@U…|alias>
    if v.startswith("<@") and v.endswith(">"):
        v = v[2:-1]
        if "|" in v:
            v = v.split("|")[0]

    # URL -> último segmento
    if v.startswith("https://"):
        v = v.rstrip("/").split("/")[-1]

    # 'T……-U……' (como en tu sheet)
    if "-" in v:
        left, right = v.split("-", 1)
        if right.startswith("U"):
            v = right

    # Si viene 'T…… U……' o algo raro, toma desde la U…
    u_pos = v.find("U")
    if u_pos > 0:
        v = v[u_pos:]

    return v

def _nk(s: str) -> str:
    """Normaliza nombres de columnas: minúsculas y alfanumérico."""
    return "".join(ch for ch in s.lower() if ch.isalnum())

# ========== Acceso Google Sheets ==========
def _open_sheet():
    creds_json = os.getenv("MY_GOOGLE_CREDS")
    if not creds_json:
        print("[ERROR] MY_GOOGLE_CREDS not set"); return None
    creds_dict = json.loads(creds_json)
    credentials = Credentials.from_service_account_info(creds_dict, scopes=[
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly"
    ])
    gc = gspread.authorize(credentials)
    sheet_id = os.getenv("SHEET_ID")
    if not sheet_id:
        print("[ERROR] SHEET_ID not set"); return None
    sh = gc.open_by_key(sheet_id)
    tab = os.getenv("SHEET_TAB")  # opcional
    ws = sh.worksheet(tab) if tab else sh.sheet1  # "Hoja 1" es la primera
    return ws

def get_user_record(slack_id):
    """Regresa el dict completo de la fila que coincide con Slack ID. Si no hay match, None."""
    try:
        ws = _open_sheet()
        if not ws:
            return None
        records = ws.get_all_records()
        target = normalize_slack_id(slack_id)
        for row in records:
            row_norm = { _nk(k): v for k, v in row.items() }
            sid = row_norm.get("slackid") or row_norm.get("slack_id") or \
                  row_norm.get("slack") or row_norm.get("idslack") or row.get("Slack ID")
            sid = normalize_slack_id(str(sid)) if sid is not None else ""
            if sid == target:
                return row  # devuelve la fila tal cual, con sus claves originales
        return None
    except Exception as e:
        print(f"[SHEETS get_user_record] {e}")
        return None

def get_preferred_name(slack_id):
    """Devuelve Name (pref) o Name (first) desde Sheets."""
    row = get_user_record(slack_id)
    if not row:
        return None
    # intenta claves típicas
    if isinstance(row.get("Name (pref)"), str) and row["Name (pref)"].strip():
        return row["Name (pref)"].strip()
    if isinstance(row.get("Name (first)"), str) and row["Name (first)"].strip():
        return row["Name (first)"].strip()
    # intenta variantes normalizadas
    rn = { _nk(k): v for k, v in row.items() }
    pref = rn.get("namepref")
    first = rn.get("namefirst") or rn.get("firstname")
    if isinstance(pref, str) and pref.strip():
        return pref.strip()
    if isinstance(first, str) and first.strip():
        return first.strip()
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

# Resolución de nombre con caché: Slack -> Sheet sobrescribe si existe
_name_cache = {}
def resolve_name(slack_id):
    if slack_id in _name_cache:
        return _name_cache[slack_id]
    name = get_slack_name(slack_id)     # rápido
    pref = get_preferred_name(slack_id) # si hay en Sheet, sobrescribe
    if pref:
        name = pref
    if name:
        _name_cache[slack_id] = name
    return name

# Detecta si es DM top-level (fallback cuando no usemos assistant_thread_started)
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
greeted_threads = set()  # (channel_id:thread_ts) ya saludados

def handle_event(data):
    eid = data.get("event_id")
    if eid and eid in processed_event_ids:
        return
    if eid:
        processed_event_ids.add(eid)

    event = data.get("event") or data
    event_type = event.get("type")
    event_ts = event.get("ts")
    user = event.get("user")
    bot_id = event.get("bot_id")
    subtype = event.get("subtype")
    thread_ts = event.get("thread_ts") or event_ts

    # 1) assistant_thread_started: saluda aquí y marca el hilo
    if event_type == "assistant_thread_started":
        at = event.get("assistant_thread") or {}
        user_id = at.get("user_id")
        ch_id = at.get("channel_id") or at.get("context", {}).get("channel_id")
        th_ts = at.get("thread_ts")
        if ch_id and th_ts:
            key = f"{ch_id}:{th_ts}"
            if key not in greeted_threads:
                name = resolve_name(user_id) if user_id else None
                saludo = f"Hola {name}, ¿cómo te puedo ayudar hoy?" if name else "¡Hola! ¿Cómo estás? ¿En qué puedo ayudarte hoy?"
                try:
                    client.chat_postMessage(
                        channel=ch_id,
                        text=saludo,
                        mrkdwn=True,
                        thread_ts=th_ts
                    )
                    greeted_threads.add(key)
                except SlackApiError as e:
                    print(f"[assistant_thread_started] chat_postMessage: {e.response.get('error')}")
        return

    # Ignora mensajes de bots o duplicados
    if (
        event_ts in sent_ts
        or user == BOT_USER_ID
        or bot_id is not None
        or subtype == "bot_message"
    ):
        return

    # 2) DM normal (fallback si no hay assistant_thread_started)
    if event_type == "message" and subtype is None:
        if event.get("channel", "").startswith('D') or event.get("channel_type") in ['im', 'app_home']:
            key = f"{event['channel']}:{thread_ts}"
            
            if is_top_level_dm(event):
                # Solo saluda si no ha sido saludado antes en este hilo
                if key not in greeted_threads:
                    name = resolve_name(user)
                    saludo = f"Hola {name}, ¿cómo te puedo ayudar hoy?" if name else "¡Hola! ¿Cómo estás? ¿En qué puedo ayudarte hoy?"
                    try:
                        client.chat_postMessage(
                            channel=event["channel"],
                            text=saludo,
                            mrkdwn=True,
                            thread_ts=thread_ts
                        )
                        sent_ts.add(event_ts)
                        greeted_threads.add(key)  # Agrega solo después de éxito
                    except SlackApiError as e:
                        print(f"Error posting saludo: {e.response['error']}")
                return  # Opcional: si quieres procesar el primer mensaje con Gemini también, quita este return

            # No es primer mensaje → responde con Gemini (sin chequear greeted_threads)
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

    # 3) Menciones en canal
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
    if "event" in data or data.get("type") == "assistant_thread_started":
        handle_event_async(data)
    return "", 200

if __name__ == "__main__":
    app.run(debug=True)
