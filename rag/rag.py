import json
import os
import tempfile
from http.server import HTTPServer, BaseHTTPRequestHandler
from io import BytesIO
from typing import List, Dict
import requests
import time

import boto3
import PyPDF2
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from settings import S3_BUCKET, S3_PREFIX, S3_SECRET_KEY, S3_ACCESS_KEY, S3_ENDPOINT, ORCHESTRATOR_ADDRESS

def send_to_logger(level, message):
    log_message = {
        "name": "rag",
        "level": level,
        "message": message
    }
    try:
        print(f"DEBUG: ORCHESTRATOR_ADDRESS = {ORCHESTRATOR_ADDRESS}")
        orchestrator = ORCHESTRATOR_ADDRESS + '/log'
        print(f"DEBUG: orchestrator URL = {orchestrator}")
        response = requests.post(orchestrator, json=log_message)
    except Exception as e:
        print(f"Error when send log: {str(e)}")
        return False


# ======================
# PDF Utils
# ======================

def extract_text_from_pdf(pdf_file: BytesIO) -> str:
    """Извлекает текст из PDF файла, безопасно обрабатывая ошибки."""
    text = []
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
    except Exception as e:
        send_to_logger("error", f"Ошибка при чтении PDF: {e}")
    return "\n".join(text)


# ======================
# Document Processing
# ======================

def prepare_documents(local_files: List[str]) -> List[Document]:
    """Загружает локальные файлы и преобразует их в объекты Document."""
    docs = []
    for path in local_files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            if content.strip():
                docs.append(Document(page_content=content))
                send_to_logger("debug", f"Документ загружен: {path}")
        except Exception as e:
            send_to_logger("warning", f"Ошибка обработки документа {path}: {e}")

    if not docs:
        send_to_logger("info", "Нет валидных документов, создается заглушка.")
        docs = [Document(page_content="Нет доступных документов.")]
    return docs


