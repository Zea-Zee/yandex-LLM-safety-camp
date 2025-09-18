import os
import tempfile

import boto3
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from settings import S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET, S3_PREFIX


def download_from_s3():
    s3 = boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name='ru-central3'
    )

    try:
        objects = s3.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=S3_PREFIX
        )
    except Exception as e:
        print(f"Ошибка подключения: {e}")
        return None

    if 'Contents' not in objects:
        return []

    local_files = []
    with tempfile.TemporaryDirectory() as tmpdir:
        for obj in objects['Contents']:
            key = obj.get('Key')
            if not key or not isinstance(key, str) or key.endswith('/'):
                continue

            size = obj.get('Size', 0)
            if size == 0:
                continue

            local_path = os.path.join(tmpdir, os.path.basename(key))
            try:
                s3.download_file(S3_BUCKET, key, local_path)
                if os.path.getsize(local_path) == 0:
                    continue
                local_files.append(local_path)
            except Exception as e:
                print(f"Ошибка скачивания {key}: {e}")
                continue

        # return load_and_index_documents(local_files)
        return load_batches(local_files)

def load_batches(paths):
    """Загружает файлы и разбивает их на текстовые чанки"""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", " ", ""]
    )

    chunks = []
    for path in paths:
        try:
            # Читаем содержимое файла
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Создаем документ LangChain
            document = Document(page_content=content)

            # Разбиваем на чанки
            document_chunks = text_splitter.split_documents([document])
            chunks.extend(document_chunks)

            print(f'Загружен файл: {path}, создано {len(document_chunks)} чанков')

        except Exception as e:
            print(f"Ошибка обработки файла {path}: {e}")
            continue

print(f'Всего создано {len(chunks)} чанков')

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectorstore = FAISS.from_documents(chunks, embeddings)
vectorstore.save_local("./vectorstore_faiss")
