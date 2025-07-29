from threading import Thread
from slack_sdk.errors import SlackApiError
from utils.slack_utils import is_top_level_dm, get_slack_name
from utils.name_resolution import resolve_name, _name_cache
from agent.gemini import genai_client, model_name
from tools.sheets import get_user_record, get_preferred_name
from src.flask_app import client, BOT_USER_ID, processed_ids, sent_ts, processed_event_ids, greeted_threads

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
        except Exception as e:
            print(f"Unexpected error: {e}")
        return

def handle_event_async(data):
    Thread(target=handle_event, args=(data,), daemon=True).start()
