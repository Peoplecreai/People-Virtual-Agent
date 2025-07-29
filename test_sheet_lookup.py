import os
import json
import gspread
from google.oauth2.service_account import Credentials

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
    worksheet = sh.sheet1
    records = worksheet.get_all_records()
    print(f"[DEBUG] Buscando Slack ID: '{slack_id}'")
    for row in records:
        sheet_slack_id = str(row.get("Slack ID", "")).strip()
        normalized_sheet_id = ''.join(sheet_slack_id.split())
        normalized_slack_id = slack_id.strip()
        print(f"[DEBUG] Sheet Slack ID: '{normalized_sheet_id}' vs. '{normalized_slack_id}'")
        if normalized_slack_id and normalized_sheet_id.endswith(normalized_slack_id):
            pref = row.get("Name (pref)", "").strip()
            if pref:
                print(f"[DEBUG] Matched pref: {pref}")
                return pref
            first = row.get("Name (first)", "").strip()
            if first:
                print(f"[DEBUG] Matched first: {first}")
                return first
            print("[DEBUG] No preferred or first name found in matched row.")
            return None
    print(f"[WARN] No match found in Sheet for slack_id: {slack_id}")
    return None

if __name__ == "__main__":
    # Pega aquí el slack_id como aparece en el Sheet (solo la parte final)
    # Ejemplo: 'U02GJ123456'
    test_slack_id = input("Pon tu Slack ID (el de la hoja): ").strip()
    nombre = get_preferred_name(test_slack_id)
    print(f"Nombre encontrado: {nombre}")
