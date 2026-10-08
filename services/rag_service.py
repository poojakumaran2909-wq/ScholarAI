from retriever.retriever import retrieve_documents
from prompts.scholarship_prompt import PROMPT_TEMPLATE
from llm.groq_client import generate_answer


def ask_question(question):
    # Step 1: Retrieve relevant documents
    documents = retrieve_documents(question)

    # Step 2: Build context
    context = "\n\n".join(
        document.page_content
        for document in documents
    )

    # Step 3: Build prompt
    prompt = PROMPT_TEMPLATE.format(
        context=context,
        question=question
    )

    # Step 4: Generate answer
    answer = generate_answer(prompt)

    # Step 5: Keep information about retrieved scholarships
    scholarships = []

    for document in documents:
        scholarships.append(document.metadata)

    return {
        "answer": answer,
        "scholarships": scholarships
    }