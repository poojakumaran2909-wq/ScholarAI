import json
import os
import hashlib
from datetime import datetime

from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS


# ============================================================
# CONFIG
# ============================================================

DATA_FILE = "data/scholarships.json"
FAISS_DIR = "data/faiss_index"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"


# ============================================================
# LOAD SCHOLARSHIPS
# ============================================================

def load_scholarships():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# CREATE SEARCHABLE CONTENT
# ============================================================

def create_content(scholarship):

    education_level = scholarship.get("education_level") or []
    if isinstance(education_level, str):
        education_level = [education_level]

    documents = scholarship.get("documents") or []
    if isinstance(documents, str):
        documents = [documents]

    parts = [
        f"Scholarship Name: {scholarship.get('name')}",
        f"Source: {scholarship.get('source')}",
        f"Education Level: {', '.join(education_level)}",
        f"Category: {scholarship.get('category')}",
        f"Gender: {scholarship.get('gender')}",
        f"State: {scholarship.get('state')}",
        f"Income Limit: {scholarship.get('income_limit')}",
        f"Minimum Marks: {scholarship.get('minimum_marks')}",
        f"Benefit: {scholarship.get('benefit')}",
        f"Eligibility: {scholarship.get('eligibility')}",
        f"Documents Required: {', '.join(documents)}",
        f"Deadline: {scholarship.get('deadline')}",
        f"Application URL: {scholarship.get('application_url')}",
        f"Source URL: {scholarship.get('source_url')}",
        f"Last Checked: {scholarship.get('last_checked')}",
    ]

    return "\n".join(
        str(part) for part in parts
        if part is not None
    )


# ============================================================
# CONTENT HASH
# ============================================================

def calculate_hash(content):

    return hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()


# ============================================================
# CREATE DOCUMENTS
# ============================================================

def create_documents(scholarships):

    documents = []

    for scholarship in scholarships:

        content = create_content(scholarship)

        content_hash = calculate_hash(content)

        metadata = scholarship.copy()

        metadata["content_hash"] = content_hash

        document = Document(
            page_content=content,
            metadata=metadata
        )

        documents.append(document)

    return documents


# ============================================================
# EXTRACT FAISS RECORDS
# ============================================================

def get_existing_records(vector_db):

    records = {}

    for doc_id, document in vector_db.docstore._dict.items():

        scholarship_id = document.metadata.get("id")

        if scholarship_id:

            records[scholarship_id] = {
                "content_hash": document.metadata.get("content_hash"),
                "doc_id": doc_id
            }

    return records


# ============================================================
# DETECT CHANGES
# ============================================================

def detect_changes(documents, existing_records):

    current_ids = set()
    new_documents = []
    changed_documents = []
    unchanged_documents = []

    for document in documents:

        scholarship_id = document.metadata.get("id")

        current_ids.add(scholarship_id)

        current_hash = document.metadata.get("content_hash")

        if scholarship_id not in existing_records:

            new_documents.append(document)

        else:

            old_hash = existing_records[scholarship_id]["content_hash"]

            if old_hash != current_hash:

                changed_documents.append(document)

            else:

                unchanged_documents.append(document)

    existing_ids = set(existing_records.keys())

    deleted_ids = existing_ids - current_ids

    return (
        new_documents,
        changed_documents,
        unchanged_documents,
        deleted_ids
    )


# ============================================================
# REBUILD FAISS
# ============================================================

