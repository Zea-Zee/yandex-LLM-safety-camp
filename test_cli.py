#!/usr/bin/env python3
"""
Тестовый скрипт для проверки CLI клиента
"""
import sys
import os

# Добавляем путь к модулям
sys.path.append(os.path.join(os.path.dirname(__file__), 'yandex_gpt'))

def test_gpt_connection():
    """Тестирует подключение к Yandex GPT"""
    try:
        from yandex_gpt import YandexGPTApi

        print("🔍 Тестируем подключение к Yandex GPT...")
        gpt_api = YandexGPTApi()

        # Тестовый запрос
        response = gpt_api.ask_gpt({"user": "Привет! Как дела?"})

        if response:
            print("✅ Подключение успешно!")
            print(f"📝 Ответ GPT: {response[:100]}...")
            return True
        else:
            print("❌ Не удалось получить ответ от GPT")
            return False

    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Тестирование CLI клиента")
    print("=" * 40)

    if test_gpt_connection():
        print("\n✅ Все готово! Можете запускать CLI клиент:")
        print("   python run_cli.py")
    else:
        print("\n❌ Проверьте настройки .env и private_key.pem")
