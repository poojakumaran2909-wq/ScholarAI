import json
import re
from difflib import SequenceMatcher

from sentence_transformers import SentenceTransformer
import numpy as np


MASTER_FILE = "data/scholarships.json"
NSP_FILE = "data/nsp_cleaned.json"
OUTPUT_FILE = "data/nsp_canonical_matches.json"


# ============================================================
# CANONICAL SCHOLARSHIP FAMILIES
# ============================================================

CANONICAL_ALIASES = {

    "aicte_swanath": [
        "swanath scholarship",
        "aicte swanath",
        "swanath scholarship scheme",
        "swanath scholarship scheme for orphans",
    ],

    "aicte_pragati": [
        "pragati scholarship",
        "aicte pragati",
        "pragati scholarship scheme",
        "pragati scholarship scheme for girls",
        "pragati scholarship scheme for girl students",
    ],

    "aicte_saksham": [
        "saksham scholarship",
        "aicte saksham",
        "saksham scholarship scheme",
        "saksham scholarship scheme for specially abled student",
        "saksham scholarship scheme for differently abled students",
    ],

    "national_pg_studies": [
        "national scholarship for post graduate studies",
        "national scholarship for postgraduate studies",
    ],

    "ishan_uday": [
        "ishan uday",
        "ishanuday",
        "ishan uday scholarship",
        "ishan uday special scholarship scheme",
        "ishan uday special scholarship scheme for ner",
        "ishan uday special scholarship scheme for north eastern region",
    ],

    "csss": [
        "central sector scheme of scholarship",
        "central sector scholarship",
        "csss",
        "pm usp csss",
        "pm usp central sector scheme of scholarship",
        "scholarship for college and university students",
    ],

    "nmmss": [
        "national means cum merit scholarship",
        "national means-cum-merit scholarship",
        "national means cum merit scholarship scheme",
        "nmmss",
    ],

    "sc_top_class": [
        "top class education scheme for sc students",
        "central sector scholarship of top class education for sc students",
        "top class education for sc students",
    ],

    "st_higher_education": [
        "national fellowship and scholarship for st students",
        "national fellowship and scholarship for higher education of st students",
        "top class education for schedule tribe students",
        "higher education of st students",
    ],

    "pm_yasasvi_school": [
        "pm yasasvi top class school scholarship",
        "pm yasasvi central sector scheme of top class education in schools",
    ],

    "pm_yasasvi_college": [
        "pm yasasvi central sector scheme of top class education in college",
        "pm yasasvi top class education in college",
    ],

    "nmms": [
        "national means cum merit scholarship",
        "national means-cum-merit scholarship scheme",
        "national means cum merit scholarship scheme nmmss",
        "nmmss",
    ],

    "railway": [
        "financial assistance to wards",
        "railway scholarship",
        "railways scholarship",
    ],
}


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_name(name):

    if not name:
        return ""

    name = name.lower()

    replacements = {
        "ner": "north eastern region",
        "nmmss": "national means cum merit scholarship",
        "csss": "central sector scholarship",
        "post graduate": "postgraduate",
        "post-graduate": "postgraduate",
        "under graduate": "undergraduate",
        "under-graduate": "undergraduate",
        "differently abled": "disability",
        "specially abled": "disability",
        "girl students": "girls",
        "girl student": "girls",
    }

    for old, new in replacements.items():
        name = name.replace(old, new)

    remove_phrases = [
        "merit based scheme",
        "welfare based scheme",
        "formally",
        "technical",
    ]

    for phrase in remove_phrases:
        name = name.replace(phrase, " ")

    name = re.sub(
        r"[^a-z0-9\s]",
        " ",
        name
    )

    name = re.sub(
        r"\s+",
        " ",
        name
    ).strip()

    return name


# ============================================================
# CANONICAL FAMILY DETECTION
# ============================================================

def detect_canonical_family(name):

    normalized = normalize_name(name)

    # Exact/substring alias matching
    for canonical_id, aliases in CANONICAL_ALIASES.items():

        for alias in aliases:

            alias_normalized = normalize_name(alias)

            if (
                alias_normalized in normalized
                or normalized in alias_normalized
            ):
                return canonical_id

    return None


# ============================================================
# SIMILARITY
# ============================================================

def name_similarity(a, b):

    a = normalize_name(a)
    b = normalize_name(b)

    return SequenceMatcher(
        None,
        a,
        b
    ).ratio()


# ============================================================
# STRUCTURED DATA
# ============================================================

