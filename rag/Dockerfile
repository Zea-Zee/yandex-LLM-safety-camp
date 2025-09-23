FROM base:3.11

WORKDIR /app/rag/vectorstore_faiss

WORKDIR /app

COPY . ./rag

WORKDIR /app/rag

EXPOSE 8002

CMD ["python", "rag.py"]
