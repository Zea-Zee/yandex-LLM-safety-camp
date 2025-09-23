import os
from dotenv import load_dotenv

load_dotenv()

ADDRESSES = {
    'LOGGER_ADDRESS': os.getenv('LOGGER_ADDRESS'),
    'YANDEX_GPT_ADDRESS': os.getenv('YANDEX_GPT_ADDRESS'),
    'MODERATOR_ADDRESS': os.getenv("MODERATOR_ADDRESS"),
    'RAG_ADDRESS': os.getenv("RAG_ADDRESS")
}
