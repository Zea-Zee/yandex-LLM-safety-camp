import os

# Для serverless контейнеров переменные окружения передаются через LockBox
S3_ENDPOINT = os.getenv("S3_ENDPOINT")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")
S3_PREFIX = os.getenv("S3_PREFIX")
ORCHESTRATOR_ADDRESS = os.getenv("ORCHESTRATOR_ADDRESS")

# Проверяем обязательные переменные
required_vars = ['S3_ENDPOINT', 'S3_ACCESS_KEY', 'S3_SECRET_KEY', 'S3_BUCKET', 'S3_PREFIX', 'ORCHESTRATOR_ADDRESS']
for var in required_vars:
    if not os.getenv(var):
        raise ValueError(f"{var} environment variable is required")
