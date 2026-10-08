import json
import re
from difflib import SequenceMatcher

from sentence_transformers import SentenceTransformer
import numpy as np


MASTER_FILE = "data/scholarships.json"
NSP_FILE = "data/nsp_cleaned.json"
OUTPUT_FILE = "data/nsp_duplicate_flags_v6.json"


# ============================================================
# NAME NORMALIZATION
# ============================================================

def normalize_name(name):

    if not name:
        return ""

    name = name.lower()

    # Common abbreviations / alternate naming
    replacements = {
        "ner": "north eastern region",
        "nmmss": "national means cum merit scholarship",
        "csss": "central sector scholarship",
        "pm usp": "pm usp",
        "pm-us p": "pm usp",
        "post graduate": "postgraduate",
        "post-graduate": "postgraduate",
        "under graduate": "undergraduate",
        "under-graduate": "undergraduate",
        "sc students": "scheduled caste",
        "st students": "scheduled tribe",
        "dnt": "denotified nomadic tribes",
    }

    for old, new in replacements.items():
        name = name.replace(old, new)

    # Remove things that describe the NSP listing,
    # not the actual identity of the scholarship.
    remove_phrases = [
        "merit based scheme",
        "welfare based scheme",
        "formally",
        "technical",
        "central sector",
        "special",
    ]

    for phrase in remove_phrases:
        name = name.replace(phrase, " ")

    # Normalize punctuation
    name = re.sub(r"[^a-z0-9\s]", " ", name)

    # Normalize spaces
    name = re.sub(r"\s+", " ", name).strip()

    return name


# ============================================================
# TOKEN SIMILARITY
# ============================================================

def token_similarity(name1, name2):

    a = set(normalize_name(name1).split())
    b = set(normalize_name(name2).split())

    if not a or not b:
        return 0.0

    intersection = len(a & b)
    union = len(a | b)

    return intersection / union


def sequence_similarity(name1, name2):

    a = normalize_name(name1)
    b = normalize_name(name2)

    return SequenceMatcher(
        None,
        a,
        b
    ).ratio()


# ============================================================
# STRUCTURED INFORMATION
# ============================================================

def get_list(record, key):

    value = record.get(key, [])

    if value is None:
        return []

    if isinstance(value, str):
        return [value.lower()]

    return [
        str(x).lower()
        for x in value
    ]


def has_contradiction(nsp, master):

    nsp_education = set(
        get_list(nsp, "education_level")
    )

    master_education = set(
        get_list(master, "education_level")
    )

    nsp_category = set(
        get_list(nsp, "category")
    )

    master_category = set(
        get_list(master, "category")
    )

    # --------------------------------------------------------
    # Education contradictions
    # --------------------------------------------------------

    education_groups = [
        {"school", "pre_matric", "post_matric"},
        {"ug", "diploma"},
        {"pg"},
        {"phd"},
    ]

    for group in education_groups:

        nsp_group = nsp_education & group
        master_group = master_education & group

        if nsp_group and master_group:

            if nsp_group.isdisjoint(master_group):
                return True, "education_level_conflict"

    # Explicit degree vs diploma
    if (
        "degree" in nsp_education
        and "diploma" in master_education
    ):
        return True, "degree_vs_diploma"

    if (
        "diploma" in nsp_education
        and "degree" in master_education
    ):
        return True, "diploma_vs_degree"

    # --------------------------------------------------------
    # Category contradictions
    # --------------------------------------------------------

    category_groups = [
        {"sc", "scheduled caste"},
        {"st", "scheduled tribe"},
        {"obc"},
        {"minority"},
        {"disability"},
    ]

    for group in category_groups:

        nsp_group = nsp_category & group
        master_group = master_category & group

        if nsp_group and master_group:

            if nsp_group.isdisjoint(master_group):
                return True, "category_conflict"

    return False, None


# ============================================================
# SPECIAL KEYWORD CONTRADICTIONS
# ============================================================

