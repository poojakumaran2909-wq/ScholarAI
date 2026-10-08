import json
import re
from pathlib import Path
from typing import Any


# ============================================================
# PATH
# ============================================================

DATA_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "scholarships.json"
)


# ============================================================
# BASIC HELPERS
# ============================================================

def normalize(value: Any) -> str:
    """
    Convert a value into a clean lowercase string.
    """
    if value is None:
        return ""

    if isinstance(value, list):
        return " ".join(str(item) for item in value).strip().lower()

    return str(value).strip().lower()


def as_list(value: Any) -> list:
    """
    Convert a value into a list.

    Examples:
        "UG"              -> ["UG"]
        ["UG", "PG"]      -> ["UG", "PG"]
        None              -> []
    """
    if value is None:
        return []

    if isinstance(value, list):
        return value

    return [value]


def text_value(value: Any) -> str:
    """
    Convert lists/dicts/values into readable text.
    """
    if value is None:
        return ""

    if isinstance(value, list):
        return " ".join(str(item) for item in value)

    if isinstance(value, dict):
        return " ".join(
            f"{key} {value}"
            for key, value in value.items()
        )

    return str(value)


def first_present(record: dict, *keys: str):
    """
    Return the first non-empty value among the given keys.
    """
    for key in keys:
        value = record.get(key)

        if value is not None and value != "":
            return value

    return None


# ============================================================
# CATEGORY MATCHING
# ============================================================

def category_matches(
    student_category: Any,
    scholarship_category: Any
):
    """
    Match student category against scholarship category.

    Returns:
        True  -> definitely matches
        False -> definitely does not match
        None  -> information is missing / needs verification
    """

    student_category = normalize(student_category)

    if not student_category:
        return None

    categories = [
        normalize(category)
        for category in as_list(scholarship_category)
        if normalize(category)
    ]

    # No category information in scholarship
    if not categories:
        return None

    # Scholarships open to everyone
    universal_categories = {
        "all",
        "all categories",
        "all category",
        "any",
        "any category",
        "general",
        "open to all",
    }

    if any(category in universal_categories for category in categories):
        return True

    # Direct match
    if student_category in categories:
        return True

    # Common aliases
    aliases = {
        "general": {"general", "gen", "open"},
        "gen": {"general", "gen", "open"},
        "obc": {"obc", "other backward classes"},
        "sc": {"sc", "scheduled caste"},
        "st": {"st", "scheduled tribe"},
        "ews": {"ews", "economically weaker section"},
    }

    student_aliases = aliases.get(
        student_category,
        {student_category}
    )

    for category in categories:
        if category in student_aliases:
            return True

    return False


# ============================================================
# INCOME MATCHING
# ============================================================

def income_matches(
    student_income: Any,
    income_limit: Any
):
    """
    Compare student family income with scholarship income limit.

    Current normalized schema:
        income_limit

    Backward compatible:
        income_max
    """

    if student_income is None or student_income == "":
        return None

    if income_limit is None or income_limit == "":
        # No known income restriction
        return True

    try:
        student_income = float(student_income)
        income_limit = float(income_limit)

        return student_income <= income_limit

    except (ValueError, TypeError):
        return None


# ============================================================
# MARKS MATCHING
# ============================================================

def marks_matches(
    student_marks: Any,
    minimum_marks: Any
):
    """
    Compare student marks with minimum required marks.

    Current normalized schema:
        minimum_marks

    Backward compatible:
        marks_min
    """

    if student_marks is None or student_marks == "":
        return None

    if minimum_marks is None or minimum_marks == "":
        # No known minimum marks restriction
        return True

    try:
        student_marks = float(student_marks)
        minimum_marks = float(minimum_marks)

        return student_marks >= minimum_marks

    except (ValueError, TypeError):
        return None


# ============================================================
# EDUCATION NORMALIZATION
# ============================================================

