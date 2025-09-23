import os

# Для serverless контейнеров переменные окружения передаются через LockBox
ADDRESSES = {
    'LOGGER_ADDRESS': os.getenv('LOGGER_ADDRESS'),
    'YANDEX_GPT_ADDRESS': os.getenv('YANDEX_GPT_ADDRESS'),
    'MODERATOR_ADDRESS': os.getenv("MODERATOR_ADDRESS"),
    'RAG_ADDRESS': os.getenv("RAG_ADDRESS")
}

# Проверяем обязательные переменные
required_vars = ['LOGGER_ADDRESS', 'YANDEX_GPT_ADDRESS', 'MODERATOR_ADDRESS', 'RAG_ADDRESS']
for var in required_vars:
    if not ADDRESSES[var]:
        raise ValueError(f"{var} environment variable is required")
