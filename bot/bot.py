import time
import json
import os
import asyncio
import aiohttp
from http.server import HTTPServer, BaseHTTPRequestHandler

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
        orchestrator = ORCHESTRATOR_ADDRESS + '/log'
        async with aiohttp.ClientSession() as session:
            async with session.post(
                orchestrator, json=log_message
            ) as response:
                await response.text()
    except Exception as e:
        print(f"Error when send log: {str(e)}")
        return False


class TelegramBot:
    async def ask_gpt(self, question):
        query = {"question": question}

        try:
            await send_to_logger(
                "info",
                f"Sending request to orchestrator: "
                f"{ORCHESTRATOR_ADDRESS}/ask_gpt"
            )
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    ORCHESTRATOR_ADDRESS + '/ask_gpt',
                    json=query,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    gpt_answer = data['gpt_answer']
                    await send_to_logger(
                        "info",
                        f"Got response from orchestrator: "
                        f"{len(gpt_answer)} chars"
                    )
        except asyncio.TimeoutError:
            await send_to_logger("error", "Orchestrator request timeout")
            return None
        except aiohttp.ClientConnectionError:
            await send_to_logger("error", "Cannot connect to orchestrator")
            return None
        except aiohttp.ClientError as e:
            await send_to_logger("error", f"Ошибка при запросе к серверу: {e}")
            return None
        except Exception as e:
            await send_to_logger("error", f"Unexpected error: {e}")
            return None

        return gpt_answer


yandex_bot = TelegramBot()


async def start(update: Update, context):
    """
    Обработчик команды /start
    """
    try:
        await update.message.reply_text(
            "Привет! Я бот для работы с Yandex GPT. "
            "Просто напиши мне свой вопрос"
        )
    except Exception as e:
        await send_to_logger("error", f"Error in start handler: {str(e)}")


async def handle_message(update: Update, context):
    """Обработка текстовых сообщений"""
    try:
        user_message = update.message.text
        await send_to_logger(
            "info", f"Processing user message: {user_message}"
        )

        if not user_message.strip():
            await send_to_logger("warning", "Empty message received")
            await update.message.reply_text("Пожалуйста, введите вопрос")
            return

        # Показываем статус "печатает"
        await send_to_logger("info", "Sending typing action")
        await bot_application.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )

        await send_to_logger("info", "Calling GPT service")
        start_time = time.time()

        try:
            response = await yandex_bot.ask_gpt(user_message)
        except Exception as gpt_error:
            await send_to_logger(
                "error", f"Error in GPT call: {str(gpt_error)}"
            )
            response = None

        end_time = time.time()
        await send_to_logger(
            "info", f"GPT response time: {end_time - start_time:.2f}s"
        )

        if response is None:
            await send_to_logger("error", "GPT returned None response")
            await update.message.reply_text(
                "Сервис временно недоступен. Попробуйте ещё раз позже."
            )
        else:
            await send_to_logger("info", "Sending response to user")
            await update.message.reply_text(response)

    except Exception as e:
        await send_to_logger(
            "error", f"Error handling message: {str(e)}"
        )
        try:
            await update.message.reply_text(
                "Извините, произошла ошибка при обработке вашего запроса. "
                "Пожалуйста, попробуйте позже."
            )
        except Exception as reply_error:
            await send_to_logger(
                "error", f"Error sending error message: {str(reply_error)}"
            )


async def error_handler(update: Update, context):
    """Обработчик ошибок"""
    try:
        await send_to_logger(
            "error", f"Update {update} caused error {context}"
        )
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "Произошла ошибка. Пожалуйста, попробуйте позже."
            )
    except Exception as e:
        await send_to_logger(
            "error", f"Error in error handler: {str(e)}"
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
        """Health check endpoint для serverless контейнера"""
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
                try:
                    # Создаем новый event loop для обработки
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(self._process_update(update))
                    finally:
                        try:
                            loop.close()
                        except Exception:
                            pass
                except Exception as e:
                    print(f"Error in event loop: {str(e)}")

                self._send_json_response({"status": "ok"})

            except Exception as e:
                print(f"Error processing webhook: {str(e)}")
                self._send_json_response(
                    {"error": "internal server error"}, status=500
                )
        else:
            self._send_json_response({"error": "not found"}, status=404)

    async def _process_update(self, update: Update):
        """Обработка update от Telegram"""
        try:
            await send_to_logger(
                "info", f"Processing update: {update.update_id}"
            )
            if update and update.message:
                await send_to_logger(
                    "info",
                    f"Message from user {update.message.from_user.id}: "
                    f"{update.message.text}"
                )
                if (update.message.text and
                        update.message.text.startswith('/start')):
                    await send_to_logger("info", "Processing /start command")
                    await start(update, None)
                elif update.message.text:
                    await send_to_logger(
                        "info",
                        f"Processing text message: "
                        f"{update.message.text[:100]}..."
                    )
                    await handle_message(update, None)
            else:
                await send_to_logger(
                    "warning", f"Update without message: {update}"
                )
        except Exception as e:
            await send_to_logger(
                "error", f"Error processing update: {str(e)}"
            )
            if update:
                try:
                    await error_handler(update, None)
                except Exception as handler_error:
                    await send_to_logger(
                        "error",
                        f"Error in error handler: {str(handler_error)}"
                    )

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

        print(f"Бот запускается на порту {port}...")
        print("Health check: GET /health")
        print("Webhook: POST /webhook")

        httpd.serve_forever()

    except Exception as e:
        print(f"Failed to start bot: {str(e)}")


if __name__ == "__main__":
    main()
