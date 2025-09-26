#!/usr/bin/env python3
"""
CLI клиент для работы с Yandex GPT с realtime выводом
"""
import sys
import os
import time

# Добавляем путь к модулям
sys.path.append(os.path.join(os.path.dirname(__file__), 'yandex_gpt'))

from yandex_gpt import YandexGPTApi


class CLIClient:
    def __init__(self):
        self.gpt_api = YandexGPTApi()
        print("🤖 CLI клиент для Yandex GPT запущен!")
        print("💡 Введите ваш вопрос (или 'exit' для выхода):")
        print("-" * 50)

    def print_realtime_response(self, question):
        """Выводит ответ GPT в реальном времени"""
        print(f"\n👤 Вы: {question}")
        print("🤖 GPT: ", end="", flush=True)

        try:
            # Получаем streaming ответ
            response_generator = self.gpt_api.ask_gpt(
                {"user": question},
                stream=True
            )

            full_response = ""
            for chunk in response_generator:
                if chunk:
                    print(chunk, end="", flush=True)
                    full_response += chunk
                    time.sleep(0.01)  # Небольшая задержка для плавности

            if not full_response:
                print("❌ Не удалось получить ответ от GPT")

            print("\n" + "-" * 50)

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            print("-" * 50)

    def run(self):
        """Основной цикл CLI"""
        while True:
            try:
                question = input("\n> ").strip()

                if question.lower() in ['exit', 'quit', 'выход']:
                    print("👋 До свидания!")
                    break

                if not question:
                    print("❓ Пожалуйста, введите вопрос")
                    continue

                self.print_realtime_response(question)

            except KeyboardInterrupt:
                print("\n\n👋 До свидания!")
                break
            except EOFError:
                print("\n\n👋 До свидания!")
                break
            except Exception as e:
                print(f"❌ Неожиданная ошибка: {e}")


def main():
    """Запуск CLI клиента"""
    try:
        client = CLIClient()
        client.run()
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        print("💡 Убедитесь, что файл .env настроен правильно")


if __name__ == "__main__":
    main()
