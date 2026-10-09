from vectorstore.faiss_db import load_vector_database


def retrieve_documents(question, k=5):

    print("RAG: Loading vector database...")

    vector_db = load_vector_database()

    print("RAG: Vector database loaded.")
    print("RAG: Running similarity search...")

    documents = vector_db.similarity_search(
        question,
        k=k
    )

    print(f"RAG: Retrieved {len(documents)} documents.")

    question_words = set(
        question.lower()
        .replace("?", "")
        .replace(",", "")
        .split()
    )

    scored_documents = []

    for document in documents:

        scholarship_name = document.metadata.get(
            "name",
            ""
        ).lower()

        name_words = set(
            scholarship_name
            .replace("-", " ")
            .split()
        )

        overlap = len(question_words & name_words)

        scored_documents.append(
            (overlap, document)
        )

    scored_documents.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return [
        document
        for _, document in scored_documents
    ]