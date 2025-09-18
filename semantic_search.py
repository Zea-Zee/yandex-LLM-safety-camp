from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings


class SemanticSearcher:
    def __init__(self):
        self.retriever = FAISS.load_local("./vectorstore_faiss",
                                          HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2"),
                                          allow_dangerous_deserialization=True).as_retriever(search_kwargs={"k": 3})

    def invoke(self, user_input):
        return self.retriever.invoke(user_input)
