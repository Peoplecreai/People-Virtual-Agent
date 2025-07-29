from dotenv import load_dotenv
import os

load_dotenv()

SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
if not SLACK_BOT_TOKEN:
    raise RuntimeError('SLACK_BOT_TOKEN is not set')

BOT_USER_ID = os.getenv('BOT_USER_ID')

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise RuntimeError('GEMINI_API_KEY is not set')

GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')

MY_GOOGLE_CREDS = os.getenv("MY_GOOGLE_CREDS")
SHEET_ID = os.getenv("SHEET_ID")
SHEET_TAB = os.getenv("SHEET_TAB")
