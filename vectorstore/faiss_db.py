import os

from langchain_community.vectorstores import FAISS

from embeddings.embedding_model import get_embedding_model


INDEX_PATH = os.path.join("data", "faiss_index")


def load_vector_database():
    embeddings = get_embedding_model()

    vector_db = FAISS.load_local(
        INDEX_PATH,
        embeddings,
        allow_dangerous_deserialization=True
    )

    return vector_db