def education_tokens(value: Any) -> set:
    """
    Convert education information into standard tokens.

    Supported tokens include:
        school
        pre_matric
        post_matric
        ug
        pg
        phd
        diploma
        iti
    """

    tokens = set()

    for item in as_list(value):

        text = normalize(item)

        if not text:
            continue

        # Preserve original normalized value
        tokens.add(
            text.replace("-", "_").replace(" ", "_")
        )

        # ----------------------------------------------------
        # Undergraduate
        # ----------------------------------------------------

        if (
            "undergraduate" in text
            or "under graduate" in text
            or "bachelor" in text
            or text in {
                "ug",
                "u_g",
                "b_e",
                "be",
                "btech",
                "b_tech",
                "b.tech",
                "degree",
            }
        ):
            tokens.add("ug")

        # ----------------------------------------------------
        # Postgraduate
        # ----------------------------------------------------

        if (
            "postgraduate" in text
            or "post graduate" in text
            or "master" in text
            or text in {
                "pg",
                "p_g",
                "mtech",
                "m_tech",
                "m.tech",
                "mba",
                "mca",
                "ma",
                "msc",
                "m.sc",
            }
        ):
            tokens.add("pg")

        # ----------------------------------------------------
        # PhD
        # ----------------------------------------------------

        if (
            "phd" in text
            or "doctorate" in text
            or "doctoral" in text
        ):
            tokens.add("phd")

        # ----------------------------------------------------
        # Diploma
        # ----------------------------------------------------

        if (
            "diploma" in text
            or "polytechnic" in text
        ):
            tokens.add("diploma")

        # ----------------------------------------------------
        # ITI
        # ----------------------------------------------------

        if "iti" in text:
            tokens.add("iti")

        # ----------------------------------------------------
        # School
        # ----------------------------------------------------

        if (
            "school" in text
            or "class 1" in text
            or "class 2" in text
            or "class 3" in text
            or "class 4" in text
            or "class 5" in text
            or "class 6" in text
            or "class 7" in text
            or "class 8" in text
            or "class 9" in text
            or "class 10" in text
            or "class 11" in text
            or "class 12" in text
        ):
            tokens.add("school")

        # ----------------------------------------------------
        # Pre-matric
        # ----------------------------------------------------

        if "pre_matric" in text or "pre-matric" in text:
            tokens.add("pre_matric")

        # ----------------------------------------------------
        # Post-matric
        # ----------------------------------------------------

        if "post_matric" in text or "post-matric" in text:
            tokens.add("post_matric")

    return tokens


# ============================================================
# EDUCATION MATCHING
# ============================================================

