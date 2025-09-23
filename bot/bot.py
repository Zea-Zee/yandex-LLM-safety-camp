import time

import jwt
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from settings import TELEGRAM_TOKEN, ORCHESTRATOR_ADDRESS

def send_to_logger(level, message):
    log_message = {
        "name": "bot",
        "level": level,
        "message": message
    }
    try:
        orchestrator = ORCHESTRATOR_ADDRESS + '/log'
        response = requests.post(orchestrator, json=log_message)
    except Exception as e:
        print(f"Error when send log: {str(e)}")
        return False


class TelegramBot:
    def ask_gpt(self, question):
        query = {"question": question}

        try:
            response = requests.post(ORCHESTRATOR_ADDRESS + '/ask_gpt', json=query)
            response.raise_for_status()
            gpt_answer = response.json()['gpt_answer']
        except requests.exceptions.RequestException as e:
            send_to_logger("error", f"Ошибка при запросе к серверу: {e}")
            return None

        return gpt_answer


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
        send_to_logger("error", f"Error handling message: {str(e)}")
        await update.message.reply_text(
            "Извините, произошла ошибка при обработке вашего запроса. "
            "Пожалуйста, попробуйте позже."
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    send_to_logger("error", f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "Произошла ошибка. Пожалуйста, попробуйте позже."
        )


def main():
    """Основная функция"""
    time.sleep(5)
    try:
        application = Application.builder().token(TELEGRAM_TOKEN).build()

        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_error_handler(error_handler)

        send_to_logger("info", "Бот запускается...")
        application.run_polling()

    except Exception as e:
        send_to_logger("error", f"Failed to start bot: {str(e)}")


if __name__ == "__main__":
    main()
