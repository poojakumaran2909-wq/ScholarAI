from vectorstore.faiss_db import load_vector_database


def retrieve_documents(question, k=5):

    vector_db = load_vector_database()

    documents = vector_db.similarity_search(
        question,
        k=k
    )

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

        # Count common words between question and scholarship name
        overlap = len(question_words & name_words)

        scored_documents.append(
            (overlap, document)
        )

    # Highest name-word overlap first
    scored_documents.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return [
        document
        for _, document in scored_documents
    ]