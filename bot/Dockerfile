FROM base:3.11

WORKDIR /app

COPY . ./bot

WORKDIR /app/bot

# Expose port for serverless container
EXPOSE 8080

# Health check for serverless container
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "bot.py"]
