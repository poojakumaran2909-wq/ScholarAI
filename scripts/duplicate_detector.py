import json
import os
import re
from difflib import SequenceMatcher

import numpy as np
from sentence_transformers import SentenceTransformer


# ============================================================
# CONFIGURATION
# ============================================================

MASTER_FILE = "data/scholarships.json"
OUTPUT_FILE = "data/duplicate_flags.json"

# Name thresholds
VERY_HIGH_NAME = 0.95
HIGH_NAME = 0.88
MODERATE_NAME = 0.78

# Semantic thresholds
HIGH_SEMANTIC = 0.88
REVIEW_SEMANTIC = 0.78


# ============================================================
# JSON HELPERS
# ============================================================

def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text):

    if text is None:
        return ""

    if isinstance(text, list):
        text = " ".join(str(x) for x in text)

    text = str(text).lower()

    # Remove quotation marks
    text = (
        text
        .replace('"', "")
        .replace("'", "")
        .replace("“", "")
        .replace("”", "")
        .replace("‘", "")
        .replace("’", "")
    )

    # Normalize ampersand
    text = text.replace("&", " and ")

    # Remove punctuation
    text = re.sub(r"[^a-z0-9\s]", " ", text)

    # Remove extra spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text


# ============================================================
# NAME SIMILARITY
# ============================================================

def name_similarity(name1, name2):

    name1 = normalize_text(name1)
    name2 = normalize_text(name2)

    if not name1 or not name2:
        return 0.0

    return SequenceMatcher(
        None,
        name1,
        name2
    ).ratio()


# ============================================================
# EDUCATION CONTEXT
# ============================================================

def get_education_context(scholarship):

    """
    Extract explicit education stage.

    Missing information = unknown.

    IMPORTANT:
    We do NOT infer education level from generic words
    like "degree".
    """

    context = set()

    class_range = normalize_text(
        scholarship.get("class_range", "")
    )

    level = normalize_text(
        scholarship.get("level", "")
    )

    name = normalize_text(
        scholarship.get("name", "")
    )

    notes = normalize_text(
        scholarship.get("notes", "")
    )

    combined = " ".join(
        x for x in [
            class_range,
            level,
            name,
            notes
        ]
        if x
    )

    # --------------------------------------------------------
    # PRE-MATRIC
    # --------------------------------------------------------

    if (
        "pre matric" in combined
        or "pre-matric" in combined
    ):
        context.add("pre_matric")

    # --------------------------------------------------------
    # POST-MATRIC
    # --------------------------------------------------------

    if (
        "post matric" in combined
        or "post-matric" in combined
    ):
        context.add("post_matric")

    # --------------------------------------------------------
    # UG
    # --------------------------------------------------------

    if (
        class_range == "ug"
        or "undergraduate" in combined
        or "under graduate" in combined
        or "ug scholarship" in combined
        or "ug students" in combined
    ):
        context.add("ug")

    # --------------------------------------------------------
    # PG
    # --------------------------------------------------------

    if (
        class_range == "pg"
        or "postgraduate" in combined
        or "post graduate" in combined
        or "pg scholarship" in combined
        or "pg students" in combined
    ):
        context.add("pg")

    # --------------------------------------------------------
    # PhD
    # --------------------------------------------------------

    if (
        "phd" in combined
        or "doctoral" in combined
        or "doctorate" in combined
    ):
        context.add("phd")

    # --------------------------------------------------------
    # SCHOOL
    # --------------------------------------------------------

    if (
        "school student" in combined
        or "school students" in combined
        or "school scholarship" in combined
    ):
        context.add("school")

    return context


# ============================================================
# GEOGRAPHIC CONTEXT
# ============================================================

INDIAN_STATES = {
    "andhra pradesh",
    "arunachal pradesh",
    "assam",
    "bihar",
    "chhattisgarh",
    "goa",
    "gujarat",
    "haryana",
    "himachal pradesh",
    "jharkhand",
    "karnataka",
    "kerala",
    "madhya pradesh",
    "maharashtra",
    "manipur",
    "meghalaya",
    "mizoram",
    "nagaland",
    "odisha",
    "punjab",
    "rajasthan",
    "sikkim",
    "tamil nadu",
    "telangana",
    "tripura",
    "uttar pradesh",
    "uttarakhand",
    "west bengal",
    "delhi",
    "jammu and kashmir",
    "ladakh",
    "chandigarh",
    "puducherry",
}