def education_matches(
    student_education: Any,
    scholarship_education: Any,
    scholarship_text: str = ""
):
    """
    Match student's education level with scholarship education level.

    Current scholarship schema:
        education_level

    Backward compatibility:
        class_range

    Returns:
        True  -> match
        False -> mismatch
        None  -> insufficient information
    """

    student = normalize(student_education)

    if not student:
        return None

    scholarship_tokens = education_tokens(
        scholarship_education
    )

    # --------------------------------------------------------
    # If normalized education_level is missing,
    # use clearly identifiable eligibility text.
    # --------------------------------------------------------

    if not scholarship_tokens and scholarship_text:

        text = normalize(scholarship_text)

        if (
            "undergraduate" in text
            or "under graduate" in text
            or "bachelor" in text
            or re.search(r"\bug\b", text)
        ):
            scholarship_tokens.add("ug")

        if (
            "postgraduate" in text
            or "post graduate" in text
            or "master" in text
            or re.search(r"\bpg\b", text)
        ):
            scholarship_tokens.add("pg")

        if "phd" in text or "doctoral" in text:
            scholarship_tokens.add("phd")

        if "post-matric" in text or "post_matric" in text:
            scholarship_tokens.add("post_matric")

        if "pre-matric" in text or "pre_matric" in text:
            scholarship_tokens.add("pre_matric")

        if "diploma" in text or "polytechnic" in text:
            scholarship_tokens.add("diploma")

    # Still no usable information
    if not scholarship_tokens:
        return None

    # ========================================================
    # STUDENT = UG
    # ========================================================

    if student in {
        "ug",
        "undergraduate",
        "b.e",
        "be",
        "btech",
        "b.tech",
        "bachelor",
        "degree",
    }:

        if "ug" in scholarship_tokens:
            return True

        # Post-matric scholarships can include UG students
        if "post_matric" in scholarship_tokens:
            return True

        # UG student should not be treated as PG
        if scholarship_tokens.intersection({
            "pg",
            "phd",
        }) and not scholarship_tokens.intersection({
            "ug",
            "post_matric",
        }):
            return False

        if scholarship_tokens.intersection({
            "school",
            "pre_matric",
        }):
            return False

        return None

    # ========================================================
    # STUDENT = PG
    # ========================================================

    if student in {
        "pg",
        "postgraduate",
        "post graduate",
        "masters",
        "master",
        "mtech",
        "m.tech",
        "mba",
        "mca",
    }:

        if "pg" in scholarship_tokens:
            return True

        if "post_matric" in scholarship_tokens:
            return True

        if scholarship_tokens.intersection({
            "ug",
            "school",
            "pre_matric",
        }) and not scholarship_tokens.intersection({
            "pg",
            "post_matric",
        }):
            return False

        return None

    # ========================================================
    # STUDENT = PhD
    # ========================================================

    if student in {
        "phd",
        "doctorate",
        "doctoral",
    }:

        if "phd" in scholarship_tokens:
            return True

        if scholarship_tokens.intersection({
            "ug",
            "pg",
            "school",
            "pre_matric",
        }):
            return False

        return None

    # ========================================================
    # STUDENT = DIPLOMA
    # ========================================================

    if "diploma" in student or "polytechnic" in student:

        if "diploma" in scholarship_tokens:
            return True

        if "post_matric" in scholarship_tokens:
            return True

        if scholarship_tokens.intersection({
            "ug",
            "pg",
            "phd",
            "school",
            "pre_matric",
        }):
            return False

        return None

    # ========================================================
    # STUDENT = SCHOOL
    # ========================================================

    if (
        "school" in student
        or "school" in student_education
    ):

        if (
            "school" in scholarship_tokens
            or "pre_matric" in scholarship_tokens
        ):
            return True

        if scholarship_tokens.intersection({
            "ug",
            "pg",
            "phd",
            "post_matric",
            "diploma",
        }):
            return False

        return None

    # Unknown education level
    return None


# ============================================================
# SPECIAL REQUIREMENTS
# ============================================================

