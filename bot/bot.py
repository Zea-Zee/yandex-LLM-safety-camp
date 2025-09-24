import time
import os
import asyncio
import aiohttp
from aiohttp import web

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters
)

from settings import TELEGRAM_TOKEN, ORCHESTRATOR_ADDRESS


async def send_to_logger(level, message):
    log_message = {
        "name": "bot",
        "level": level,
        "message": message
    }
    try:
        # Убираем двойной слеш в URL
        orchestrator_url = ORCHESTRATOR_ADDRESS.rstrip('/') + '/log'
        async with aiohttp.ClientSession() as session:
            async with session.post(orchestrator_url, json=log_message) as response:
                await response.text()
    except Exception as e:
        print(f"Error when send log: {str(e)}")
        return False


class TelegramBot:
    async def ask_gpt(self, question):
        query = {"question": question}

        try:
            await send_to_logger("info", f"Calling GPT service")
            # Убираем двойной слеш в URL
            orchestrator_url = ORCHESTRATOR_ADDRESS.rstrip('/') + '/ask_gpt'

            async with aiohttp.ClientSession() as session:
                async with session.post(orchestrator_url, json=query) as response:
                    response.raise_for_status()
                    data = await response.json()
                    gpt_answer = data['gpt_answer']
                    await send_to_logger("info", f"Got response from orchestrator")
        except aiohttp.ClientError as e:
            await send_to_logger("error", f"Ошибка при запросе к серверу: {e}")
            return None
        except Exception as e:
            await send_to_logger("error", f"Unexpected error: {e}")
            return None

        return gpt_answer


yandex_bot = TelegramBot()


async def start(update: Update, context):
    """Обработчик команды /start"""
    await update.message.reply_text(
        "Привет! Я бот для работы с Yandex GPT. Просто напиши мне свой вопрос"
    )


async def handle_message(update: Update, context):
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

        response = await yandex_bot.ask_gpt(user_message)
        if response is None:
            await update.message.reply_text(
                "Сервис временно недоступен. Попробуйте ещё раз позже."
            )
        else:
            await update.message.reply_text(response)

    except Exception as e:
        await send_to_logger("error", f"Error handling message: {str(e)}")
        await update.message.reply_text(
            "Извините, произошла ошибка при обработке вашего запроса. "
            "Пожалуйста, попробуйте позже."
        )


async def error_handler(update: Update, context):
    """Обработчик ошибок"""
    await send_to_logger("error", f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "Произошла ошибка. Пожалуйста, попробуйте позже."
        )


# Глобальная переменная для application
bot_application = None


async def handle_health(request):
    """Health check endpoint"""
    return web.json_response({"status": "healthy", "service": "bot"})


async def handle_webhook(request):
    """Webhook endpoint для Telegram"""
    try:
        update_data = await request.json()
        update = Update.de_json(update_data, bot_application.bot)

        # Обрабатываем update через application
        await bot_application.process_update(update)

        return web.json_response({"status": "ok"})
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        return web.json_response({"error": "internal server error"}, status=500)


def main():
    """Основная функция"""
    global bot_application

    try:
        # Создаем aiohttp приложение
        app = web.Application()
        app.router.add_get('/health', handle_health)
        app.router.add_post('/webhook', handle_webhook)

        # Создаем Telegram application
        bot_application = Application.builder().token(TELEGRAM_TOKEN).build()
        bot_application.add_handler(CommandHandler("start", start))
        bot_application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        bot_application.add_error_handler(error_handler)

        # Инициализируем бота
        asyncio.run(bot_application.initialize())

        # Serverless контейнеры автоматически устанавливают переменную PORT
        port = int(os.getenv('PORT', 8080))

        print(f"Бот запускается на порту {port}...")
        print("Health check: GET /health")
        print("Webhook: POST /webhook")

        # Запускаем сервер
        web.run_app(app, host='0.0.0.0', port=port)

    except Exception as e:
        print(f"Failed to start bot: {str(e)}")


if __name__ == "__main__":
    main()
