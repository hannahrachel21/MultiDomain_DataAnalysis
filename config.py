import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

# Where uploaded files are stored
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploaded_excels")
os.makedirs(UPLOAD_DIR, exist_ok=True)
