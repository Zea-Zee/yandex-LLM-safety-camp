import json
from http.server import HTTPServer, BaseHTTPRequestHandler

import requests

from settings import ADDRESSES

logger_client = requests.Session()
logger_client.headers.update({'Content-Type': 'application/json'})


def logger(level, message):
    return requests.post(ADDRESSES['LOGGER_ADDRESS'], json={'level': level, 'message': message})


def _request_moderator(question):
    response = requests.post(ADDRESSES['MODERATOR_ADDRESS'], json={'question': question})
    response.raise_for_status()
    is_safe = response.json()['is_safe']
    return is_safe


def _request_rag(question):
    response = requests.get(ADDRESSES['RAG_ADDRESS'], json={'question': question})
    response.raise_for_status()
    context = response.json()['context']
    return context


def request_gpt(user, system=None):
    if system is None:
        data = {'user': user}
    else:
        data = {'user': user, 'system': system}
    response = requests.post(ADDRESSES['YANDEX_GPT_ADDRESS'], json=data)
    response.raise_for_status()
    return response.json()


def ask_gpt_pipeline(question):
    is_safe = _request_moderator(question)
    if not is_safe:
        return {'gpt_answer': 'Ваш вопрос не прошел модерацию. Попробуйте по другому сформулировать вопрос.'}

    context = _request_rag(question)
    gpt_response = request_gpt(
        system=f"""
        Контекст: {context} 
        Используйте контекст, чтобы ответить на вопрос. 
        Если контекст не соответствует вопросу, то не используйте его,
        и ответь на вопрос так, как будто контекста не было.
        Если Контекста не достаточно для полного ответа, то обязательно дополни ответ своими знаниями.""",
        user=question
    )

    return gpt_response


class OrchestratorRequestHandler(BaseHTTPRequestHandler):
    def _retrieve_message(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        query = json.loads(post_data.decode('utf-8'))
        return query

    def _send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _set_response(self, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def do_POST(self):
        query = self._retrieve_message()
        match self.path:
            case '/ask_gpt':
                gpt_answer = ask_gpt_pipeline(**query)
                self._send_json_response(gpt_answer)
            case '/gpt_moderator':
                print(query)
                gpt_answer = request_gpt(**query)
                self._send_json_response(gpt_answer)
            case '/log':
                response = logger(**query)
                self._send_json_response(response)
            case _:
                self._send_json_response({"status": "error", "message": "Endpoint not found. Use /"}, 404)


def main():
    port = 8003
    server_address = ('', port)
    httpd = HTTPServer(server_address, OrchestratorRequestHandler)
    logger('info', f"Orchestrator is running on port {port}")

    httpd.serve_forever()


if __name__ == '__main__':
    main()
