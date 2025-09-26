#!/usr/bin/env python3
"""
Быстрый запуск CLI клиента
"""
import sys
import os

# Добавляем путь к модулям
sys.path.append(os.path.join(os.path.dirname(__file__), 'yandex_gpt'))

if __name__ == "__main__":
    from cli_client import main
    main()
