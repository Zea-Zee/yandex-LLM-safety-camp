#!/usr/bin/env python3
"""
Простой скрипт запуска Telegram бота
"""
import sys
import os

# Добавляем путь к модулям
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'yandex_gpt'))

if __name__ == "__main__":
    from bot.bot import main
    main()
