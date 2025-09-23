import time
import os

import jwt
import requests

from settings import SERVICE_ACCOUNT_ID, KEY_ID, PRIVATE_KEY, FOLDER_ID, LOGGER_ADDRESS

from http.server import HTTPServer, BaseHTTPRequestHandler
import json

def send_to_logger(level, message):
    log_message = {
        "name": "GPT",
        "level": level,
        "message": message
    }
    try:
        response = requests.post(LOGGER_ADDRESS, json=log_message)
    except Exception as e:
        print(f"Error when send log: {str(e)}")
        return False

class YandexGPTApi:
    def __init__(self):
        self.searcher = None
        self.iam_token = None
        self.token_expires = 0

    def get_iam_token(self):
        """Получение IAM-токена (с кэшированием на 1 час)"""
        if self.iam_token and time.time() < self.token_expires:
            return self.iam_token

        try:
            now = int(time.time())
            payload = {
                'aud': 'https://iam.api.cloud.yandex.net/iam/v1/tokens',
                'iss': SERVICE_ACCOUNT_ID,
                'iat': now,
                'exp': now + 3600
            }

            encoded_token = jwt.encode(
                payload,
                PRIVATE_KEY,
                algorithm='PS256',
                headers={'kid': KEY_ID}
            )

            response = requests.post(
                'https://iam.api.cloud.yandex.net/iam/v1/tokens',
                json={'jwt': encoded_token},
                timeout=30  # Увеличиваем timeout
            )

            if response.status_code != 200:
                raise Exception(f"Ошибка генерации токена: {response.text}")

            token_data = response.json()
            self.iam_token = token_data['iamToken']
            self.token_expires = now + 3500  # На 100 секунд меньше срока действия

            send_to_logger("info", "IAM token generated successfully")
            return self.iam_token

        except Exception as e:
            send_to_logger("error", f"Error generating IAM token: {str(e)}")
            raise

    def transform_messages(self, input_dict):
        result = []
        if 'system' in input_dict:
            result.append({
                "role": "system",
                "text": input_dict['system']
            })
        if 'user' in input_dict:
            result.append({
                "role": "user",
                "text": input_dict['user']
            })
        return result

    def ask_gpt(self, dict_messages):
        try:
            iam_token = self.get_iam_token()

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {iam_token}',
                'x-folder-id': FOLDER_ID
            }

            messages = self.transform_messages(dict_messages)

            data = {
                "modelUri": f"gpt://{FOLDER_ID}/yandexgpt-lite",
                "completionOptions": {
                    "stream": False,
                    "temperature": 0.6,
                    "maxTokens": 1000  # Уменьшаем для ускорения
                },
                "messages": messages
            }

            response = requests.post(
                'https://llm.api.cloud.yandex.net/foundationModels/v1/completion',
                headers=headers,
                json=data,
                timeout=60  # Увеличиваем timeout для GPT API
            )

            if response.status_code != 200:
                send_to_logger("error", f"Yandex GPT API error: {response.text}")
                raise Exception(f"Ошибка API: {response.status_code}")

            return response.json()['result']['alternatives'][0]['message']['text']

        except Exception as e:
            send_to_logger("error", f"Error in ask_gpt: {str(e)}")
            raise

class YandexGPTRequestHandler(BaseHTTPRequestHandler):
    def __init__(self, request, client_address, server):
        self.yandex_gpt = YandexGPTApi()
        super().__init__(request, client_address, server)

    def _send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        """Health check endpoint для serverless контейнера"""
        if self.path == '/health':
            self._send_json_response({"status": "healthy", "service": "yandex_gpt"})
        else:
            self._send_json_response({"error": "not found"}, status=404)

    def _retrieve_message(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        query = json.loads(post_data.decode('utf-8'))
        user = query['user']
        system = query.get('system', None)
        return query

    def do_POST(self):
        try:
            json_data = self._retrieve_message()
        except Exception as e:
            send_to_logger("error", "Failed to read or parse request body")
            self._send_json_response({"error": "invalid request body"}, status=400)
            return

        try:
            gpt_answer = self.yandex_gpt.ask_gpt(json_data)
        except Exception as e:
            send_to_logger("error", "Moderator check_question failed")
            self._send_json_response({"error": "internal server error"}, status=500)
            return

        response = {
            "gpt_answer": gpt_answer
        }

        try:
            self._send_json_response(response)
        except Exception as e:
            send_to_logger("error", "Failed to send response")
            self._send_json_response({"error": "internal server error"}, status=500)
            return

def main():
    time.sleep(5)
    # Serverless контейнеры автоматически устанавливают переменную PORT
    port = int(os.getenv('PORT', 8000))
    server_address = ('', port)

    # Предварительно инициализируем IAM токен
    try:
        gpt_api = YandexGPTApi()
        gpt_api.get_iam_token()
        send_to_logger("info", "IAM token pre-initialized successfully")
    except Exception as e:
        send_to_logger("warning", f"Failed to pre-initialize IAM token: {str(e)}")

    httpd = HTTPServer(server_address, YandexGPTRequestHandler)
    send_to_logger("info", f"YandexGPT is running on port {port}")
    send_to_logger("info", "Health check: GET /health")

    httpd.serve_forever()

if __name__ == '__main__':
    main()
