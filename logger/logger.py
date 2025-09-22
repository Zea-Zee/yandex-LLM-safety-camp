import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


class LoggerRequestHandler(BaseHTTPRequestHandler):
    def _send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _retrieve_message(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            json_data = json.loads(post_data.decode('utf-8'))
        except Exception as e:
            return 'error', f'Error parsing request: {str(e)}'

        message = json_data.get('message', 'Missing required field: message')
        level = json_data.get('level', f'Missing required field: level. Message: {message}')

        return level, message

    def do_POST(self):
        if self.path != '/':
            logger.error("Endpoint not found. Use /")
            response = {
                "status": "error",
                "message": "Endpoint not found. Use /"
            }
            self._send_json_response(response, 404)
            return

        level, message = self._retrieve_message()
        print(level, message)
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
                logger.error(f'Unknown log level "{level}". Message: {message}')
                level = 'error'
        response = {
            "status": "success",
            "logged_level": level,
            "message": "Message logged successfully"
        }
        self._send_json_response(response, 200)


def main():
    port = 8020
    server_address = ('', port)
    httpd = HTTPServer(server_address, LoggerRequestHandler)
    logger.info(f'Logger running on http://localhost:{port}')

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info('Логгер остановлен')
    except Exception as e:
        logger.error(f"Ошибка при работе сервера: {str(e)}")


if __name__ == "__main__":
    main()
