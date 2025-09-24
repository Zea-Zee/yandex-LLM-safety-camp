import json
import aiohttp
import time
import os
from aiohttp import web

from settings import ADDRESSES


async def logger(name, level, message):
    async with aiohttp.ClientSession() as session:
        async with session.post(ADDRESSES['LOGGER_ADDRESS'], json={'name': name, 'level': level, 'message': message}) as response:
            return await response.json()


async def _request_moderator(question):
    async with aiohttp.ClientSession() as session:
        async with session.post(ADDRESSES['MODERATOR_ADDRESS'], json={'question': question}) as response:
            response.raise_for_status()
            data = await response.json()
            return data['is_safe']


async def _request_rag(question):
    async with aiohttp.ClientSession() as session:
        async with session.post(ADDRESSES['RAG_ADDRESS'], json={'question': question}) as response:
            response.raise_for_status()
            data = await response.json()
            return data['context']


async def request_gpt(user, system=None):
    if system is None:
        data = {'user': user}
    else:
        data = {'user': user, 'system': system}

    async with aiohttp.ClientSession() as session:
        async with session.post(ADDRESSES['YANDEX_GPT_ADDRESS'], json=data) as response:
            response.raise_for_status()
            return await response.json()


async def ask_gpt_pipeline(question):
    is_safe = await _request_moderator(question)
    if not is_safe:
        return {'gpt_answer': 'Ваш вопрос не прошел модерацию. Попробуйте по другому сформулировать вопрос.'}

    context = await _request_rag(question)
    gpt_response = await request_gpt(
        system=f"""
        Контекст: {context}
        Используйте контекст, чтобы ответить на вопрос.
        Если контекст не соответствует вопросу, то не используйте его, и ответь на вопрос так, как будто контекста не было.
        Если Контекста не достаточно для полного ответа, то обязательно дополни ответ своими знаниями.""",
        user=question
    )

    return gpt_response


async def handle_health(request):
    """Health check endpoint"""
    return web.json_response({"status": "healthy", "service": "orchestrator"})


async def handle_post(request):
    try:
        query = await request.json()
    except:
        return web.json_response({"status": "error", "message": "Invalid JSON"}, status=400)

    match request.path:
        case '/ask_gpt':
            gpt_answer = await ask_gpt_pipeline(**query)
            return web.json_response(gpt_answer)
        case '/gpt_moderator':
            gpt_answer = await request_gpt(**query)
            return web.json_response(gpt_answer)
        case '/log':
            response = await logger(**query)
            return web.json_response(response)
        case _:
            return web.json_response({"status": "error", "message": "Endpoint not found. Use /"}, status=404)


def main():
    # Serverless контейнеры автоматически устанавливают переменную PORT
    port = int(os.getenv('PORT', 8003))

    app = web.Application()
    app.router.add_get('/health', handle_health)
    app.router.add_post('/', handle_post)
    app.router.add_post('/{path:.*}', handle_post)

    # Простая инициализация логгера
    try:
        import requests
        requests.post(ADDRESSES['LOGGER_ADDRESS'],
                      json={'name': 'orchestrator', 'level': 'info', 'message': f"Orchestrator is running on port {port}"})
    except Exception as e:
        print(f"Warning: Could not connect to logger: {e}")

    web.run_app(app, host='0.0.0.0', port=port)


if __name__ == '__main__':
    main()
