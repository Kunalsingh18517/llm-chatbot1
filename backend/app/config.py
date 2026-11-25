import os
from dotenv import load_dotenv

load_dotenv()

LLM_API_KEYS = [key.strip() for key in os.getenv("LLM_API_KEYS", "").split(",") if key.strip()]
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if origin.strip()]
ENABLE_FAILURE_SIMULATION = os.getenv("ENABLE_FAILURE_SIMULATION", "false").lower() == "true"
DEFAULT_SYSTEM_PROMPT = os.getenv(
    "DEFAULT_SYSTEM_PROMPT",
    "You are a helpful, accurate AI assistant. Answer clearly and conversationally."
)