def build_vectorstore(docs: List[Document]) -> FAISS:
    """Создает FAISS-векторное хранилище из документов."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(docs)
    send_to_logger("info", f"Создано {len(chunks)} чанков")

    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = FAISS.from_documents(chunks, embeddings)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    vectorstore.save_local(os.path.join(current_dir, "vectorstore_faiss"))
    send_to_logger("info", "Векторное хранилище сохранено локально.")
    return vectorstore


# ======================
# S3 Helper
# ======================

class S3Helper:
    """Инкапсулирует работу с S3: подключение, листинг и скачивание файлов."""

    def __init__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT,
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY,
            region_name="ru-central1",
        )
        send_to_logger("info", "S3 клиент инициализирован.")

    def list_objects(self) -> Dict:
        try:
            send_to_logger("info", "Получение списка объектов из S3...")
            return self.client.list_objects_v2(Bucket=S3_BUCKET, Prefix=S3_PREFIX)
        except Exception as e:
            send_to_logger("error", f"Ошибка подключения к S3: {e}")
            return {}

    def download_files(self, objects: Dict, tmpdir: str) -> List[str]:
        local_files = []
        for obj in objects.get("Contents", []):
            key = obj.get("Key")
            if not key or key.endswith("/"):
                continue
            if obj.get("Size", 0) == 0:
                continue

            ext = os.path.splitext(key)[1].lower()
            local_path = os.path.join(tmpdir, os.path.basename(key))

            try:
                if ext == ".pdf":
                    send_to_logger("info", f"Загрузка PDF из S3: {key}")
                    response = self.client.get_object(Bucket=S3_BUCKET, Key=key)
                    pdf_data = response["Body"].read()
                    pdf_text = extract_text_from_pdf(BytesIO(pdf_data))
                    if pdf_text.strip():
                        txt_path = local_path + ".txt"
                        with open(txt_path, "w", encoding="utf-8") as f:
                            f.write(pdf_text)
                        local_files.append(txt_path)
                        send_to_logger("debug", f"PDF сконвертирован в текст: {txt_path}")
                else:
                    send_to_logger("info", f"Загрузка файла из S3: {key}")
                    self.client.download_file(S3_BUCKET, key, local_path)
                    if os.path.getsize(local_path) > 0:
                        local_files.append(local_path)
                        send_to_logger("debug", f"Файл загружен: {local_path}")
            except Exception as e:
                send_to_logger("warning", f"Ошибка обработки {key}: {e}")

        send_to_logger("info", f"Загружено {len(local_files)} файлов из S3")
        return local_files


# ======================
# RAG Logic
# ======================

class RAGHelper:
    """Работа с векторным индексом и извлечение релевантных фрагментов."""

    def __init__(self):
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        vectorstore_path = os.path.join(current_dir, "vectorstore_faiss")

        # Всегда перестраиваем индекс при старте
        send_to_logger("info", "Инициализация векторного хранилища при старте сервера...")
        self.vectorstore = self._download_and_build_index()
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3})
        send_to_logger("info", "Векторное хранилище инициализировано и готово к работе")

    def _download_and_build_index(self) -> FAISS:
        s3 = S3Helper()

        # Сначала проверяем, есть ли готовое векторное хранилище в S3
        vectorstore_key = f"{S3_PREFIX}/vectorstore_faiss"
        try:
            send_to_logger("info", "Попытка загрузки готового векторного хранилища из S3...")

            # Проверяем, есть ли файлы векторного хранилища
            s3.client.head_object(Bucket=S3_BUCKET, Key=f"{vectorstore_key}/index.faiss")
            s3.client.head_object(Bucket=S3_BUCKET, Key=f"{vectorstore_key}/index.pkl")

            # Загружаем готовое хранилище
            s3.client.download_file(S3_BUCKET, f"{vectorstore_key}/index.faiss", "/tmp/index.faiss")
            s3.client.download_file(S3_BUCKET, f"{vectorstore_key}/index.pkl", "/tmp/index.pkl")

            embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            vectorstore = FAISS.load_local("/tmp", embeddings, allow_dangerous_deserialization=True)
            send_to_logger("info", "Готовое векторное хранилище загружено из S3")
            return vectorstore

        except Exception as e:
            send_to_logger("info", f"Готовое хранилище не найдено, создаем новое: {str(e)}")

        # Если готового нет, создаем новое
        objects = s3.list_objects()
        if "Contents" not in objects:
            send_to_logger("warning", "В S3 не найдено объектов, создается пустой индекс.")
            return self._build_empty_index()

        with tempfile.TemporaryDirectory() as tmpdir:
            local_files = s3.download_files(objects, tmpdir)
            vectorstore = self._build_index_from_files(local_files)

            # Сохраняем готовое хранилище в S3 для будущего использования
            try:
                send_to_logger("info", "Сохраняем векторное хранилище в S3...")
                vectorstore.save_local("/tmp/vectorstore_faiss")
                s3.client.upload_file("/tmp/vectorstore_faiss/index.faiss", S3_BUCKET, f"{vectorstore_key}/index.faiss")
                s3.client.upload_file("/tmp/vectorstore_faiss/index.pkl", S3_BUCKET, f"{vectorstore_key}/index.pkl")
                send_to_logger("info", "Векторное хранилище сохранено в S3")
            except Exception as e:
                send_to_logger("warning", f"Не удалось сохранить в S3: {str(e)}")

            return vectorstore

    def _build_empty_index(self) -> FAISS:
        """Создает пустое векторное хранилище с заглушкой"""
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        docs = [Document(page_content="Нет доступных документов.")]
        return FAISS.from_documents(docs, embeddings)

    def _build_index_from_files(self, local_files: List[str]) -> FAISS:
        """Строит индекс из локальных файлов"""
        docs = prepare_documents(local_files)
        return build_vectorstore(docs)

    def get_context_chunks(self, question: str) -> str:
        send_to_logger("info", f"Запрос на поиск контекста: '{question}'")
        docs = self.retriever.invoke(question)
        send_to_logger("info", f"Найдено {len(docs)} релевантных документов")
        return "\n\n".join(doc.page_content for doc in docs)


# ======================
# HTTP Request Handler
# ======================

class RAGRequestHandler(BaseHTTPRequestHandler):
    """Обработчик HTTP-запросов для взаимодействия с RAG."""

    def __init__(self, request, client_address, server):
        # Используем общий RAGHelper из сервера
        self.rag_helper = server.rag_helper
        super().__init__(request, client_address, server)

    def _send_json_response(self, data: Dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_GET(self):
        """Health check endpoint для serverless контейнера"""
        if self.path == '/health':
            self._send_json_response({"status": "healthy", "service": "rag", "ORCHESTRATOR_ADDRESS": ORCHESTRATOR_ADDRESS})
        else:
            self._send_json_response({"error": "not found"}, status=404)

    def _retrieve_question(self) -> str:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return ""
        post_data = self.rfile.read(length)
        try:
            json_data = json.loads(post_data.decode("utf-8"))
            return json_data.get("question", "")
        except json.JSONDecodeError:
            send_to_logger("warning", "Получен некорректный JSON-запрос.")
            return ""

    def do_POST(self):
        question = self._retrieve_question()
        if not question.strip():
            send_to_logger("warning", "Пустой вопрос получен в POST-запросе.")
            self._send_json_response({"error": "Вопрос не задан"}, status=400)
            return

        try:
            context_chunks = self.rag_helper.get_context_chunks(question)
            send_to_logger("info", f"Ответ сформирован, длина контекста: {len(context_chunks)} символов")
            self._send_json_response({"context": context_chunks})
        except Exception as e:
            send_to_logger("error", f"Ошибка при обработке запроса: {e}")
            self._send_json_response({"error": "Внутренняя ошибка сервера"}, status=500)


# ======================
# Custom HTTP Server
# ======================

class RAGHTTPServer(HTTPServer):
    """Кастомный HTTP сервер с предварительно инициализированным RAGHelper."""

    def __init__(self, server_address, RequestHandlerClass):
        # Инициализируем RAGHelper до запуска сервера
        self.rag_helper = RAGHelper()
        super().__init__(server_address, RequestHandlerClass)


# ======================
# Entry Point
# ======================

def main():
    time.sleep(5)
    # Serverless контейнеры автоматически устанавливают переменную PORT
    port = int(os.getenv('PORT', 8002))
    server_address = ("", port)

    # Используем кастомный сервер с предварительной инициализацией
    httpd = RAGHTTPServer(server_address, RAGRequestHandler)
    send_to_logger("info", f"Server running on port {port}")
    send_to_logger("info", "Health check: GET /health")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        send_to_logger("info", "Сервер остановлен")
    except Exception as e:
        send_to_logger("error", f"Ошибка при работе сервера: {e}")


if __name__ == "__main__":
    main()