def get_special_requirements(
    scholarship: dict
) -> dict:
    """
    Detect special eligibility requirements from the
    current normalized scholarship schema.

    Reads:
        name
        eligibility
        documents
        benefit
        education_level
    """

    combined_text = " ".join([
        normalize(scholarship.get("name")),
        text_value(scholarship.get("eligibility")),
        text_value(scholarship.get("documents")),
        text_value(scholarship.get("benefit")),
        text_value(scholarship.get("education_level")),
    ])

    requirements = {}

    # --------------------------------------------------------
    # Female
    # --------------------------------------------------------

    female_patterns = [
        "girls only",
        "girl students only",
        "female students only",
        "only for female",
        "only for girls",
        "women students only",
    ]

    if any(
        pattern in combined_text
        for pattern in female_patterns
    ):
        requirements["female"] = True

    # --------------------------------------------------------
    # Disability
    # --------------------------------------------------------

    disability_patterns = [
        "persons with disabilities",
        "person with disability",
        "students with disabilities",
        "students with disability",
        "minimum 40% disability",
        "40% disability",
        "disability scholarship",
        "disability",
    ]

    if any(
        pattern in combined_text
        for pattern in disability_patterns
    ):
        requirements["disability"] = True

    # --------------------------------------------------------
    # North Eastern Region
    # --------------------------------------------------------

    northeast_patterns = [
        "north eastern region",
        "north-east region",
        "north eastern",
        "north-east",
        "northeastern",
        "ner states",
    ]

    if any(
        pattern in combined_text
        for pattern in northeast_patterns
    ):
        requirements["northeast"] = True

    # --------------------------------------------------------
    # Orphan
    # --------------------------------------------------------

    orphan_patterns = [
        "orphan",
        "orphans",
    ]

    if any(
        pattern in combined_text
        for pattern in orphan_patterns
    ):
        requirements["orphan"] = True

    # --------------------------------------------------------
    # Abroad
    # --------------------------------------------------------

    abroad_patterns = [
        "study abroad",
        "studying abroad",
        "foreign university",
        "foreign institution",
        "overseas education",
        "overseas study",
    ]

    if any(
        pattern in combined_text
        for pattern in abroad_patterns
    ):
        requirements["abroad"] = True

    # --------------------------------------------------------
    # Top NIRF
    # --------------------------------------------------------

    if (
        "nirf" in combined_text
        or "top ranked institute" in combined_text
        or "top-ranked institute" in combined_text
    ):
        requirements["top_nirf"] = True

    return requirements


# ============================================================
# CHECK SPECIAL REQUIREMENTS
# ============================================================

def check_special_requirements(
    profile: dict,
    scholarship: dict
) -> dict:
    """
    Check additional requirements such as:
        female
        disability
        northeast
        orphan
        abroad
        top NIRF
    """

    requirements = get_special_requirements(
        scholarship
    )

    matched = []
    verification_reasons = []
    not_matched = []

    # --------------------------------------------------------
    # No special requirements
    # --------------------------------------------------------

    if not requirements:
        return {
            "status": "matched",
            "matched": [],
            "needs_verification": [],
            "not_matched": [],
        }

    # --------------------------------------------------------
    # Female
    # --------------------------------------------------------

    if requirements.get("female"):

        gender = normalize(profile.get("gender"))

        if not gender:
            verification_reasons.append(
                "Scholarship is for female students"
            )

        elif gender in {
            "female",
            "woman",
            "women",
            "girl",
        }:
            matched.append(
                "Female eligibility"
            )

        else:
            not_matched.append(
                "Scholarship is restricted to female students"
            )

    # --------------------------------------------------------
    # Disability
    # --------------------------------------------------------

    if requirements.get("disability"):

        disability = profile.get("disability")

        if disability is None:
            verification_reasons.append(
                "Disability status needs verification"
            )

        elif isinstance(disability, str):
            if normalize(disability) in {
                "yes",
                "true",
                "1",
                "disabled",
                "person with disability",
                "pwd",
            }:
                matched.append(
                    "Disability eligibility"
                )
            else:
                not_matched.append(
                    "Scholarship requires disability eligibility"
                )

        elif disability is True:
            matched.append(
                "Disability eligibility"
            )

        else:
            not_matched.append(
                "Scholarship requires disability eligibility"
            )

    # --------------------------------------------------------
    # North Eastern Region
    # --------------------------------------------------------

    if requirements.get("northeast"):

        state = normalize(profile.get("state"))

        if not state:
            verification_reasons.append(
                "North Eastern Region state needs verification"
            )

        else:

            northeast_states = {
                "assam",
                "arunachal pradesh",
                "manipur",
                "meghalaya",
                "mizoram",
                "nagaland",
                "sikkim",
                "tripura",
            }

            if state in northeast_states:
                matched.append(
                    "North Eastern Region eligibility"
                )
            else:
                not_matched.append(
                    "Student state is outside the North Eastern Region"
                )

    # --------------------------------------------------------
    # Orphan
    # --------------------------------------------------------

    if requirements.get("orphan"):

        orphan = profile.get("orphan")

        if orphan is None:
            verification_reasons.append(
                "Orphan status needs verification"
            )

        elif (
            orphan is True
            or normalize(orphan) in {
                "yes",
                "true",
                "1",
            }
        ):
            matched.append(
                "Orphan eligibility"
            )

        else:
            not_matched.append(
                "Scholarship requires orphan eligibility"
            )

    # --------------------------------------------------------
    # Abroad
    # --------------------------------------------------------

    if requirements.get("abroad"):

        study_location = normalize(
            profile.get("study_location")
        )

        if not study_location:
            verification_reasons.append(
                "Study location needs verification"
            )

        elif study_location in {
            "abroad",
            "foreign",
            "overseas",
        }:
            matched.append(
                "Study abroad eligibility"
            )

        else:
            not_matched.append(
                "Scholarship requires study abroad"
            )

    # --------------------------------------------------------
    # Top NIRF
    # --------------------------------------------------------

    if requirements.get("top_nirf"):

        rank = profile.get(
            "institute_nirf_rank"
        )

        if rank is None:
            verification_reasons.append(
                "Institute NIRF rank needs verification"
            )

        else:
            try:
                if int(rank) <= 100:
                    matched.append(
                        "Top NIRF institute eligibility"
                    )
                else:
                    not_matched.append(
                        "Institute does not satisfy the NIRF rank requirement"
                    )
            except (ValueError, TypeError):
                verification_reasons.append(
                    "Institute NIRF rank needs verification"
                )

    # --------------------------------------------------------
    # Final status
    # --------------------------------------------------------

    if not_matched:
        status = "not_matched"

    elif verification_reasons:
        status = "needs_verification"

    else:
        status = "matched"

    return {
        "status": status,
        "matched": matched,
        "needs_verification": verification_reasons,
        "not_matched": not_matched,
    }


