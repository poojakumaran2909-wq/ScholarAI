import json
import os
import re
from itertools import combinations

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


# ============================================================
# FILES
# ============================================================

MASTER_FILE = "data/scholarships.json"
NSP_FILE = "data/nsp_cleaned.json"
OUTPUT_FILE = "data/nsp_duplicate_flags.json"


# ============================================================
# SETTINGS
# ============================================================

NAME_LIKELY_THRESHOLD = 0.88
NAME_REVIEW_THRESHOLD = 0.78

SEMANTIC_LIKELY_THRESHOLD = 0.88
SEMANTIC_REVIEW_THRESHOLD = 0.78


# ============================================================
# TEXT HELPERS
# ============================================================

def normalize_text(text):
    if not text:
        return ""

    text = str(text).lower()

    text = re.sub(
        r"[^a-z0-9\s]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def tokenize(text):
    return set(
        normalize_text(text).split()
    )


def name_similarity(name1, name2):
    """
    Jaccard similarity over normalized name tokens.
    """

    a = tokenize(name1)
    b = tokenize(name2)

    if not a or not b:
        return 0.0

    intersection = len(a & b)
    union = len(a | b)

    return intersection / union


# ============================================================
# EDUCATION CONTRADICTION
# ============================================================

def education_contradiction(a, b):

    edu_a = set(
        a.get("education_level") or []
    )

    edu_b = set(
        b.get("education_level") or []
    )

    # Missing metadata = neutral
    if not edu_a or not edu_b:
        return False

    # --------------------------------------------------------
    # Direct contradictions
    # --------------------------------------------------------

    if "diploma" in edu_a and (
        "ug" in edu_b
        or "pg" in edu_b
        or "phd" in edu_b
    ):
        return True

    if "diploma" in edu_b and (
        "ug" in edu_a
        or "pg" in edu_a
        or "phd" in edu_a
    ):
        return True

    if "pre_matric" in edu_a and (
        "ug" in edu_b
        or "pg" in edu_b
        or "phd" in edu_b
    ):
        return True

    if "pre_matric" in edu_b and (
        "ug" in edu_a
        or "pg" in edu_a
        or "phd" in edu_a
    ):
        return True

    if "school" in edu_a and (
        "ug" in edu_b
        or "pg" in edu_b
        or "phd" in edu_b
        or "diploma" in edu_b
    ):
        return True

    if "school" in edu_b and (
        "ug" in edu_a
        or "pg" in edu_a
        or "phd" in edu_a
        or "diploma" in edu_a
    ):
        return True

    return False


# ============================================================
# CATEGORY CONTRADICTION
# ============================================================

def category_contradiction(a, b):

    cat_a = set(
        x.upper()
        for x in (a.get("category") or [])
    )

    cat_b = set(
        x.upper()
        for x in (b.get("category") or [])
    )

    # Missing category = neutral
    if not cat_a or not cat_b:
        return False

    # Strongly disjoint categories
    disjoint_pairs = [
        {"SC", "ST"},
        {"SC", "GENERAL"},
        {"ST", "GENERAL"},
    ]

    for pair in disjoint_pairs:

        if (
            pair.issubset(cat_a)
            and pair.issubset(cat_b)
        ):
            return True

    return False


# ============================================================
# SEMANTIC TEXT
# ============================================================

def scholarship_text(s):

    parts = [
        s.get("name", ""),
        " ".join(
            s.get("education_level") or []
        ),
        " ".join(
            s.get("category") or []
        ),
        s.get("benefit", ""),
        s.get("eligibility", ""),
    ]

    return " ".join(
        str(x)
        for x in parts
        if x
    )


# ============================================================
# CLASSIFY PAIR
# ============================================================

def classify_pair(
    nsp,
    master,
    name_score,
    semantic_score
):

    # Exact ID
    nsp_id = str(
        nsp.get("id", "")
    )

    master_id = str(
        master.get("id", "")
    )

    if nsp_id and nsp_id == master_id:

        return (
            "likely_duplicate",
            "exact_id_match"
        )

    # Structural contradiction
    if education_contradiction(
        nsp,
        master
    ):
        return (
            "not_duplicate",
            "education_contradiction"
        )

    if category_contradiction(
        nsp,
        master
    ):
        return (
            "not_duplicate",
            "category_contradiction"
        )

    # --------------------------------------------------------
    # Very high name similarity
    # --------------------------------------------------------

    if name_score >= 0.95:

        return (
            "likely_duplicate",
            "very_high_name_similarity"
        )

    # --------------------------------------------------------
    # Strong combined evidence
    # --------------------------------------------------------

    if (
        name_score >= NAME_LIKELY_THRESHOLD
        and
        semantic_score >= SEMANTIC_LIKELY_THRESHOLD
    ):

        return (
            "likely_duplicate",
            "high_name_and_semantic_similarity"
        )

    # --------------------------------------------------------
    # Moderate combined evidence
    # --------------------------------------------------------

    if (
        name_score >= NAME_REVIEW_THRESHOLD
        and
        semantic_score >= SEMANTIC_REVIEW_THRESHOLD
    ):

        return (
            "needs_review",
            "moderate_name_and_semantic_similarity"
        )

    # --------------------------------------------------------
    # Semantic similarity alone is NOT enough
    # --------------------------------------------------------

    if (
        semantic_score >= 0.90
        and
        name_score >= 0.60
    ):

        return (
            "needs_review",
            "high_semantic_similarity"
        )

    return (
        "unique",
        "insufficient_duplicate_evidence"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("          NSP DUPLICATE DETECTOR V5")
    print("=" * 70)

    # --------------------------------------------------------
    # Check files
    # --------------------------------------------------------

    if not os.path.exists(MASTER_FILE):

        print(
            f"\nERROR: {MASTER_FILE} not found."
        )

        return

    if not os.path.exists(NSP_FILE):

        print(
            f"\nERROR: {NSP_FILE} not found."
        )

        return

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    with open(
        MASTER_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        master = json.load(f)

    with open(
        NSP_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        nsp = json.load(f)

    print(
        f"\nMaster scholarships : {len(master)}"
    )

    print(
        f"NSP scholarships    : {len(nsp)}"
    )

    # --------------------------------------------------------
    # Embedding model
    # --------------------------------------------------------

    print(
        "\nLoading embedding model..."
    )

    model = SentenceTransformer(
        "all-MiniLM-L6-v2"
    )

    # --------------------------------------------------------
    # Precompute embeddings
    # --------------------------------------------------------

    print(
        "Creating embeddings..."
    )

    master_texts = [
        scholarship_text(s)
        for s in master
    ]

    nsp_texts = [
        scholarship_text(s)
        for s in nsp
    ]

    master_embeddings = model.encode(
        master_texts,
        show_progress_bar=True
    )

    nsp_embeddings = model.encode(
        nsp_texts,
        show_progress_bar=True
    )

    # --------------------------------------------------------
    # Compare
    # --------------------------------------------------------

    flags = []

    likely_duplicates = []
    needs_review = []
    unique_records = []

    print(
        "\nComparing NSP scholarships "
        "against master dataset..."
    )

    for nsp_index, nsp_item in enumerate(nsp):

        best_match = None

        best_name_score = 0.0
        best_semantic_score = 0.0

        for master_index, master_item in enumerate(master):

            name_score = name_similarity(
                nsp_item.get("name", ""),
                master_item.get("name", "")
            )

            semantic_score = cosine_similarity(
                nsp_embeddings[nsp_index].reshape(1, -1),
                master_embeddings[master_index].reshape(1, -1)
            )[0][0]

            # Keep strongest candidate
            combined_score = (
                0.45 * name_score
                +
                0.55 * semantic_score
            )

            if (
                best_match is None
                or combined_score > best_match["combined_score"]
            ):

                best_match = {
                    "master_index": master_index,
                    "combined_score": combined_score
                }

                best_name_score = name_score
                best_semantic_score = semantic_score

        # ----------------------------------------------------
        # Classify best match
        # ----------------------------------------------------

        master_item = master[
            best_match["master_index"]
        ]

        classification, reason = classify_pair(
            nsp_item,
            master_item,
            best_name_score,
            best_semantic_score
        )

        record = {
            "nsp_id": nsp_item.get("id"),
            "nsp_name": nsp_item.get("name"),
            "master_id": master_item.get("id"),
            "master_name": master_item.get("name"),
            "name_similarity": round(
                float(best_name_score),
                4
            ),
            "semantic_similarity": round(
                float(best_semantic_score),
                4
            ),
            "classification": classification,
            "reason": reason
        }

        flags.append(record)

        if classification == "likely_duplicate":

            likely_duplicates.append(record)

        elif classification == "needs_review":

            needs_review.append(record)

        else:

            unique_records.append(record)

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    output = {
        "summary": {
            "master_count": len(master),
            "nsp_count": len(nsp),
            "likely_duplicates": len(
                likely_duplicates
            ),
            "needs_review": len(
                needs_review
            ),
            "unique": len(
                unique_records
            )
        },
        "likely_duplicates": likely_duplicates,
        "needs_review": needs_review,
        "all_comparisons": flags
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output,
            f,
            indent=2,
            ensure_ascii=False
        )

    # ========================================================
    # RESULTS
    # ========================================================

    print("\n")
    print("=" * 70)
    print("                    RESULTS")
    print("=" * 70)

    print(
        "\nLikely duplicates:",
        len(likely_duplicates)
    )

    print(
        "Needs review:",
        len(needs_review)
    )

    print(
        "Unique:",
        len(unique_records)
    )

    # --------------------------------------------------------
    # Likely duplicates
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("                  LIKELY DUPLICATES")
    print("=" * 70)

    if not likely_duplicates:

        print(
            "\nNone found."
        )

    else:

        for i, item in enumerate(
            likely_duplicates,
            start=1
        ):

            print(
                f"\n{i}. {item['nsp_name']}"
            )

            print(
                "   ↔",
                item["master_name"]
            )

            print(
                "   Name similarity:",
                item["name_similarity"]
            )

            print(
                "   Semantic similarity:",
                item["semantic_similarity"]
            )

            print(
                "   Reason:",
                item["reason"]
            )

    # --------------------------------------------------------
    # Review
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("                    NEEDS REVIEW")
    print("=" * 70)

    if not needs_review:

        print(
            "\nNone found."
        )

    else:

        for i, item in enumerate(
            needs_review,
            start=1
        ):

            print(
                f"\n{i}. {item['nsp_name']}"
            )

            print(
                "   ↔",
                item["master_name"]
            )

            print(
                "   Name similarity:",
                item["name_similarity"]
            )

            print(
                "   Semantic similarity:",
                item["semantic_similarity"]
            )

            print(
                "   Reason:",
                item["reason"]
            )

    # --------------------------------------------------------
    # Final
    # --------------------------------------------------------

    print("\n" + "=" * 70)

    print(
        f"Saved duplicate report to: "
        f"{OUTPUT_FILE}"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()