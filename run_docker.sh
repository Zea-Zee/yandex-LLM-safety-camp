#!/bin/bash
set -e

# -------------------------
# 1. Создаем Docker сеть
# -------------------------
echo "Creating network..."
sudo docker network create --driver bridge microservices-network 2>/dev/null || true

# -------------------------
# 2. Собираем базовый образ
# -------------------------
echo "Building base image..."
sudo docker build -f base.Dockerfile -t base:3.11 .

# -------------------------
# 3. Собираем микросервисы
# -------------------------
echo "Building logger..."
sudo docker build -t logger-image ./logger

echo "Building bot..."
sudo docker build -t bot-image ./bot

echo "Building moderator..."
sudo docker build -t moderator-image ./moderator

echo "Building orchestrator..."
sudo docker build -t orchestrator-image ./orchestrator

echo "Building rag..."
sudo docker build -t rag-image ./rag

echo "Building yandex_gpt..."
sudo docker build -t yandex_gpt-image ./yandex_gpt

# -------------------------
# 4. Останавливаем старые контейнеры (если есть)
# -------------------------
echo "Stopping old containers..."

#sudo docker rm -f bot moderator orchestrator rag yandex_gpt 2>/dev/null || true
sudo docker rm -f bot moderator orchestrator rag yandex_gpt logger

# -------------------------
# 5. Запуск контейнеров в общей сети
# -------------------------
echo "Running containers..."

# Запускаем сервисы в правильном порядке (сначала зависимости)

sudo docker run -d --name logger --network microservices-network -p 8020:8020 logger-image
sudo docker run -d --name orchestrator --network microservices-network -p 8003:8003 --env-file ./orchestrator/.env orchestrator-image
sudo docker run -d --name yandex_gpt --network microservices-network -p 8000:8000 --env-file ./yandex_gpt/.env yandex_gpt-image
sudo docker run -d --name rag --network microservices-network -p 8002:8002 --env-file ./rag/.env rag-image
sudo docker run -d --name moderator --network microservices-network -p 8001:8001 --env-file ./moderator/.env moderator-image
sudo docker run -d --name bot --network microservices-network --env-file ./bot/.env bot-image

echo "All services are running. Final check:"
sleep 5
sudo docker ps

# -------------------------
# 6. Проверка сети
# -------------------------
echo "Network info:"
sudo docker network inspect microservices-network