# ============================================================
# SCHOLARSHIP TEXT
# ============================================================

def scholarship_text_for_matching(
    scholarship: dict
) -> str:
    """
    Build searchable text from current scholarship fields.
    """

    fields = [
        scholarship.get("name"),
        scholarship.get("eligibility"),
        scholarship.get("benefit"),
        scholarship.get("documents"),
        scholarship.get("education_level"),
        scholarship.get("category"),
    ]

    return " ".join(
        text_value(field)
        for field in fields
        if field is not None
    )


# ============================================================
# SINGLE SCHOLARSHIP MATCH
# ============================================================

def match_scholarship(
    profile: dict,
    scholarship: dict
) -> dict:
    """
    Match one scholarship against one student profile.

    Returns:
        status
        match_score
        match_reason
        checks
        verification_reasons
    """

    checks = []
    verification_reasons = []

    # ========================================================
    # CATEGORY
    # ========================================================

    category_value = first_present(
        scholarship,
        "category",
    )

    category_result = category_matches(
        profile.get("category"),
        category_value,
    )

    if category_result is True:
        checks.append(
            "Category matches"
        )

    elif category_result is False:
        return {
            "status": "not_matched",
            "match_score": 0,
            "match_reason": (
                "Student category does not satisfy "
                "the scholarship category requirement."
            ),
            "checks": [],
            "verification_reasons": [],
        }

    else:
        verification_reasons.append(
            "Scholarship category information needs verification"
        )

    # ========================================================
    # INCOME
    # ========================================================

    income_limit = first_present(
        scholarship,
        "income_limit",
        "income_max",
    )

    income_result = income_matches(
        profile.get("family_income"),
        income_limit,
    )

    if income_result is True:
        checks.append(
            "Family income satisfies the limit"
        )

    elif income_result is False:
        return {
            "status": "not_matched",
            "match_score": 0,
            "match_reason": (
                "Student family income exceeds "
                "the scholarship income limit."
            ),
            "checks": [],
            "verification_reasons": [],
        }

    else:
        verification_reasons.append(
            "Family income requirement needs verification"
        )

    # ========================================================
    # MARKS
    # ========================================================

    minimum_marks = first_present(
        scholarship,
        "minimum_marks",
        "marks_min",
    )

    marks_result = marks_matches(
        profile.get("marks"),
        minimum_marks,
    )

    if marks_result is True:
        checks.append(
            "Academic marks satisfy the minimum requirement"
        )

    elif marks_result is False:
        return {
            "status": "not_matched",
            "match_score": 0,
            "match_reason": (
                "Student marks are below "
                "the required minimum."
            ),
            "checks": [],
            "verification_reasons": [],
        }

    else:
        verification_reasons.append(
            "Minimum marks requirement needs verification"
        )

    # ========================================================
    # EDUCATION
    # ========================================================

    scholarship_education = first_present(
        scholarship,
        "education_level",
        "class_range",
    )

    scholarship_text = scholarship_text_for_matching(
        scholarship
    )

    education_result = education_matches(
        profile.get("education_level"),
        scholarship_education,
        scholarship_text,
    )

    if education_result is True:
        checks.append(
            "Education level matches"
        )

    elif education_result is False:
        return {
            "status": "not_matched",
            "match_score": 0,
            "match_reason": (
                "Student education level does not "
                "match the scholarship."
            ),
            "checks": [],
            "verification_reasons": [],
        }

    else:
        verification_reasons.append(
            "Education eligibility needs verification"
        )

    # ========================================================
    # SPECIAL REQUIREMENTS
    # ========================================================

    special_result = check_special_requirements(
        profile,
        scholarship,
    )

    if special_result["status"] == "not_matched":
        return {
            "status": "not_matched",
            "match_score": 0,
            "match_reason": "; ".join(
                special_result["not_matched"]
            ),
            "checks": checks,
            "verification_reasons": verification_reasons,
        }

    checks.extend(
        special_result["matched"]
    )

    verification_reasons.extend(
        special_result["needs_verification"]
    )

    # ========================================================
    # SCORE
    # ========================================================

    total_checks = (
        len(checks)
        + len(verification_reasons)
    )

    if total_checks == 0:
        score = 0
        status = "needs_verification"

    else:
        score = round(
            (len(checks) / total_checks) * 100
        )

        if verification_reasons:
            status = "needs_verification"
        else:
            status = "matched"

    # ========================================================
    # REASON
    # ========================================================

    reason_parts = []

    if checks:
        reason_parts.append(
            "Matched: " + ", ".join(checks)
        )

    if verification_reasons:
        reason_parts.append(
            "Verify: " + ", ".join(
                verification_reasons
            )
        )

    if not reason_parts:
        reason_parts.append(
            "Eligibility information needs verification."
        )

    return {
        "status": status,
        "match_score": score,
        "match_reason": " | ".join(reason_parts),
        "checks": checks,
        "verification_reasons": verification_reasons,
    }


