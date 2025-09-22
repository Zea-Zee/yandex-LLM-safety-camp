import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


class LoggerRequestHandler(BaseHTTPRequestHandler):
    def _set_response(self, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def _retrieve_message(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                return 'error', 'Empty request body'

            post_data = self.rfile.read(content_length)
            json_data = json.loads(post_data.decode('utf-8'))

            # Проверяем наличие обязательного поля 'message'
            if 'message' not in json_data:
                return 'error', 'Missing required field: message'

            return json_data.get('level', 'info'), json_data.get('message', 'No message provided')
        except Exception as e:
            return 'error', f'Error parsing request: {str(e)}'

    def do_POST(self):
        if self.path != '/':
            self._set_response(404)
            response = {
                "status": "error",
                "message": "Endpoint not found. Use /"
            }
            self.wfile.write(json.dumps(response).encode('utf-8'))
            return

        level, message = self._retrieve_message()

        # Если произошла ошибка при парсинге (level = 'error')
        if level == 'error':
            logger.error(f'Request error: {message}')
            self._set_response(400)
            response = {
                "status": "error",
                "message": message
            }
            self.wfile.write(json.dumps(response).encode('utf-8'))
            return

        match level:
            case 'debug':
                logger.debug(message)
            case 'info':
                logger.info(message)
            case 'warning':
                logger.warning(message)
            case 'error':
                logger.error(message)
            case 'critical':
                logger.critical(message)
            case _:
                logger.error(f'Unknown log level {level}. Message: {message}')
                level = 'error'

        self._set_response(200)
        response = {
            "status": "success",
            "logged_level": level,
            "message": "Message logged successfully"
        }
        self.wfile.write(json.dumps(response).encode('utf-8'))


def main():
    port = 8020
    server_address = ("localhost", port)
    httpd = HTTPServer(server_address, LoggerRequestHandler)
    logger.info("Server running on http://localhost:%d", port)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Сервер остановлен")
    except Exception as e:
        logger.error("Ошибка при работе сервера: %s", e)


if __name__ == "__main__":
    main()