def get_values(record, key):

    value = record.get(key, [])

    if value is None:
        return set()

    if isinstance(value, str):
        return {value.lower()}

    return {
        str(x).lower()
        for x in value
    }


def education_conflict(a, b):

    edu_a = get_values(
        a,
        "education_level"
    )

    edu_b = get_values(
        b,
        "education_level"
    )

    if not edu_a or not edu_b:
        return False

    # Same family can legitimately contain
    # degree + diploma variants.
    # Therefore we don't mark these as conflicts.

    # Strongly different levels
    if (
        "school" in edu_a
        and (
            "ug" in edu_b
            or "pg" in edu_b
            or "phd" in edu_b
        )
    ):
        return True

    if (
        "school" in edu_b
        and (
            "ug" in edu_a
            or "pg" in edu_a
            or "phd" in edu_a
        )
    ):
        return True

    return False


def category_conflict(a, b):

    cat_a = get_values(
        a,
        "category"
    )

    cat_b = get_values(
        b,
        "category"
    )

    if not cat_a or not cat_b:
        return False

    incompatible = [
        {"sc", "st"},
        {"minority", "disability"},
        {"sc", "minority"},
        {"st", "minority"},
    ]

    for group in incompatible:

        if (
            cat_a.intersection(group)
            and cat_b.intersection(group)
        ):
            if (
                cat_a.intersection(group)
                != cat_b.intersection(group)
            ):
                return True

    return False


# ============================================================
# EMBEDDINGS
# ============================================================