def rebuild_faiss(documents, embeddings):

    print()
    print("Creating FAISS index from scratch...")

    vector_db = FAISS.from_documents(
        documents,
        embeddings
    )

    vector_db.save_local(FAISS_DIR)

    print("FAISS index created successfully.")

    return vector_db


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("        SCHOLARSHIP FAISS INGESTION / UPDATE")
    print("=" * 70)

    # --------------------------------------------------------
    # Load master dataset
    # --------------------------------------------------------

    scholarships = load_scholarships()

    print()
    print(f"Loaded {len(scholarships)} scholarships")

    # --------------------------------------------------------
    # Create documents
    # --------------------------------------------------------

    documents = create_documents(scholarships)

    print(f"Created {len(documents)} documents")

    # --------------------------------------------------------
    # Load embedding model
    # --------------------------------------------------------

    print()
    print("Loading embedding model...")

    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL
    )

    print("Embedding model loaded")

    # --------------------------------------------------------
    # If FAISS doesn't exist
    # --------------------------------------------------------

    if not os.path.exists(FAISS_DIR):

        print()
        print("FAISS index does not exist.")
        print("Creating new FAISS index...")

        rebuild_faiss(
            documents,
            embeddings
        )

        print()
        print(f"Total documents in FAISS: {len(documents)}")

        return

    # --------------------------------------------------------
    # Load existing FAISS
    # --------------------------------------------------------

    print()
    print("Loading existing FAISS index...")

    vector_db = FAISS.load_local(
        FAISS_DIR,
        embeddings,
        allow_dangerous_deserialization=True
    )

    existing_records = get_existing_records(vector_db)

    print(
        f"Existing scholarships in FAISS: "
        f"{len(existing_records)}"
    )

    # --------------------------------------------------------
    # Detect changes
    # --------------------------------------------------------

    (
        new_documents,
        changed_documents,
        unchanged_documents,
        deleted_ids
    ) = detect_changes(
        documents,
        existing_records
    )

    print()
    print("CHANGE DETECTION")
    print("-" * 70)

    print(f"New       : {len(new_documents)}")
    print(f"Changed   : {len(changed_documents)}")
    print(f"Deleted   : {len(deleted_ids)}")
    print(f"Unchanged : {len(unchanged_documents)}")

    # --------------------------------------------------------
    # Print deleted IDs
    # --------------------------------------------------------

    if deleted_ids:

        print()
        print("Deleted scholarships:")

        for scholarship_id in deleted_ids:

            print(f"🗑️ {scholarship_id}")

    # --------------------------------------------------------
    # Print new scholarships
    # --------------------------------------------------------

    if new_documents:

        print()
        print("New scholarships:")

        for document in new_documents:

            print(
                f"➕ {document.metadata.get('name')}"
            )

    # --------------------------------------------------------
    # Print changed scholarships
    # --------------------------------------------------------

    if changed_documents:

        print()
        print("Changed scholarships:")

        for document in changed_documents:

            print(
                f"🔄 {document.metadata.get('name')}"
            )

    # --------------------------------------------------------
    # NOTHING CHANGED
    # --------------------------------------------------------

    if (
        len(new_documents) == 0
        and
        len(changed_documents) == 0
        and
        len(deleted_ids) == 0
    ):

        print()
        print("No changes detected.")

        print(
            f"FAISS already contains "
            f"{len(existing_records)} scholarships."
        )

        return

    # --------------------------------------------------------
    # ONLY NEW RECORDS
    # --------------------------------------------------------

    if (
        len(new_documents) > 0
        and
        len(changed_documents) == 0
        and
        len(deleted_ids) == 0
    ):

        print()
        print("Only new scholarships detected.")

        vector_db.add_documents(
            new_documents
        )

        vector_db.save_local(
            FAISS_DIR
        )

        print()
        print("New scholarships added successfully.")

        print(
            f"Total documents in FAISS: "
            f"{len(existing_records) + len(new_documents)}"
        )

        return

    # --------------------------------------------------------
    # CHANGES / DELETIONS
    # --------------------------------------------------------

    print()
    print(
        "Scholarship changes detected."
    )

    print(
        "Rebuilding FAISS index from current master dataset..."
    )

    vector_db = rebuild_faiss(
        documents,
        embeddings
    )

    print()
    print("=" * 70)
    print("FAISS UPDATE COMPLETED")
    print("=" * 70)

    print(
        f"Master scholarships : {len(scholarships)}"
    )

    print(
        f"FAISS documents     : {len(documents)}"
    )

    print("=" * 70)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()