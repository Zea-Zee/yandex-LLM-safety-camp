#!/bin/bash

echo "=== Testing Bot Service ==="

BOT_URL="https://bbadigfuua7qlsgtdtos.containers.yandexcloud.net"
BOT_TOKEN="8432904792:AAFdQYOdMwqU7Nic80liV8ndwfxmKXgrx90"

# 1. Health check
echo "1. Health check:"
curl -s "$BOT_URL/health" | jq

# 2. Set TG webhook
echo -e "\n2. Setting Telegram webhook:"
curl -X POST "https://api.telegram.org/bot$BOT_TOKEN/setWebhook" \
     -H "Content-Type: application/json" \
     -d "{\"url\": \"$BOT_URL/webhook\"}" | jq

# 3. Get TG webhook info
echo -e "\n3. Getting webhook info:"
curl -s "https://api.telegram.org/bot$BOT_TOKEN/getWebhookInfo" | jq

# 4. Test webhook processing with /start
echo -e "\n4. Testing /start command:"
curl -X POST "$BOT_URL/webhook" \
     -H "Content-Type: application/json" \
     -d '{"message": {"text": "/start", "chat": {"id": 123}, "from": {"id": 123, "first_name": "Test"}}, "update_id": 1}' | jq

# 5. Test webhook processing with regular message
echo -e "\n5. Testing regular message:"
curl -X POST "$BOT_URL/webhook" \
     -H "Content-Type: application/json" \
     -d '{"message": {"text": "Привет! Как дела?", "chat": {"id": 123}, "from": {"id": 123, "first_name": "Test"}}, "update_id": 2}' | jq

# 6. Test webhook processing with test message
echo -e "\n6. Testing test message:"
curl -X POST "$BOT_URL/webhook" \
     -H "Content-Type: application/json" \
     -d '{"message": {"text": "test", "chat": {"id": 123}, "from": {"id": 123, "first_name": "Test"}}, "update_id": 3}' | jq

echo -e "\n=== Bot test completed ==="
echo "Note: Check Yandex Cloud logs to see if messages are being processed"
