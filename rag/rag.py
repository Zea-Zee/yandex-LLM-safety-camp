import json
import os
import tempfile
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from io import BytesIO
from typing import List, Dict

import boto3
import PyPDF2
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from settings import S3_BUCKET, S3_PREFIX, S3_SECRET_KEY, S3_ACCESS_KEY, S3_ENDPOINT

# ======================
# Logging setup
# ======================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


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
        logger.error("Ошибка при чтении PDF: %s", e)
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
                logger.debug("Документ загружен: %s", path)
        except Exception as e:
            logger.warning("Ошибка обработки документа %s: %s", path, e)

    if not docs:
        logger.info("Нет валидных документов, создается заглушка.")
        docs = [Document(page_content="Нет доступных документов.")]
    return docs


def build_vectorstore(docs: List[Document]) -> FAISS:
    """Создает FAISS-векторное хранилище из документов."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(docs)
    logger.info("Создано %d чанков", len(chunks))

    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = FAISS.from_documents(chunks, embeddings)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    vectorstore.save_local(os.path.join(current_dir, "vectorstore_faiss"))
    logger.info("Векторное хранилище сохранено локально.")
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
        logger.info("S3 клиент инициализирован.")

    def list_objects(self) -> Dict:
        try:
            logger.info("Получение списка объектов из S3...")
            return self.client.list_objects_v2(Bucket=S3_BUCKET, Prefix=S3_PREFIX)
        except Exception as e:
            logger.error("Ошибка подключения к S3: %s", e)
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
                    logger.info("Загрузка PDF из S3: %s", key)
                    response = self.client.get_object(Bucket=S3_BUCKET, Key=key)
                    pdf_data = response["Body"].read()
                    pdf_text = extract_text_from_pdf(BytesIO(pdf_data))
                    if pdf_text.strip():
                        txt_path = local_path + ".txt"
                        with open(txt_path, "w", encoding="utf-8") as f:
                            f.write(pdf_text)
                        local_files.append(txt_path)
                        logger.debug("PDF сконвертирован в текст: %s", txt_path)
                else:
                    logger.info("Загрузка файла из S3: %s", key)
                    self.client.download_file(S3_BUCKET, key, local_path)
                    if os.path.getsize(local_path) > 0:
                        local_files.append(local_path)
                        logger.debug("Файл загружен: %s", local_path)
            except Exception as e:
                logger.warning("Ошибка обработки %s: %s", key, e)

        logger.info("Загружено %d файлов из S3", len(local_files))
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
        logger.info("Инициализация векторного хранилища при старте сервера...")
        self.vectorstore = self._download_and_build_index()
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3})
        logger.info("Векторное хранилище инициализировано и готово к работе")

    def _download_and_build_index(self) -> FAISS:
        s3 = S3Helper()
        objects = s3.list_objects()

        if "Contents" not in objects:
            logger.warning("В S3 не найдено объектов, создается пустой индекс.")
            return self._build_empty_index()

        with tempfile.TemporaryDirectory() as tmpdir:
            local_files = s3.download_files(objects, tmpdir)
            return self._build_index_from_files(local_files)

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
        logger.info("Запрос на поиск контекста: '%s'", question)
        docs = self.retriever.invoke(question)
        logger.info("Найдено %d релевантных документов", len(docs))
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

    def _retrieve_question(self) -> str:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return ""
        post_data = self.rfile.read(length)
        try:
            json_data = json.loads(post_data.decode("utf-8"))
            return json_data.get("question", "")
        except json.JSONDecodeError:
            logger.warning("Получен некорректный JSON-запрос.")
            return ""

    def do_POST(self):
        question = self._retrieve_question()
        if not question.strip():
            logger.warning("Пустой вопрос получен в POST-запросе.")
            self._send_json_response({"error": "Вопрос не задан"}, status=400)
            return

        try:
            context_chunks = self.rag_helper.get_context_chunks(question)
            logger.info("Ответ сформирован, длина контекста: %d символов", len(context_chunks))
            self._send_json_response({"context": context_chunks})
        except Exception as e:
            logger.error("Ошибка при обработке запроса: %s", e)
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
    port = 8002
    server_address = ("", port)

    # Используем кастомный сервер с предварительной инициализацией
    httpd = RAGHTTPServer(server_address, RAGRequestHandler)
    logger.info("Server running on http://localhost:%d", port)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Сервер остановлен")
    except Exception as e:
        logger.error("Ошибка при работе сервера: %s", e)


if __name__ == "__main__":
    main()
