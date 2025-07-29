from src.flask_app import client  # Import client desde flask_app
from slack_sdk.errors import SlackApiError

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

def is_top_level_dm(event: dict) -> bool:
    ch = event.get("channel", "")
    ch_type = event.get("channel_type")
    is_dm = ch.startswith("D") or ch_type == "im"
    thread_ts = event.get("thread_ts")
    ts = event.get("ts")
    is_top = (thread_ts is None) or (thread_ts == ts)
    return is_dm and is_top

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
