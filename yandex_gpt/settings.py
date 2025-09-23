import os

# Для serverless контейнеров переменные окружения передаются через LockBox
SERVICE_ACCOUNT_ID = os.getenv("SERVICE_ACCOUNT_ID")
KEY_ID = os.getenv("KEY_ID")
FOLDER_ID = os.getenv("FOLDER_ID")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
LOGGER_ADDRESS = os.getenv("LOGGER_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

# Проверяем обязательные переменные
required_vars = ['SERVICE_ACCOUNT_ID', 'KEY_ID', 'FOLDER_ID', 'LOGGER_ADDRESS', 'PRIVATE_KEY']
for var in required_vars:
    if not os.getenv(var):
        raise ValueError(f"{var} environment variable is required")
