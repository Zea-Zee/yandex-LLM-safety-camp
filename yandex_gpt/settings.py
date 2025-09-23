import os

# Для serverless контейнеров переменные окружения передаются через LockBox
SERVICE_ACCOUNT_ID = os.getenv("SERVICE_ACCOUNT_ID")
KEY_ID = os.getenv("KEY_ID")
FOLDER_ID = os.getenv("FOLDER_ID")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
LOGGER_ADDRESS = os.getenv("LOGGER_ADDRESS")

# Проверяем обязательные переменные
required_vars = ['SERVICE_ACCOUNT_ID', 'KEY_ID', 'FOLDER_ID', 'LOGGER_ADDRESS']
for var in required_vars:
    if not os.getenv(var):
        raise ValueError(f"{var} environment variable is required")

# Загружаем приватный ключ
current_dir = os.path.dirname(os.path.abspath(__file__))
private_key_path = os.path.join(current_dir, "private_key.pem")
try:
    with open(private_key_path, "r") as f:
        PRIVATE_KEY = f.read()
except FileNotFoundError:
    raise ValueError("private_key.pem file not found")