def build_embeddings(model, records):

    names = [
        item.get("name", "")
        for item in records
    ]

    return model.encode(
        names,
        normalize_embeddings=True
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("          NSP CANONICAL SCHOLARSHIP MATCHER")
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
    # Model
    # --------------------------------------------------------

    print(
        "\nLoading embedding model..."
    )

    model = SentenceTransformer(
        "all-MiniLM-L6-v2"
    )

    print(
        "Creating embeddings..."
    )

    master_embeddings = build_embeddings(
        model,
        master
    )

    nsp_embeddings = build_embeddings(
        model,
        nsp
    )

    # --------------------------------------------------------
    # Result containers
    # --------------------------------------------------------

    duplicates = []
    reviews = []
    new_scholarships = []

    # ========================================================
    # PROCESS NSP
    # ========================================================

    for i, nsp_item in enumerate(nsp):

        nsp_name = nsp_item.get(
            "name",
            ""
        )

        nsp_family = detect_canonical_family(
            nsp_name
        )

        best_match = None

        # ----------------------------------------------------
        # Compare with master
        # ----------------------------------------------------

        for j, master_item in enumerate(master):

            master_name = master_item.get(
                "name",
                ""
            )

            master_family = detect_canonical_family(
                master_name
            )

            semantic_score = float(
                np.dot(
                    nsp_embeddings[i],
                    master_embeddings[j]
                )
            )

            name_score = name_similarity(
                nsp_name,
                master_name
            )

            same_family = (
                nsp_family is not None
                and master_family is not None
                and nsp_family == master_family
            )

            edu_conflict = education_conflict(
                nsp_item,
                master_item
            )

            category_conflict_flag = category_conflict(
                nsp_item,
                master_item
            )

            # ------------------------------------------------
            # Calculate priority score
            # ------------------------------------------------

            score = (
                0.35 * name_score
                + 0.65 * semantic_score
            )

            # Canonical family gets strong priority
            if same_family:
                score += 0.25

            # Structural conflicts reduce confidence
            if edu_conflict:
                score -= 0.25

            if category_conflict_flag:
                score -= 0.25

            candidate = {
                "master_id": master_item.get("id"),
                "master_name": master_name,
                "canonical_family": master_family,
                "nsp_canonical_family": nsp_family,
                "name_score": round(
                    name_score,
                    4
                ),
                "semantic_score": round(
                    semantic_score,
                    4
                ),
                "final_score": round(
                    score,
                    4
                ),
                "same_canonical_family": same_family,
                "education_conflict": edu_conflict,
                "category_conflict": category_conflict_flag,
            }

            if (
                best_match is None
                or candidate["final_score"]
                > best_match["final_score"]
            ):
                best_match = candidate

        # ----------------------------------------------------
        # Classification
        # ----------------------------------------------------

        classification = "new"
        reason = "no_matching_family"

        if best_match:

            same_family = best_match[
                "same_canonical_family"
            ]

            final_score = best_match[
                "final_score"
            ]

            edu_conflict = best_match[
                "education_conflict"
            ]

            category_conflict_flag = best_match[
                "category_conflict"
            ]

            # ------------------------------------------------
            # Strong canonical match
            # ------------------------------------------------

            if (
                same_family
                and not category_conflict_flag
                and final_score >= 0.85
            ):

                classification = (
                    "likely_duplicate"
                )

                reason = (
                    "same_canonical_family"
                )

            # ------------------------------------------------
            # Same family but structural difference
            # ------------------------------------------------

            elif (
                same_family
                and (
                    edu_conflict
                    or category_conflict_flag
                )
            ):

                classification = (
                    "needs_review"
                )

                reason = (
                    "same_family_but_structural_difference"
                )

            # ------------------------------------------------
            # Strong semantic/name match
            # ------------------------------------------------

            elif (
                final_score >= 0.90
                and not category_conflict_flag
            ):

                classification = (
                    "likely_duplicate"
                )

                reason = (
                    "strong_name_semantic_match"
                )

            # ------------------------------------------------
            # Medium match
            # ------------------------------------------------

            elif (
                final_score >= 0.78
                and not category_conflict_flag
            ):

                classification = (
                    "needs_review"
                )

                reason = (
                    "possible_duplicate"
                )

        result = {
            "nsp_id": nsp_item.get("id"),
            "nsp_name": nsp_name,
            "nsp_canonical_family": nsp_family,
            "classification": classification,
            "reason": reason,
            "best_match": best_match,
        }

        if classification == "likely_duplicate":

            duplicates.append(result)

        elif classification == "needs_review":

            reviews.append(result)

        else:

            new_scholarships.append(result)

    # ========================================================
    # SAVE REPORT
    # ========================================================

    report = {
        "summary": {
            "master_count": len(master),
            "nsp_count": len(nsp),
            "likely_duplicates": len(
                duplicates
            ),
            "needs_review": len(
                reviews
            ),
            "new_scholarships": len(
                new_scholarships
            ),
        },

        "likely_duplicates": duplicates,

        "needs_review": reviews,

        "new_scholarships": new_scholarships,
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
    # PRINT RESULTS
    # ========================================================

    print(
        "\n" + "=" * 70
    )

    print("RESULTS")

    print(
        "=" * 70
    )

    print(
        f"Likely duplicates : "
        f"{len(duplicates)}"
    )

    print(
        f"Needs review      : "
        f"{len(reviews)}"
    )

    print(
        f"New scholarships   : "
        f"{len(new_scholarships)}"
    )

    # --------------------------------------------------------
    # DUPLICATES
    # --------------------------------------------------------

    if duplicates:

        print(
            "\n" + "=" * 70
        )

        print(
            "LIKELY DUPLICATES"
        )

        print(
            "=" * 70
        )

        for item in duplicates:

            match = item["best_match"]

            print(
                f"\nNSP    : "
                f"{item['nsp_name']}"
            )

            print(
                f"MASTER : "
                f"{match['master_name']}"
            )

            print(
                f"Family : "
                f"{item['nsp_canonical_family']}"
            )

            print(
                f"Score  : "
                f"{match['final_score']}"
            )

            print(
                f"Reason : "
                f"{item['reason']}"
            )

    # --------------------------------------------------------
    # REVIEW
    # --------------------------------------------------------

    if reviews:

        print(
            "\n" + "=" * 70
        )

        print(
            "NEEDS REVIEW"
        )

        print(
            "=" * 70
        )

        for item in reviews:

            match = item["best_match"]

            print(
                f"\nNSP    : "
                f"{item['nsp_name']}"
            )

            print(
                f"MASTER : "
                f"{match['master_name']}"
            )

            print(
                f"NSP family: "
                f"{item['nsp_canonical_family']}"
            )

            print(
                f"Master family: "
                f"{match['canonical_family']}"
            )

            print(
                f"Score  : "
                f"{match['final_score']}"
            )

            print(
                f"Reason : "
                f"{item['reason']}"
            )

    # --------------------------------------------------------
    # NEW
    # --------------------------------------------------------

    print(
        "\n" + "=" * 70
    )

    print(
        "NEW SCHOLARSHIPS"
    )

    print(
        "=" * 70
    )

    for item in new_scholarships:

        print(
            f"➕ {item['nsp_name']}"
        )

    print(
        "\n" + "=" * 70
    )

    print(
        "Full report:"
    )

    print(
        OUTPUT_FILE
    )

    print(
        "=" * 70
    )


if __name__ == "__main__":
    main()