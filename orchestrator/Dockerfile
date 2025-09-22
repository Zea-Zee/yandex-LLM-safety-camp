FROM base:3.11

WORKDIR /app

COPY . ./orchestrator

WORKDIR /app/orchestrator

EXPOSE 8003

CMD ["python", "orchestrator.py"]