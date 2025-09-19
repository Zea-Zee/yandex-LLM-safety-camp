import logging
import time

import jwt
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from injection_filter import COMPILED_PATTERNS
#from semantic_search import SemanticSearcher
from settings import TELEGRAM_TOKEN

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self):
        pass

    def ask_gpt(self, question):
        url_gpt = "http://localhost:8000"
        url_moderator = "http://localhost:8001"

        data_moderator = {
            "question": question
        }
        # Проверка модератором
        try:
            response = requests.post(url_moderator, json=data_moderator)
            response.raise_for_status()  # Проверяем на ошибки HTTP
            is_safe = response.json()['is_safe']

        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе к серверу: {e}")
            return None

        if is_safe == False:
            result = "Ваш вопрос не прошел модерацию. Попробуйте по другому сформулировать вопрос."
            return result

        data_gpt = {
            "message": {
                "user": question
            }
        }

        try:
            response = requests.post(url_gpt, json=data_gpt)
            response.raise_for_status()  # Проверяем на ошибки HTTP

            result = response.json()['gpt_answer']
            return result

        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе к серверу: {e}")
            return None


yandex_bot = TelegramBot()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
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
        await update.message.reply_text(response)

    except Exception as e:
        logger.error(f"Error handling message: {str(e)}")
        await update.message.reply_text(
            "Извините, произошла ошибка при обработке вашего запроса. "
            "Пожалуйста, попробуйте позже."
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "Произошла ошибка. Пожалуйста, попробуйте позже."
        )


def main():
    """Основная функция"""
    try:
        application = Application.builder().token(TELEGRAM_TOKEN).build()

        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_error_handler(error_handler)

        logger.info(f"Бот запускается с токеном {TELEGRAM_TOKEN}")
        application.run_polling()

    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}")


if __name__ == "__main__":
    main()
