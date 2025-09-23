import os

# Для serverless контейнеров не используем dotenv,
# переменные окружения будут переданы через LockBox
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ORCHESTRATOR_ADDRESS = os.getenv("ORCHESTRATOR_ADDRESS")

# Проверяем обязательные переменные
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable is required")
if not ORCHESTRATOR_ADDRESS:
    raise ValueError("ORCHESTRATOR_ADDRESS environment variable is required")