def keyword_set(name):

    name = normalize_name(name)

    keywords = set()

    important_keywords = [
        "orphan",
        "girl",
        "girls",
        "women",
        "disability",
        "disabled",
        "minority",
        "sc",
        "scheduled caste",
        "st",
        "scheduled tribe",
        "obc",
        "ebc",
        "dnt",
        "north eastern region",
        "ner",
        "beedi",
        "railway",
        "jammu",
        "kashmir",
        "ladakh",
        "professional courses",
        "school",
        "college",
        "university",
        "postgraduate",
        "undergraduate",
        "diploma",
    ]

    for word in important_keywords:

        if word in name:
            keywords.add(word)

    return keywords


def special_contradiction(nsp, master):

    a = keyword_set(nsp.get("name", ""))
    b = keyword_set(master.get("name", ""))

    # Target groups that cannot be treated as interchangeable.
    incompatible_pairs = [
        ("disability", "minority"),
        ("disability", "orphan"),
        ("sc", "st"),
        ("scheduled caste", "scheduled tribe"),
        ("girl", "orphan"),
        ("girls", "orphan"),
    ]

    for x, y in incompatible_pairs:

        if x in a and y in b:
            return True

        if y in a and x in b:
            return True

    return False


# ============================================================
# COMBINED NAME SCORE
# ============================================================