def get_geographic_context(scholarship):

    fields = [
        scholarship.get("name", ""),
        scholarship.get("notes", ""),
        scholarship.get("documents", ""),
        scholarship.get("state", ""),
    ]

    combined = normalize_text(
        " ".join(
            str(x)
            for x in fields
            if x
        )
    )

    states = set()

    for state in INDIAN_STATES:

        if state in combined:
            states.add(state)

    return states


# ============================================================
# CATEGORY CONTEXT
# ============================================================

CATEGORY_KEYWORDS = {
    "sc": [
        "sc",
        "scheduled caste",
        "scheduled castes",
    ],

    "st": [
        "st",
        "scheduled tribe",
        "scheduled tribes",
    ],

    "obc": [
        "obc",
        "other backward class",
        "other backward classes",
    ],

    "minority": [
        "minority",
        "minorities",
    ],

    "ews": [
        "ews",
        "economically weaker section",
    ],

    "general": [
        "general category",
    ],
}


def get_category_context(scholarship):

    fields = [
        scholarship.get("name", ""),
        scholarship.get("category", ""),
        scholarship.get("notes", ""),
    ]

    combined = normalize_text(
        " ".join(
            str(x)
            for x in fields
            if x
        )
    )

    categories = set()

    for category, keywords in CATEGORY_KEYWORDS.items():

        for keyword in keywords:

            # Avoid matching "sc" inside arbitrary words
            if keyword == "sc" or keyword == "st":

                pattern = rf"\b{keyword}\b"

                if re.search(pattern, combined):
                    categories.add(category)

            elif keyword in combined:
                categories.add(category)

    return categories


# ============================================================
# SPECIAL REQUIREMENTS
# ============================================================

def get_special_requirements(scholarship):

    fields = [
        scholarship.get("name", ""),
        scholarship.get("notes", ""),
        scholarship.get("documents", ""),
        scholarship.get("eligibility", ""),
    ]

    combined = normalize_text(
        " ".join(
            str(x)
            for x in fields
            if x
        )
    )

    requirements = set()

    if (
        "female" in combined
        or "women" in combined
        or "girl" in combined
    ):
        requirements.add("female")

    if (
        "disability" in combined
        or "disabled" in combined
    ):
        requirements.add("disability")

    if "orphan" in combined:
        requirements.add("orphan")

    if (
        "northeast" in combined
        or "north eastern" in combined
    ):
        requirements.add("northeast")

    if (
        "abroad" in combined
        or "foreign university" in combined
    ):
        requirements.add("abroad")

    return requirements


# ============================================================
# ELIGIBILITY SIGNALS
# ============================================================

def get_eligibility_signals(scholarship):

    signals = set()

    text = normalize_text(
        " ".join(
            str(scholarship.get(field, ""))
            for field in [
                "name",
                "notes",
                "documents",
                "eligibility",
                "class_range",
            ]
        )
    )

    # --------------------------------------------------------
    # INCOME
    # --------------------------------------------------------

    income = scholarship.get("income_max")

    if income is not None:

        try:
            signals.add(
                f"income_max:{float(income)}"
            )

        except (ValueError, TypeError):
            pass

    # --------------------------------------------------------
    # MARKS
    # --------------------------------------------------------

    marks = scholarship.get("marks_min")

    if marks is not None:

        try:
            signals.add(
                f"marks_min:{float(marks)}"
            )

        except (ValueError, TypeError):
            pass

    # --------------------------------------------------------
    # SPECIAL REQUIREMENTS
    # --------------------------------------------------------

    signals.update(
        get_special_requirements(scholarship)
    )

    # --------------------------------------------------------
    # CATEGORY
    # --------------------------------------------------------

    signals.update(
        f"category:{x}"
        for x in get_category_context(scholarship)
    )

    return signals


# ============================================================
# STRUCTURAL CONTRADICTIONS
# ============================================================

