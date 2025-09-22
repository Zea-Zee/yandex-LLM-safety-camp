#!/bin/bash
set -e

# -------------------------
# 1. Собираем базовый образ
# -------------------------
echo "Building base image..."
sudo docker build -f base.Dockerfile -t base:3.11 .

# -------------------------
# 2. Собираем микросервисы
# -------------------------
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
# 3. Останавливаем старые контейнеры (если есть)
# -------------------------
echo "Stopping old containers..."
sudo docker rm -f bot moderator orchestrator rag yandex_gpt 2>/dev/null || true

# -------------------------
# 4. Запуск контейнеров с подключением их .env
# -------------------------
echo "Running containers..."

sudo docker run -d --name bot --env-file ./bot/.env bot-image
sudo docker run -d --name moderator --env-file ./moderator/.env moderator-image
sudo docker run -d --name orchestrator --env-file ./orchestrator/.env orchestrator-image
sudo docker run -d --name rag --env-file ./rag/.env rag-image
sudo docker run -d --name yandex_gpt --env-file ./yandex_gpt/.env yandex_gpt-image

echo "All services are running. Final check:"
sleep 1
sudo docker ps
