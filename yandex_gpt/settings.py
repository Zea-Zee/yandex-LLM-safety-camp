import os

from dotenv import load_dotenv

load_dotenv()

SERVICE_ACCOUNT_ID = os.getenv("SERVICE_ACCOUNT_ID")
KEY_ID = os.getenv("KEY_ID")
FOLDER_ID = os.getenv("FOLDER_ID")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

current_dir = os.path.dirname(os.path.abspath(__file__))
private_key_path = os.path.join(current_dir, "private_key.pem")

with open(private_key_path, "r") as f:
    PRIVATE_KEY = f.read()

S3_ENDPOINT = os.getenv("S3_ENDPOINT")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")
S3_PREFIX = os.getenv("S3_PREFIX")