def find_structural_contradictions(a, b):

    contradictions = []

    # ========================================================
    # EDUCATION
    # ========================================================

    edu_a = get_education_context(a)
    edu_b = get_education_context(b)

    # Only compare if BOTH records contain explicit info.
    if edu_a and edu_b:

        # ----------------------------------------------------
        # Pre-Matric vs Post-Matric
        # ----------------------------------------------------

        if (
            "pre_matric" in edu_a
            and "post_matric" in edu_b
        ) or (
            "post_matric" in edu_a
            and "pre_matric" in edu_b
        ):

            contradictions.append(
                "different education stage: "
                "pre-matric vs post-matric"
            )

        # ----------------------------------------------------
        # School vs Higher Education
        # ----------------------------------------------------

        school_a = (
            "school" in edu_a
            or "pre_matric" in edu_a
        )

        school_b = (
            "school" in edu_b
            or "pre_matric" in edu_b
        )

        higher_a = bool(
            edu_a.intersection(
                {"ug", "pg", "phd"}
            )
        )

        higher_b = bool(
            edu_b.intersection(
                {"ug", "pg", "phd"}
            )
        )

        if school_a and higher_b:

            contradictions.append(
                "school-level vs higher-education"
            )

        if school_b and higher_a:

            contradictions.append(
                "school-level vs higher-education"
            )

        # ----------------------------------------------------
        # UG vs PG
        # ----------------------------------------------------

        if (
            edu_a == {"ug"}
            and edu_b == {"pg"}
        ) or (
            edu_a == {"pg"}
            and edu_b == {"ug"}
        ):

            contradictions.append(
                "different education level: UG vs PG"
            )

        # ----------------------------------------------------
        # UG vs PhD
        # ----------------------------------------------------

        if (
            edu_a == {"ug"}
            and edu_b == {"phd"}
        ) or (
            edu_a == {"phd"}
            and edu_b == {"ug"}
        ):

            contradictions.append(
                "different education level: UG vs PhD"
            )

    # ========================================================
    # GEOGRAPHY
    # ========================================================

    geo_a = get_geographic_context(a)
    geo_b = get_geographic_context(b)

    # Missing geography = neutral.
    if geo_a and geo_b:

        if geo_a.isdisjoint(geo_b):

            contradictions.append(
                "different geographic states: "
                + ", ".join(sorted(geo_a))
                + " vs "
                + ", ".join(sorted(geo_b))
            )

    # ========================================================
    # CATEGORY
    # ========================================================

    category_a = get_category_context(a)
    category_b = get_category_context(b)

    # Category is only considered contradictory when
    # BOTH records explicitly identify categories and
    # there is no overlap.

    if category_a and category_b:

        if category_a.isdisjoint(category_b):

            contradictions.append(
                "different target categories: "
                + ", ".join(sorted(category_a))
                + " vs "
                + ", ".join(sorted(category_b))
            )

    return contradictions


# ============================================================
# SEMANTIC TEXT
# ============================================================

def build_semantic_text(scholarship):

    fields = []

    name = scholarship.get("name")
    benefit = scholarship.get("benefit")
    notes = scholarship.get("notes")
    eligibility = scholarship.get("eligibility")
    how_to_apply = scholarship.get("how_to_apply")

    if name:
        fields.append(
            f"Scholarship: {name}"
        )

    if eligibility:
        fields.append(
            f"Eligibility: {eligibility}"
        )

    if benefit:
        fields.append(
            f"Benefit: {benefit}"
        )

    if notes:
        fields.append(
            f"Details: {notes}"
        )

    if how_to_apply:
        fields.append(
            f"Application: {how_to_apply}"
        )

    return " ".join(fields)


# ============================================================
# COSINE SIMILARITY
# ============================================================

def cosine_similarity(vector_a, vector_b):

    denominator = (
        np.linalg.norm(vector_a)
        * np.linalg.norm(vector_b)
    )

    if denominator == 0:
        return 0.0

    return float(
        np.dot(vector_a, vector_b)
        / denominator
    )


# ============================================================
# PAIR CLASSIFICATION
# ============================================================

