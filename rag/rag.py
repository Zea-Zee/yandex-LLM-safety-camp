import json
import os
import tempfile
from http.server import HTTPServer, BaseHTTPRequestHandler
from io import BytesIO

import boto3
import PyPDF2
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from settings import S3_BUCKET, S3_PREFIX, S3_SECRET_KEY, S3_ACCESS_KEY, S3_ENDPOINT


def extract_text_from_pdf(pdf_file):
    """Извлекает текст из PDF файла"""
    text = ""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as e:
        print(f"Ошибка при чтении PDF: {e}")
    return text


def download_from_s3():
    s3 = boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name='ru-central1'
    )

    try:
        objects = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=S3_PREFIX)
    except Exception as e:
        print(f"Ошибка подключения: {e}")
        return None

    if 'Contents' not in objects:
        return load_and_index_documents([])

    local_files = []
    with tempfile.TemporaryDirectory() as tmpdir:
        for obj in objects['Contents']:
            key = obj.get('Key')
            if not key or not isinstance(key, str) or key.endswith('/'):
                continue

            size = obj.get('Size', 0)
            if size == 0:
                continue

            # Определяем расширение файла
            file_extension = os.path.splitext(key)[1].lower()

            local_path = os.path.join(tmpdir, os.path.basename(key))

            try:
                # Для PDF файлов обрабатываем содержимое
                if file_extension == '.pdf':
                    # Скачиваем файл в память
                    response = s3.get_object(Bucket=S3_BUCKET, Key=key)
                    pdf_data = response['Body'].read()

                    # Извлекаем текст из PDF
                    pdf_text = extract_text_from_pdf(BytesIO(pdf_data))

                    if pdf_text.strip():
                        # Сохраняем извлеченный текст во временный файл
                        text_file_path = local_path + '.txt'
                        with open(text_file_path, 'w', encoding='utf-8') as f:
                            f.write(pdf_text)
                        local_files.append(text_file_path)
                else:
                    # Для обычных файлов скачиваем как обычно
                    s3.download_file(S3_BUCKET, key, local_path)
                    if os.path.getsize(local_path) == 0:
                        continue
                    local_files.append(local_path)

            except Exception as e:
                print(f"Ошибка обработки {key}: {e}")
                continue

        return load_and_index_documents(local_files)


def load_and_index_documents(local_files):
    loaded = []
    for local_file in local_files:
        try:
            # Проверяем расширение файла
            file_extension = os.path.splitext(local_file)[1].lower()

            if file_extension == '.txt':
                # Текстовые файлы
                with open(local_file, 'r', encoding='utf-8') as f:
                    content = f.read()
            else:
                # Другие форматы
                with open(local_file, 'r', encoding='utf-8') as f:
                    content = f.read()

            if content.strip():
                loaded.append(Document(page_content=content))

        except Exception as e:
            print(f"Ошибка обработки документа {local_file}: {e}")
            continue

    valid_docs = [
        doc for doc in loaded
        if hasattr(doc, 'page_content') and
           isinstance(doc.page_content, str) and
           doc.page_content.strip()
    ]

    if not valid_docs:
        valid_docs = [Document(page_content="Нет доступных документов.", metadata={})]

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    )

    chunks = text_splitter.split_documents(valid_docs)
    print(f"Создано {len(chunks)} чанков")

    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local("./vectorstore_faiss")

    return vectorstore


class RAGRequestHandler(BaseHTTPRequestHandler):

    def _send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        json_data = json.loads(post_data.decode('utf-8'))
        question = json_data['question']

        print(question)
        if not os.path.exists('./vectorstore_faiss'):
            download_from_s3()
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vectorstore = FAISS.load_local("./vectorstore_faiss", embeddings, allow_dangerous_deserialization=True)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        retrieved_docs = retriever.invoke(question)
        context_chunks = "\n\n".join([doc.page_content for doc in retrieved_docs])
        print(context_chunks)
        print(f"RAG: найдено {len(retrieved_docs)} релевантных фрагментов.")

        response = {
            "context": context_chunks,
        }

        self._send_json_response(response)


def main():
    port = 8002
    server_address = ('', port)
    httpd = HTTPServer(server_address, RAGRequestHandler)
    print(f"Server running on http://localhost:{port}")
    httpd.serve_forever()


if __name__ == '__main__':
    main()