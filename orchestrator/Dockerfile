FROM base:3.11

WORKDIR /app

COPY . ./orchestrator

WORKDIR /app/orchestrator

# Health check для serverless контейнера
# PORT будет установлен автоматически Yandex Cloud
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8003}/health || exit 1

CMD ["python", "orchestrator.py"]
