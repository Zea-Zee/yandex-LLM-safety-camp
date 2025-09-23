import logging
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

import requests
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler, filters
)

from settings import TELEGRAM_TOKEN, ORCHESTRATOR_ADDRESS
import os

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self):
        self.orchestrator_address = ORCHESTRATOR_ADDRESS

    def ask_gpt(self, question):
        data = {
            "question": question
        }

        try:
            response = requests.post(self.orchestrator_address, json=data)
            response.raise_for_status()
            gpt_answer = response.json()['gpt_answer']
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при запросе к серверу: {e}")
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


class BotRequestHandler(BaseHTTPRequestHandler):
    def __init__(self, request, client_address, server):
        super().__init__(request, client_address, server)

    def _send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        """Health check endpoint"""
        if self.path == '/health':
            self._send_json_response({"status": "healthy", "service": "bot"})
        else:
            self._send_json_response({"error": "not found"}, status=404)

    def do_POST(self):
        """Webhook endpoint для Telegram"""
        if self.path == '/webhook':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                update_data = json.loads(post_data.decode('utf-8'))

                # Создаем Update объект из данных webhook
                update = Update.de_json(update_data, bot_application.bot)

                # Обрабатываем update асинхронно
                import asyncio
                asyncio.create_task(self._process_update(update))

                self._send_json_response({"status": "ok"})

            except Exception as e:
                logger.error(f"Error processing webhook: {str(e)}")
                self._send_json_response(
                    {"error": "internal server error"}, status=500
                )
        else:
            self._send_json_response({"error": "not found"}, status=404)

    async def _process_update(self, update: Update):
        """Обработка update от Telegram"""
        try:
            if update.message:
                if (update.message.text and
                        update.message.text.startswith('/start')):
                    await start(update, None)
                elif update.message.text:
                    await handle_message(update, None)
        except Exception as e:
            logger.error(f"Error processing update: {str(e)}")
            await error_handler(update, None)

    def log_message(self, format, *args):
        """Отключаем стандартное логирование HTTP запросов"""
        pass


# Глобальная переменная для application
bot_application = None


def main():
    """Основная функция"""
    global bot_application

    try:
        # Создаем приложение для обработки сообщений
        bot_application = Application.builder().token(TELEGRAM_TOKEN).build()

        # Добавляем обработчики
        bot_application.add_handler(CommandHandler("start", start))
        bot_application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        )
        bot_application.add_error_handler(error_handler)

        # Инициализируем бота асинхронно
        import asyncio
        asyncio.run(bot_application.initialize())

        # Создаем HTTP сервер
        # Serverless контейнеры автоматически устанавливают переменную PORT
        port = int(os.getenv('PORT', 8080))
        server_address = ('', port)
        httpd = HTTPServer(server_address, BotRequestHandler)

        logger.info(f"Бот запускается на порту {port}...")
        logger.info("Health check: GET /health")
        logger.info("Webhook: POST /webhook")

        httpd.serve_forever()

    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}")


if __name__ == "__main__":
    main()
