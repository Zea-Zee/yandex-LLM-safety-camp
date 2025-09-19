#!/bin/bash

# Запуск всех процессов в фоне и вывод логов в один терминал

echo "Запуск Yandex GPT сервиса..."
python yandex_gpt/yandex_gpt.py &
YANDEX_PID=$!

echo "Запуск модератора..."
python moderator/moderator.py &
MODERATOR_PID=$!

echo "Запуск бота..."
python bot/bot.py &
wait 5
BOT_PID=$!

echo "Все процессы запущены!"
echo "Yandex GPT PID: $YANDEX_PID"
echo "Moderator PID: $MODERATOR_PID"
echo "Bot PID: $BOT_PID"
echo ""
echo "Нажмите Ctrl+C для остановки всех процессов"

# Функция для остановки всех процессов при выходе
cleanup() {
    echo ""
    echo "Остановка всех процессов..."
    kill $YANDEX_PID $MODERATOR_PID $BOT_PID 2>/dev/null
    wait
    echo "Все процессы остановлены"
    exit 0
}

# Перехватываем сигнал завершения
trap cleanup SIGINT SIGTERM

# Ждем завершения любого из процессов
wait
