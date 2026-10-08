from services.rag_service import ask_question


if __name__ == "__main__":
    query = input("Ask a question: ")

    print("Thinking...")

    answer = ask_question(query)

    print(f"\nAssistant: {answer}")