def combined_name_score(name1, name2):

    token_score = token_similarity(
        name1,
        name2
    )

    sequence_score = sequence_similarity(
        name1,
        name2
    )

    return (
        0.55 * token_score
        + 0.45 * sequence_score
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("       NSP DUPLICATE DETECTOR V6")
    print("=" * 70)

    # --------------------------------------------------------
    # Load data
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

    master_names = [
        item.get("name", "")
        for item in master
    ]

    nsp_names = [
        item.get("name", "")
        for item in nsp
    ]

    print(
        "Creating embeddings..."
    )

    master_embeddings = model.encode(
        master_names,
        normalize_embeddings=True
    )

    nsp_embeddings = model.encode(
        nsp_names,
        normalize_embeddings=True
    )

    # --------------------------------------------------------
    # Results
    # --------------------------------------------------------

    likely_duplicates = []
    needs_review = []
    unique = []

    all_comparisons = []

    print(
        "\nComparing NSP scholarships against master..."
    )

    for i, nsp_item in enumerate(nsp):

        nsp_name = nsp_item.get(
            "name",
            ""
        )

        best_matches = []

        for j, master_item in enumerate(master):

            master_name = master_item.get(
                "name",
                ""
            )

            # Name scores
            name_score = combined_name_score(
                nsp_name,
                master_name
            )

            # Semantic score
            semantic_score = float(
                np.dot(
                    nsp_embeddings[i],
                    master_embeddings[j]
                )
            )

            # Structural contradiction
            contradiction, contradiction_reason = (
                has_contradiction(
                    nsp_item,
                    master_item
                )
            )

            # Special keyword contradiction
            special_conflict = special_contradiction(
                nsp_item,
                master_item
            )

            if special_conflict:
                contradiction = True
                contradiction_reason = (
                    "special_requirement_conflict"
                )

            # Combined score
            combined_score = (
                0.45 * name_score
                + 0.55 * semantic_score
            )

            best_matches.append({
                "master_name": master_name,
                "master_id": master_item.get("id"),
                "name_score": round(
                    name_score,
                    4
                ),
                "semantic_score": round(
                    semantic_score,
                    4
                ),
                "combined_score": round(
                    combined_score,
                    4
                ),
                "contradiction": contradiction,
                "contradiction_reason": contradiction_reason
            })

        # ----------------------------------------------------
        # Sort best matches
        # ----------------------------------------------------

        best_matches.sort(
            key=lambda x: x["combined_score"],
            reverse=True
        )

        top_match = best_matches[0]

        # Keep top 3 for auditing
        top_three = best_matches[:3]

        comparison_record = {
            "nsp_name": nsp_name,
            "nsp_id": nsp_item.get("id"),
            "top_matches": top_three
        }

        all_comparisons.append(
            comparison_record
        )

        name_score = top_match["name_score"]
        semantic_score = top_match["semantic_score"]
        combined_score = top_match["combined_score"]

        contradiction = top_match["contradiction"]

        # ----------------------------------------------------
        # Classification
        # ----------------------------------------------------

        classification = "unique"
        reason = "no_strong_match"

        # Exact normalized name
        if (
            normalize_name(nsp_name)
            == normalize_name(
                top_match["master_name"]
            )
            and not contradiction
        ):

            classification = "likely_duplicate"

            reason = "normalized_name_match"

        # Very strong name similarity
        elif (
            name_score >= 0.88
            and semantic_score >= 0.82
            and not contradiction
        ):

            classification = "likely_duplicate"

            reason = "strong_name_and_semantic_match"

        # Strong semantic + name
        elif (
            name_score >= 0.78
            and semantic_score >= 0.85
            and not contradiction
        ):

            classification = "likely_duplicate"

            reason = "semantic_and_name_match"

        # Review
        elif (
            name_score >= 0.70
            and semantic_score >= 0.78
            and not contradiction
        ):

            classification = "needs_review"

            reason = "possible_duplicate"

        # Semantic similarity alone is NOT enough.
        elif (
            semantic_score >= 0.88
            and name_score >= 0.65
            and not contradiction
        ):

            classification = "needs_review"

            reason = "high_semantic_similarity"

        # Contradictions mean don't merge automatically.
        elif contradiction:

            classification = "unique"

            reason = (
                "similar_name_but_structural_conflict"
            )

        # ----------------------------------------------------
        # Store result
        # ----------------------------------------------------

        result = {
            "nsp_id": nsp_item.get("id"),
            "nsp_name": nsp_name,
            "classification": classification,
            "reason": reason,
            "best_match": top_match,
            "top_matches": top_three
        }

        if classification == "likely_duplicate":

            likely_duplicates.append(result)

        elif classification == "needs_review":

            needs_review.append(result)

        else:

            unique.append(result)

    # ========================================================
    # SAVE REPORT
    # ========================================================

    report = {
        "summary": {
            "master_count": len(master),
            "nsp_count": len(nsp),
            "likely_duplicates": len(
                likely_duplicates
            ),
            "needs_review": len(
                needs_review
            ),
            "unique": len(unique)
        },

        "likely_duplicates":
            likely_duplicates,

        "needs_review":
            needs_review,

        "unique":
            unique,

        "all_comparisons":
            all_comparisons
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            report,
            f,
            indent=2,
            ensure_ascii=False
        )

    # ========================================================
    # PRINT SUMMARY
    # ========================================================

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    print(
        f"Likely duplicates : "
        f"{len(likely_duplicates)}"
    )

    print(
        f"Needs review      : "
        f"{len(needs_review)}"
    )

    print(
        f"Unique            : "
        f"{len(unique)}"
    )

    # --------------------------------------------------------
    # Likely duplicates
    # --------------------------------------------------------

    if likely_duplicates:

        print(
            "\n" + "=" * 70
        )

        print(
            "LIKELY DUPLICATES"
        )

        print(
            "=" * 70
        )

        for item in likely_duplicates:

            match = item["best_match"]

            print(
                f"\nNSP    : {item['nsp_name']}"
            )

            print(
                f"MASTER : {match['master_name']}"
            )

            print(
                f"Name   : {match['name_score']}"
            )

            print(
                f"Semantic: "
                f"{match['semantic_score']}"
            )

            print(
                f"Reason : {item['reason']}"
            )

    # --------------------------------------------------------
    # Review
    # --------------------------------------------------------

    if needs_review:

        print(
            "\n" + "=" * 70
        )

        print(
            "NEEDS REVIEW"
        )

        print(
            "=" * 70
        )

        for item in needs_review:

            match = item["best_match"]

            print(
                f"\nNSP    : {item['nsp_name']}"
            )

            print(
                f"MASTER : {match['master_name']}"
            )

            print(
                f"Name   : {match['name_score']}"
            )

            print(
                f"Semantic: "
                f"{match['semantic_score']}"
            )

    print(
        "\n" + "=" * 70
    )

    print(
        f"Full report saved to:"
        f"\n{OUTPUT_FILE}"
    )

    print(
        "=" * 70
    )


if __name__ == "__main__":
    main()