# ============================================================
# BACKWARD-COMPATIBLE UI FIELDS
# ============================================================

def add_legacy_display_fields(
    scholarship: dict
) -> dict:
    """
    Preserve compatibility with the existing mobile UI.

    The normalized master dataset uses:
        education_level
        income_limit
        minimum_marks
        eligibility
        application_url

    Older UI code may expect:
        level
        class_range
        income_max
        marks_min
        notes
        how_to_apply

    We add these only to the API response.
    The master dataset itself is NOT modified.
    """

    result = dict(scholarship)

    education = scholarship.get(
        "education_level"
    )

    if isinstance(education, list):
        education_display = ", ".join(
            str(item)
            for item in education
        )
    elif education is None:
        education_display = ""
    else:
        education_display = str(education)

    result["level"] = (
        scholarship.get("level")
        or education_display
    )

    result["class_range"] = (
        scholarship.get("class_range")
        or education_display
    )

    result["income_max"] = first_present(
        scholarship,
        "income_max",
        "income_limit",
    )

    result["marks_min"] = first_present(
        scholarship,
        "marks_min",
        "minimum_marks",
    )

    result["how_to_apply"] = first_present(
        scholarship,
        "how_to_apply",
        "application_url",
    )

    result["notes"] = first_present(
        scholarship,
        "notes",
        "eligibility",
    )

    return result


