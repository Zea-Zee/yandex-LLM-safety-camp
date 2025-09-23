import os

# Для serverless контейнеров переменные окружения передаются через LockBox
ORCHESTRATOR_ADDRESS = os.getenv("ORCHESTRATOR_ADDRESS")

# Проверяем обязательные переменные
if not ORCHESTRATOR_ADDRESS:
    raise ValueError("ORCHESTRATOR_ADDRESS environment variable is required")
