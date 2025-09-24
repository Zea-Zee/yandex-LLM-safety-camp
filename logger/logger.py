import json
import logging
import time
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(name)s - %(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


class LoggerRequestHandler(BaseHTTPRequestHandler):
    def _send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        """Health check endpoint для serverless контейнера"""
        if self.path == '/health':
            self._send_json_response({"status": "healthy", "service": "logger"})
        else:
            self._send_json_response({"error": "not found"}, status=404)

    def _retrieve_message(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            json_data = json.loads(post_data.decode('utf-8'))
        except Exception as e:
            return 'error', f'Error parsing request: {str(e)}', 'unknown'  #-------

        message = json_data.get('message', 'Missing required field: message')
        level = json_data.get('level', f'Missing required field: level. Message: {message}')
        name = json_data.get('name', f'Missing required field: name. Message: {message}')

        return level, message, name  #-------

    def do_POST(self):
        # Принимаем POST запросы на любой путь
        level, message, name = self._retrieve_message()  #-------
        sender_logger = logging.getLogger(name)  #-------

        match level:
            case 'debug':
                sender_logger.debug(message)  #-------
            case 'info':
                sender_logger.info(message)  #-------
            case 'warning':
                sender_logger.warning(message)  #-------
            case 'error':
                sender_logger.error(message)  #-------
            case 'critical':
                sender_logger.critical(message)  #-------
            case _:
                sender_logger.error(f'Unknown log level "{level}". Message: {message}')  #-------
                level = 'error'
        response = {
            "status": "success",
            "logged_level": level,
            "message": "Message logged successfully"
        }
        self._send_json_response(response, 200)


def main():
    # Serverless контейнеры автоматически устанавливают переменную PORT
    port = int(os.getenv('PORT', 8020))
    server_address = ('', port)
    httpd = HTTPServer(server_address, LoggerRequestHandler)
    logger.info(f'Logger running on port {port}')
    logger.info('Health check: GET /health')

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info('Логгер остановлен')
    except Exception as e:
        logger.error(f"Ошибка при работе сервера: {str(e)}")


if __name__ == "__main__":
    main()
