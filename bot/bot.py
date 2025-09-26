import sys
import os

from telegram import Update
from telegram.ext import (Application, CommandHandler, ContextTypes,
                          MessageHandler, filters)

# Добавляем путь к yandex_gpt модулю
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'yandex_gpt'))

from yandex_gpt import YandexGPTApi
from settings import TELEGRAM_TOKEN


class TelegramBot:
    def __init__(self):
        self.gpt_api = YandexGPTApi()

    def ask_gpt(self, question):
        try:
            # Простой запрос без системного промпта
            response = self.gpt_api.ask_gpt({"user": question})
            return response
        except Exception as e:
            print(f"Ошибка при запросе к Yandex GPT: {e}")
            return None

yandex_bot = TelegramBot()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /start
    """

    await update.message.reply_text(
        "Привет! Я бот для работы с Yandex GPT. Просто напиши мне свой вопрос"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    user_message = update.message.text

    if not user_message.strip():
        await update.message.reply_text("Пожалуйста, введите вопрос")
        return

    try:
        # Показываем статус "печатает"
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )

        response = yandex_bot.ask_gpt(user_message)
        if response is None:
            await update.message.reply_text(
                "Сервис временно недоступен. Попробуйте ещё раз позже."
            )
        else:
            await update.message.reply_text(response)

    except Exception as e:
        print(f"Error handling message: {str(e)}")
        await update.message.reply_text(
            "Извините, произошла ошибка при обработке вашего запроса. "
            "Пожалуйста, попробуйте позже."
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    print(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "Произошла ошибка. Пожалуйста, попробуйте позже."
        )


def main():
    """Основная функция"""
    try:
        application = Application.builder().token(TELEGRAM_TOKEN).build()

        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_error_handler(error_handler)

        print("Бот запускается...")
        application.run_polling()

    except Exception as e:
        print(f"Failed to start bot: {str(e)}")


if __name__ == "__main__":
    main()
