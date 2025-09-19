import os
from dotenv import load_dotenv

load_dotenv()

YANDEXGPT_ADDRESS = os.getenv("YANDEXGPT_ADDRESS")
MODERATOR_ADDRESS = os.getenv("MODERATOR_ADDRESS")
RAG_ADDRESS = os.getenv("RAG_ADDRESS")