# ============================================================
# LOAD SCHOLARSHIPS
# ============================================================

def load_scholarships() -> list:
    """
    Load the current master scholarship dataset.
    """

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Scholarship data file not found: {DATA_PATH}"
        )

    with open(
        DATA_PATH,
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    if isinstance(data, dict):

        # Support common wrapper formats
        if "scholarships" in data:
            data = data["scholarships"]

        elif "data" in data:
            data = data["data"]

    if not isinstance(data, list):
        raise ValueError(
            "Scholarship data must be a list."
        )

    return data


# ============================================================
# FIND MATCHING SCHOLARSHIPS
# ============================================================

def find_matching_scholarships(
    profile: dict
) -> list:
    """
    Find scholarships applicable to a student.

    Results are sorted by match score.
    """

    scholarships = load_scholarships()

    results = []

    for scholarship in scholarships:

        if not isinstance(scholarship, dict):
            continue

        match_result = match_scholarship(
            profile,
            scholarship,
        )

        # Completely incompatible scholarships
        if match_result["status"] == "not_matched":
            continue

        # Avoid returning records with absolutely
        # no usable matching information.
        if (
            match_result["match_score"] == 0
            and match_result["status"] == "needs_verification"
        ):
            continue

        result = add_legacy_display_fields(
            scholarship
        )

        # Add matching information
        result["status"] = match_result[
            "status"
        ]

        result["match_score"] = match_result[
            "match_score"
        ]

        result["match_reason"] = match_result[
            "match_reason"
        ]

        result["checks"] = match_result[
            "checks"
        ]

        result["verification_reasons"] = (
            match_result["verification_reasons"]
        )

        results.append(result)

    # ========================================================
    # SORT
    # ========================================================

    results.sort(
        key=lambda item: (
            item.get("match_score", 0),
            item.get("status") == "matched",
        ),
        reverse=True,
    )

    return results


# ============================================================
# OPTIONAL DEBUG FUNCTION
# ============================================================

def debug_profile_matches(
    profile: dict
) -> None:
    """
    Print matching results for debugging.
    """

    results = find_matching_scholarships(
        profile
    )

    print()
    print("=" * 70)
    print("SCHOLARSHIP MATCHING RESULTS")
    print("=" * 70)

    print(
        f"Student: {profile.get('name')}"
    )

    print(
        f"Education: {profile.get('education_level')}"
    )

    print(
        f"Category: {profile.get('category')}"
    )

    print(
        f"Marks: {profile.get('marks')}"
    )

    print(
        f"Family Income: {profile.get('family_income')}"
    )

    print(
        f"\nTotal matches: {len(results)}"
    )

    print("=" * 70)

    for index, scholarship in enumerate(
        results,
        start=1,
    ):

        print(
            f"\n{index}. "
            f"{scholarship.get('name', 'Unknown')}"
        )

        print(
            f"   Score: "
            f"{scholarship.get('match_score', 0)}%"
        )

        print(
            f"   Status: "
            f"{scholarship.get('status')}"
        )

        print(
            f"   Reason: "
            f"{scholarship.get('match_reason')}"
        )

    print()
    print("=" * 70)


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":

    test_profile = {
        "name": "Pooja",
        "email": "pooja@test.com",
        "education_level": "UG",
        "course": "B.E Computer Science",
        "category": "General",
        "gender": "Female",
        "state": None,
        "year": None,
        "marks": 82.0,
        "family_income": 400000.0,
    }

    debug_profile_matches(
        test_profile
    )