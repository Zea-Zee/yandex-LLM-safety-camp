import time
import jwt
import requests
from settings import SERVICE_ACCOUNT_ID, KEY_ID, PRIVATE_KEY, FOLDER_ID


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
                timeout=10
            )

            if response.status_code != 200:
                raise Exception(f"Ошибка генерации токена: {response.text}")

            token_data = response.json()
            self.iam_token = token_data['iamToken']
            # На 100 секунд меньше срока действия
            self.token_expires = now + 3500

            return self.iam_token

        except Exception as e:
            print(f"Error generating IAM token: {str(e)}")
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

    def ask_gpt(self, dict_messages, stream=False):
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
                    "stream": stream,
                    "temperature": 0.6,
                    "maxTokens": 2000
                },
                "messages": messages
            }

            url = ('https://llm.api.cloud.yandex.net/foundationModels/v1/'
                   'completion')

            if stream:
                return self._stream_response(url, headers, data)
            else:
                response = requests.post(
                    url,
                    headers=headers,
                    json=data,
                    timeout=30
                )

                if response.status_code != 200:
                    print(f"Yandex GPT API error: {response.text}")
                    raise Exception(f"Ошибка API: {response.status_code}")

                result = response.json()['result']['alternatives'][0]
                return result['message']['text']

        except Exception as e:
            print(f"Error in ask_gpt: {str(e)}")
            raise

    def _stream_response(self, url, headers, data):
        """Обработка streaming ответа от Yandex GPT"""
        import json

        response = requests.post(
            url,
            headers=headers,
            json=data,
            stream=True,
            timeout=30
        )

        if response.status_code != 200:
            print(f"Yandex GPT API error: {response.text}")
            raise Exception(f"Ошибка API: {response.status_code}")

        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data_line = line[6:]  # Убираем 'data: '
                    if data_line.strip() == '[DONE]':
                        break
                    try:
                        chunk = json.loads(data_line)
                        if ('result' in chunk and
                                'alternatives' in chunk['result']):
                            alternatives = chunk['result']['alternatives']
                            if (alternatives and
                                    'message' in alternatives[0]):
                                message = alternatives[0]['message']
                                if 'text' in message:
                                    yield message['text']
                    except json.JSONDecodeError:
                        continue

# Простой класс для работы с Yandex GPT API
