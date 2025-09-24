#!/bin/bash
set -e

# -------------------------
# 1. Создаем Docker сеть
# -------------------------
echo "Creating network..."
docker network create --driver bridge microservices-network 2>/dev/null || true

# -------------------------
# 2. Собираем базовый образ
# -------------------------
echo "Building base image..."
docker build -f base.Dockerfile -t base:3.11 .

# -------------------------
# 3. Собираем микросервисы
# -------------------------
echo "Building bot..."
docker build -t bot-image ./bot

echo "Building moderator..."
docker build -t moderator-image ./moderator

echo "Building orchestrator..."
docker build -t orchestrator-image ./orchestrator

echo "Building rag..."
docker build -t rag-image ./rag

echo "Building yandex_gpt..."
docker build -t yandex_gpt-image ./yandex_gpt

echo "Building logger..."
docker build -t logger-image ./logger

# -------------------------
# 4. Останавливаем старые контейнеры (если есть)
# -------------------------
echo "Stopping old containers..."
docker rm -f bot moderator orchestrator rag yandex_gpt logger 2>/dev/null || true

# -------------------------
# 5. Запуск контейнеров в общей сети
# -------------------------
echo "Running containers..."

# Запускаем сервисы в правильном порядке (сначала зависимости)
docker run -d --name yandex_gpt --network microservices-network -p 8000:8000 yandex_gpt-image
docker run -d --name rag --network microservices-network -p 8002:8002 rag-image
docker run -d --name moderator --network microservices-network -p 8001:8001 moderator-image
docker run -d --name orchestrator --network microservices-network -p 8003:8003 orchestrator-image
docker run -d --name bot --network microservices-network bot-image
docker run -d --name logger --network microservices-network logger-image

echo "All services are running. Final check:"
docker ps

# -------------------------
# 6. Проверка сети
# -------------------------
echo "Network info:"
docker network inspect microservices-network


# Тегируем образы
docker tag orchestrator-image:latest cr.yandex/crphfppr95vssc70laib/orchestrator-image:latest
docker tag moderator-image:latest cr.yandex/crphfppr95vssc70laib/moderator-image:latest
docker tag bot-image:latest cr.yandex/crphfppr95vssc70laib/bot-image:latest
docker tag yandex_gpt-image:latest cr.yandex/crphfppr95vssc70laib/yandex_gpt-image:latest
docker tag rag-image:latest cr.yandex/crphfppr95vssc70laib/rag-image:latest
docker tag logger-image:latest cr.yandex/crphfppr95vssc70laib/logger-image:latest
docker tag base:3.11 cr.yandex/crphfppr95vssc70laib/base:3.11

# Пушим образы
docker push cr.yandex/crphfppr95vssc70laib/orchestrator-image:latest
docker push cr.yandex/crphfppr95vssc70laib/moderator-image:latest
docker push cr.yandex/crphfppr95vssc70laib/bot-image:latest
docker push cr.yandex/crphfppr95vssc70laib/yandex_gpt-image:latest
docker push cr.yandex/crphfppr95vssc70laib/rag-image:latest
docker push cr.yandex/crphfppr95vssc70laib/logger-image:latest
docker push cr.yandex/crphfppr95vssc70laib/base:3.11
