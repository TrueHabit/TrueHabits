import os
from dotenv import load_dotenv
import logging

load_dotenv()

# Configurar logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
# )

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

if not TELEGRAM_TOKEN:
    logging.error("TELEGRAM_TOKEN no está definido en .env")
    raise ValueError("TELEGRAM_TOKEN no está definido")

if not OPENAI_API_KEY:
    logging.error("OPENAI_API_KEY no está definido en .env")
    raise ValueError("OPENAI_API_KEY no está definido")

if not DATABASE_URL:
    logging.error("DATABASE_URL no está definido en .env")
    raise ValueError("DATABASE_URL no está definido")