def classify_pair(
    scholarship_a,
    scholarship_b,
    name_score,
    semantic_score
):

    contradictions = find_structural_contradictions(
        scholarship_a,
        scholarship_b
    )

    # ========================================================
    # RULE 1
    # HARD STRUCTURAL CONTRADICTION
    # ========================================================

    if contradictions:

        return {
            "status": "different",
            "reason": "structural_contradiction",
            "contradictions": contradictions
        }

    # ========================================================
    # RULE 2
    # VERY HIGH NAME SIMILARITY
    #
    # Example:
    #
    # Ishan Uday Special Scholarship...
    # “IshanUday” Special Scholarship...
    #
    # These are almost certainly the same program.
    # ========================================================

    if name_score >= VERY_HIGH_NAME:

        return {
            "status": "likely_duplicate",
            "reason": "very_high_name_similarity",
            "contradictions": []
        }

    # ========================================================
    # RULE 3
    # HIGH NAME + HIGH SEMANTIC
    # ========================================================

    if (
        name_score >= HIGH_NAME
        and semantic_score >= HIGH_SEMANTIC
    ):

        return {
            "status": "likely_duplicate",
            "reason": "high_name_and_semantic_similarity",
            "contradictions": []
        }

    # ========================================================
    # RULE 4
    # MODERATE/HIGH NAME + SOME SEMANTIC SIMILARITY
    # ========================================================

    if (
        name_score >= MODERATE_NAME
        and semantic_score >= REVIEW_SEMANTIC
    ):

        return {
            "status": "needs_review",
            "reason": "name_and_semantic_similarity",
            "contradictions": []
        }

    # ========================================================
    # RULE 5
    # SEMANTIC SIMILARITY ALONE
    #
    # IMPORTANT:
    # Never call it duplicate based only on semantic score.
    #
    # Similar scholarships often discuss:
    # - students
    # - tuition
    # - income
    # - minority
    # - education
    #
    # So semantic similarity alone is insufficient.
    # ========================================================

    if semantic_score >= HIGH_SEMANTIC:

        return {
            "status": "different",
            "reason": "semantic_similarity_only",
            "contradictions": []
        }

    # ========================================================
    # RULE 6
    # EVERYTHING ELSE
    # ========================================================

    return {
        "status": "different",
        "reason": "low_similarity",
        "contradictions": []
    }


# ============================================================
# EXACT ID DUPLICATES
# ============================================================

def find_exact_id_duplicates(scholarships):

    seen = {}
    duplicates = []

    for scholarship in scholarships:

        scholarship_id = scholarship.get("id")

        if not scholarship_id:
            continue

        scholarship_id = str(
            scholarship_id
        )

        if scholarship_id in seen:

            duplicates.append({
                "id": scholarship_id,
                "name_1": seen[scholarship_id],
                "name_2": scholarship.get(
                    "name",
                    ""
                )
            })

        else:

            seen[scholarship_id] = scholarship.get(
                "name",
                ""
            )

    return duplicates


# ============================================================
# DUPLICATE DETECTION
# ============================================================

