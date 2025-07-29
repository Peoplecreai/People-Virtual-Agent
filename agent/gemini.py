from google import genai  # Asumiendo que es google-generativeai o similar, ajusta si es necesario
import os

# Setup de Gemini
google_api_key = os.getenv('GEMINI_API_KEY')
if not google_api_key:
    raise RuntimeError('GEMINI_API_KEY is not set')
model_name = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
genai_client = genai.Client(api_key=google_api_key)
