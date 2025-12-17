import os

class Config:
    # FastAPI backend (из README: обычно http://127.0.0.1:8000) :contentReference[oaicite:3]{index=3}
    API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", os.getenv("APP_SECRET_KEY", "dev-change-me"))
