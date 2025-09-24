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
    await logger("orchestrator", "info", f"Requesting moderator for question: {question[:100]}...")
    start_time = time.time()
    async with aiohttp.ClientSession() as session:
        async with session.post(ADDRESSES['MODERATOR_ADDRESS'], json={'question': question}) as response:
            response.raise_for_status()
            data = await response.json()
            end_time = time.time()
            await logger("orchestrator", "info", f"Moderator response time: {end_time - start_time:.2f}s, result: {data['is_safe']}")
            return data['is_safe']


async def _request_rag(question):
    await logger("orchestrator", "info", f"Requesting RAG for question: {question[:100]}...")
    start_time = time.time()
    async with aiohttp.ClientSession() as session:
        async with session.post(ADDRESSES['RAG_ADDRESS'], json={'question': question}) as response:
            response.raise_for_status()
            data = await response.json()
            end_time = time.time()
            context = data['context']
            await logger("orchestrator", "info", f"RAG response time: {end_time - start_time:.2f}s, context length: {len(context)}")
            return context


async def request_gpt(user, system=None):
    await logger("orchestrator", "info", f"Requesting GPT for user: {user[:100]}..., system: {system[:100] if system else 'None'}...")
    if system is None:
        data = {'user': user}
    else:
        data = {'user': user, 'system': system}

    start_time = time.time()
    async with aiohttp.ClientSession() as session:
        async with session.post(ADDRESSES['YANDEX_GPT_ADDRESS'], json=data) as response:
            response.raise_for_status()
            result = await response.json()
            end_time = time.time()
            gpt_answer = result['gpt_answer']
            await logger("orchestrator", "info", f"GPT response time: {end_time - start_time:.2f}s, answer length: {len(gpt_answer)}")
            return result


async def ask_gpt_pipeline(question):
    await logger("orchestrator", "info", f"Starting GPT pipeline for question: {question[:100]}...")
    pipeline_start = time.time()

    is_safe = await _request_moderator(question)
    if not is_safe:
        await logger("orchestrator", "warning", "Question failed moderation")
        return {'gpt_answer': 'Ваш вопрос не прошел модерацию. Попробуйте по другому сформулировать вопрос.'}

    context = await _request_rag(question)
    await logger("orchestrator", "info", f"Got context from RAG, length: {len(context)}")

    gpt_response = await request_gpt(
        system=f"""
        Контекст: {context}
        Используйте контекст, чтобы ответить на вопрос.
        Если контекст не соответствует вопросу, то не используйте его, и ответь на вопрос так, как будто контекста не было.
        Если Контекста не достаточно для полного ответа, то обязательно дополни ответ своими знаниями.""",
        user=question
    )

    pipeline_end = time.time()
    await logger("orchestrator", "info", f"GPT pipeline completed in {pipeline_end - pipeline_start:.2f}s")
    return gpt_response


async def handle_get(request):
    """Health check и диагностические endpoints для serverless контейнера"""
    if request.path == '/health':
        return web.json_response({"status": "healthy", "service": "orchestrator"})
    elif request.path == '/check-connections':
        # Диагностический endpoint для проверки связей с другими сервисами
        results = {}

        # Проверяем Logger
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(ADDRESSES['LOGGER_ADDRESS'] + '/health') as response:
                    results['logger'] = {
                        'url': ADDRESSES['LOGGER_ADDRESS'],
                        'status': 'ok' if response.status == 200 else 'error',
                        'status_code': response.status
                    }
        except Exception as e:
            results['logger'] = {
                'url': ADDRESSES['LOGGER_ADDRESS'],
                'status': 'error',
                'error': str(e)
            }

        # Проверяем Moderator
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(ADDRESSES['MODERATOR_ADDRESS'] + '/health') as response:
                    results['moderator'] = {
                        'url': ADDRESSES['MODERATOR_ADDRESS'],
                        'status': 'ok' if response.status == 200 else 'error',
                        'status_code': response.status
                    }
        except Exception as e:
            results['moderator'] = {
                'url': ADDRESSES['MODERATOR_ADDRESS'],
                'status': 'error',
                'error': str(e)
            }

        # Проверяем Yandex GPT
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(ADDRESSES['YANDEX_GPT_ADDRESS'] + '/health') as response:
                    results['yandex_gpt'] = {
                        'url': ADDRESSES['YANDEX_GPT_ADDRESS'],
                        'status': 'ok' if response.status == 200 else 'error',
                        'status_code': response.status
                    }
        except Exception as e:
            results['yandex_gpt'] = {
                'url': ADDRESSES['YANDEX_GPT_ADDRESS'],
                'status': 'error',
                'error': str(e)
            }

        # Проверяем RAG
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(ADDRESSES['RAG_ADDRESS'] + '/health') as response:
                    results['rag'] = {
                        'url': ADDRESSES['RAG_ADDRESS'],
                        'status': 'ok' if response.status == 200 else 'error',
                        'status_code': response.status
                    }
        except Exception as e:
            results['rag'] = {
                'url': ADDRESSES['RAG_ADDRESS'],
                'status': 'error',
                'error': str(e)
            }

        return web.json_response({
            "status": "diagnostic_complete",
            "service": "orchestrator",
            "connections": results
        })
    else:
        return web.json_response({"error": "not found"}, status=404)

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
            name = query.get('name', 'unknown')
            level = query.get('level', 'info')
            message = query.get('message', '')
            response = await logger(name, level, message)
            return web.json_response(response)
        case _:
            return web.json_response({"status": "error", "message": "Endpoint not found. Use /"}, status=404)


def main():
    time.sleep(5)
    # Serverless контейнеры автоматически устанавливают переменную PORT
    port = int(os.getenv('PORT', 8003))

    app = web.Application()
    app.router.add_get('/health', handle_get)
    app.router.add_get('/check-connections', handle_get)
    app.router.add_post('/', handle_post)
    app.router.add_post('/{path:.*}', handle_post)

    import requests
    requests.post(ADDRESSES['LOGGER_ADDRESS'],
                  json={'name': 'orchestrator', 'level': 'info', 'message': f"Orchestrator is running on port {port}"})
    requests.post(ADDRESSES['LOGGER_ADDRESS'],
                  json={'name': 'orchestrator', 'level': 'info', 'message': "Health check: GET /health"})

    web.run_app(app, host='', port=port)


if __name__ == '__main__':
    main()
