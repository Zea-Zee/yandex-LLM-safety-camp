# === STAGE 1: build requirements ===
FROM python:3.11-slim AS builder

# Устанавливаем системные зависимости для сборки (если нужно)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем requirements
COPY requirements.txt .

# Создаём виртуальное окружение (по желанию) или просто устанавливаем глобально
RUN pip install --upgrade pip \
 && pip install -r requirements.txt 
#--no-cache-dir 

# === STAGE 2: runtime image ===
FROM python:3.11-slim

# Создаём непривилегированного пользователя
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Копируем установленный Python из builder
COPY --from=builder /usr/local /usr/local

# Переключаемся на непривилегированного пользователя
USER appuser

# Устанавливаем переменные окружения
ENV PYTHONUNBUFFERED=1 \
    PATH="/home/appuser/.local/bin:${PATH}"