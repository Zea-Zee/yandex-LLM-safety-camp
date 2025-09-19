import logging
import time

import jwt
import requests

from settings import YANDEXGPT_ADDRESS, MODERATOR_ADDRESS, RAG_ADDRESS

from http.server import HTTPServer, BaseHTTPRequestHandler
import json

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self):
        self.yandex_gpt_adress = YANDEXGPT_ADDRESS
        self.moderator_address = MODERATOR_ADDRESS
        self.rag_address = RAG_ADDRESS

    def check_message(self, question):
        """ Проверка сообщения на безопасность """
        data_moderator = {
            "question": question
        }

        try:
            response = requests.post(self.moderator_address, json=data_moderator)
            response.raise_for_status()  # Проверяем на ошибки HTTP
            is_safe = response.json()['is_safe']
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе к серверу: {e}")
            return None

        return is_safe
    
    def rag_request(self, question):
        data_rag = {
            "question": question
        }

        try:
            response = requests.post(self.rag_address, json=data_rag)
            response.raise_for_status()
            context = response.json()['context']
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе к серверу: {e}")
            return None

        return context
    
    def gpt_request(self, question):
        data_yandex_gpt = {
            "message": {
                "user": question
            }
        }

        try:
            response = requests.post(self.yandex_gpt_adress, json=data_yandex_gpt)
            response.raise_for_status()
            gpt_answer = response.json()['gpt_answer']
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе к серверу: {e}")
            return None

        return gpt_answer
    
    def request_processing(self, question):
        is_safe = self.check_message(question)
        if is_safe == False:
            result = "Ваш вопрос не прошел модерацию. Попробуйте по другому сформулировать вопрос."
            return result

        context = self.rag_request(question)
        question_w_context = 'Конеткст: ' + context + '\n\nВопрос: ' + question
        gpt_final_answer = self.gpt_request(question_w_context)

        return gpt_final_answer

class OrchestratorRequestHandler(BaseHTTPRequestHandler):
    def __init__(self, request, client_address, server):
        self.orchestrator = Orchestrator()
        super().__init__(request, client_address, server)
        
    def _send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        json_data = json.loads(post_data.decode('utf-8'))
        gpt_answer = self.orchestrator.request_processing(json_data['question']) #(json_data['messages'])

        response = {
            "gpt_answer": gpt_answer
        }

        self._send_json_response(response)

def main():
    server_adress = ('', 8003)
    httpd = HTTPServer(server_adress, OrchestratorRequestHandler)
    print("Orchestrator is running on port 8003")
    
    httpd.serve_forever()

if __name__ == '__main__':
    main()
