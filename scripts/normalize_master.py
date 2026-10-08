import json
import shutil
from pathlib import Path
from datetime import datetime


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

MASTER_FILE = DATA_DIR / "scholarships.json"


# ============================================================
# LOAD MASTER DATASET
# ============================================================

if not MASTER_FILE.exists():
    print(f"❌ File not found: {MASTER_FILE}")
    raise SystemExit(1)


with open(MASTER_FILE, "r", encoding="utf-8") as f:
    scholarships = json.load(f)


print("=" * 60)
print("SCHOLARSHIP MASTER NORMALIZER")
print("=" * 60)

print(f"Loaded scholarships: {len(scholarships)}")


# ============================================================
# BACKUP
# ============================================================

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

backup_file = (
    DATA_DIR /
    f"scholarships_before_normalization_{timestamp}.json"
)

shutil.copy2(MASTER_FILE, backup_file)

print(f"Backup created: {backup_file.name}")


# ============================================================
# STANDARD FIELD STRUCTURE
# ============================================================

STANDARD_FIELDS = [
    "id",
    "name",
    "source",
    "source_url",
    "education_level",
    "category",
    "gender",
    "state",
    "income_limit",
    "minimum_marks",
    "benefit",
    "eligibility",
    "documents",
    "deadline",
    "application_url",
    "last_checked"
]


# ============================================================
# NORMALIZATION
# ============================================================

normalized_scholarships = []

missing_ids = []
seen_ids = set()

duplicate_ids = []


for index, scholarship in enumerate(scholarships):

    # --------------------------------------------------------
    # Create a clean record
    # --------------------------------------------------------

    record = {}

    # --------------------------------------------------------
    # Standard fields
    # --------------------------------------------------------

    for field in STANDARD_FIELDS:

        value = scholarship.get(field)

        # Keep missing information as None
        if value == "":
            value = None

        record[field] = value

    # --------------------------------------------------------
    # Preserve additional important metadata
    # --------------------------------------------------------

    extra_fields = [
        "specification_status",
        "added_from",
        "added_at",
        "content_hash"
    ]

    for field in extra_fields:

        if field in scholarship:
            record[field] = scholarship[field]

    # --------------------------------------------------------
    # ID validation
    # --------------------------------------------------------

    scholarship_id = record.get("id")

    if not scholarship_id:

        missing_ids.append({
            "index": index,
            "name": record.get("name")
        })

    else:

        if scholarship_id in seen_ids:

            duplicate_ids.append({
                "id": scholarship_id,
                "name": record.get("name"),
                "index": index
            })

        else:
            seen_ids.add(scholarship_id)

    # --------------------------------------------------------
    # Education level
    # --------------------------------------------------------

    education = record.get("education_level")

    if isinstance(education, str):

        education = education.strip()

        if education:
            record["education_level"] = [education]
        else:
            record["education_level"] = None

    elif isinstance(education, list):

        cleaned_education = []

        for item in education:

            if item is None:
                continue

            item = str(item).strip()

            if item and item not in cleaned_education:
                cleaned_education.append(item)

        record["education_level"] = (
            cleaned_education
            if cleaned_education
            else None
        )

    # --------------------------------------------------------
    # Category
    # --------------------------------------------------------

    category = record.get("category")

    if isinstance(category, str):

        category = category.strip()

        record["category"] = category if category else None

    # --------------------------------------------------------
    # Gender
    # --------------------------------------------------------

    gender = record.get("gender")

    if isinstance(gender, str):

        gender = gender.strip()

        record["gender"] = gender if gender else None

    # --------------------------------------------------------
    # State
    # --------------------------------------------------------

    state = record.get("state")

    if isinstance(state, str):

        state = state.strip()

        record["state"] = state if state else None

    # --------------------------------------------------------
    # Documents
    # --------------------------------------------------------

    documents = record.get("documents")

    if isinstance(documents, str):

        documents = documents.strip()

        if documents:
            record["documents"] = [documents]
        else:
            record["documents"] = None

    elif isinstance(documents, list):

        cleaned_documents = []

        for item in documents:

            if item is None:
                continue

            item = str(item).strip()

            if item and item not in cleaned_documents:
                cleaned_documents.append(item)

        record["documents"] = (
            cleaned_documents
            if cleaned_documents
            else None
        )

    # --------------------------------------------------------
    # Last checked
    # --------------------------------------------------------

    if not record.get("last_checked"):

        record["last_checked"] = datetime.now().strftime(
            "%Y-%m-%d"
        )

    # --------------------------------------------------------
    # Add normalized record
    # --------------------------------------------------------

    normalized_scholarships.append(record)


# ============================================================
# SAVE NORMALIZED DATA
# ============================================================

with open(MASTER_FILE, "w", encoding="utf-8") as f:

    json.dump(
        normalized_scholarships,
        f,
        indent=2,
        ensure_ascii=False
    )


# ============================================================
# SUMMARY
# ============================================================

print()
print("=" * 60)
print("NORMALIZATION SUMMARY")
print("=" * 60)

print(f"Records processed : {len(normalized_scholarships)}")
print(f"Missing IDs       : {len(missing_ids)}")
print(f"Duplicate IDs     : {len(duplicate_ids)}")


# ============================================================
# SHOW PROBLEMS
# ============================================================

if missing_ids:

    print()
    print("❌ RECORDS WITH MISSING IDs")

    for item in missing_ids:

        print(
            f"Index: {item['index']} | "
            f"Name: {item['name']}"
        )


if duplicate_ids:

    print()
    print("❌ DUPLICATE IDs")

    for item in duplicate_ids:

        print(
            f"ID: {item['id']} | "
            f"Name: {item['name']} | "
            f"Index: {item['index']}"
        )


print()
print("=" * 60)
print("✅ NORMALIZATION COMPLETED")
print("=" * 60)

print(f"Updated file: {MASTER_FILE}")
print(f"Backup file : {backup_file}")