def detect_duplicates(scholarships):

    print("\n🔎 Loading embedding model...")

    model = SentenceTransformer(
        "all-MiniLM-L6-v2"
    )

    # --------------------------------------------------------
    # Build semantic texts
    # --------------------------------------------------------

    semantic_texts = [
        build_semantic_text(
            scholarship
        )
        for scholarship in scholarships
    ]

    # --------------------------------------------------------
    # Embed ONCE
    # --------------------------------------------------------

    print(
        "🧠 Creating embeddings for scholarships..."
    )

    embeddings = model.encode(
        semantic_texts,
        normalize_embeddings=True,
        show_progress_bar=True
    )

    likely_duplicates = []
    needs_review = []

    total_pairs = 0

    # --------------------------------------------------------
    # Pairwise comparison
    # --------------------------------------------------------

    for i in range(
        len(scholarships)
    ):

        for j in range(
            i + 1,
            len(scholarships)
        ):

            total_pairs += 1

            a = scholarships[i]
            b = scholarships[j]

            name_score = name_similarity(
                a.get("name", ""),
                b.get("name", "")
            )

            semantic_score = cosine_similarity(
                embeddings[i],
                embeddings[j]
            )

            classification = classify_pair(
                a,
                b,
                name_score,
                semantic_score
            )

            result = {
                "scholarship_1": {
                    "id": a.get("id"),
                    "name": a.get("name")
                },

                "scholarship_2": {
                    "id": b.get("id"),
                    "name": b.get("name")
                },

                "name_similarity": round(
                    name_score,
                    4
                ),

                "semantic_similarity": round(
                    semantic_score,
                    4
                ),

                "status": classification[
                    "status"
                ],

                "reason": classification[
                    "reason"
                ],

                "contradictions": classification[
                    "contradictions"
                ]
            }

            if (
                classification["status"]
                == "likely_duplicate"
            ):

                likely_duplicates.append(
                    result
                )

            elif (
                classification["status"]
                == "needs_review"
            ):

                needs_review.append(
                    result
                )

    return (
        total_pairs,
        likely_duplicates,
        needs_review
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print("\n" + "=" * 60)
    print(
        "🔍 SCHOLARSHIP DUPLICATE DETECTOR v5"
    )
    print("=" * 60)

    # --------------------------------------------------------
    # Check file
    # --------------------------------------------------------

    if not os.path.exists(
        MASTER_FILE
    ):

        print(
            f"\n❌ Master file not found:"
            f" {MASTER_FILE}"
        )

        exit()

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    scholarships = load_json(
        MASTER_FILE
    )

    print(
        f"\n📚 Scholarships loaded:"
        f" {len(scholarships)}"
    )

    # --------------------------------------------------------
    # Exact ID duplicates
    # --------------------------------------------------------

    exact_id_duplicates = (
        find_exact_id_duplicates(
            scholarships
        )
    )

    print(
        f"🆔 Exact ID duplicates:"
        f" {len(exact_id_duplicates)}"
    )

    # --------------------------------------------------------
    # Pairwise detection
    # --------------------------------------------------------

    (
        total_pairs,
        likely_duplicates,
        needs_review
    ) = detect_duplicates(
        scholarships
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print(
        f"\n🔢 Scholarship pairs checked:"
        f" {total_pairs}"
    )

    print(
        f"🟥 Likely duplicates:"
        f" {len(likely_duplicates)}"
    )

    print(
        f"🟨 Needs review:"
        f" {len(needs_review)}"
    )

    # ========================================================
    # PRINT LIKELY DUPLICATES
    # ========================================================

    if likely_duplicates:

        print(
            "\n" + "=" * 60
        )

        print(
            "🟥 LIKELY DUPLICATES"
        )

        print(
            "=" * 60
        )

        for index, item in enumerate(
            likely_duplicates,
            start=1
        ):

            print(f"\n{index}.")

            print(
                "   Scholarship 1:",
                item[
                    "scholarship_1"
                ]["name"]
            )

            print(
                "   ID:",
                item[
                    "scholarship_1"
                ]["id"]
            )

            print(
                "   Scholarship 2:",
                item[
                    "scholarship_2"
                ]["name"]
            )

            print(
                "   ID:",
                item[
                    "scholarship_2"
                ]["id"]
            )

            print(
                "   Name similarity:",
                item[
                    "name_similarity"
                ]
            )

            print(
                "   Semantic similarity:",
                item[
                    "semantic_similarity"
                ]
            )

            print(
                "   Reason:",
                item["reason"]
            )

    # ========================================================
    # PRINT REVIEW
    # ========================================================

    if needs_review:

        print(
            "\n" + "=" * 60
        )

        print(
            "🟨 NEEDS REVIEW"
        )

        print(
            "=" * 60
        )

        for index, item in enumerate(
            needs_review,
            start=1
        ):

            print(f"\n{index}.")

            print(
                "   Scholarship 1:",
                item[
                    "scholarship_1"
                ]["name"]
            )

            print(
                "   ID:",
                item[
                    "scholarship_1"
                ]["id"]
            )

            print(
                "   Scholarship 2:",
                item[
                    "scholarship_2"
                ]["name"]
            )

            print(
                "   ID:",
                item[
                    "scholarship_2"
                ]["id"]
            )

            print(
                "   Name similarity:",
                item[
                    "name_similarity"
                ]
            )

            print(
                "   Semantic similarity:",
                item[
                    "semantic_similarity"
                ]
            )

            print(
                "   Reason:",
                item["reason"]
            )

            if item["contradictions"]:

                print(
                    "   Contradictions:"
                )

                for contradiction in item[
                    "contradictions"
                ]:

                    print(
                        "      -",
                        contradiction
                    )

    # ========================================================
    # SAVE REPORT
    # ========================================================

    output = {
        "summary": {
            "total_scholarships": len(
                scholarships
            ),

            "exact_id_duplicates": len(
                exact_id_duplicates
            ),

            "total_pairs_checked": (
                total_pairs
            ),

            "likely_duplicates": len(
                likely_duplicates
            ),

            "needs_review": len(
                needs_review
            )
        },

        "exact_id_duplicates":
            exact_id_duplicates,

        "likely_duplicates":
            likely_duplicates,

        "needs_review":
            needs_review
    }

    save_json(
        OUTPUT_FILE,
        output
    )

    print(
        f"\n💾 Duplicate report saved to:"
        f" {OUTPUT_FILE}"
    )

    print(
        "\n" + "=" * 60
    )

    print(
        "🎉 Duplicate detection completed!"
    )

    print(
        "=" * 60
    )