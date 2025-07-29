import gspread
from google.oauth2.service_account import Credentials
import os
import json
from utils.slack_utils import normalize_slack_id

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
            row_norm = { _nk(k): v for k, v in row.items() }  # _nk movido a name_resolution, pero lo uso aquí; puedes importarlo si separas.
            sid = row_norm.get("slackid") or row_norm.get("slack_id") or \
                  row_norm.get("slack") or row_norm.get("idslack") or row.get("Slack ID")
            sid = normalize_slack_id(str(sid)) if sid is not None else ""
            if sid == target:
                return row  # devuelve la fila tal cual, con sus claves originales
        return None
    except Exception as e:
        print(f"[SHEETS get_user_record] {e}")
        return None

# Nota: _nk está en name_resolution.py, importa desde allí si lo usas aquí: from utils.name_resolution import _nk
