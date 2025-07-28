import gspread
from google.oauth2.service_account import Credentials
import os
import json

def test_gsheet_access():
    creds_json = os.getenv("MY_GOOGLE_CREDS")
    if not creds_json:
        print("NO CREDENCIAL JSON")
        return
    creds_dict = json.loads(creds_json)
    credentials = Credentials.from_service_account_info(creds_dict, scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ])
    gc = gspread.authorize(credentials)
    sheet_id = os.getenv("SHEET_ID")
    if not sheet_id:
        print("NO SHEET_ID")
        return
    try:
        sh = gc.open_by_key(sheet_id)
        worksheet = sh.sheet1
        print(f"Acceso correcto al Sheet '{worksheet.title}'. Primeras filas:")
        rows = worksheet.get_all_records()
        for r in rows[:3]:  # muestra las 3 primeras filas
            print(r)
    except Exception as e:
        print("ERROR ACCEDIENDO SHEET:", e)

# Pon esto en tu main temporalmente:
if __name__ == "__main__":
    test_gsheet_access()
    # app.run(debug=True)
