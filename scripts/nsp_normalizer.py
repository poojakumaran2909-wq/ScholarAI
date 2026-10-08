import json
import os
import re
from copy import deepcopy


INPUT_FILE = "data/nsp_candidates.json"
OUTPUT_FILE = "data/nsp_cleaned.json"


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):
    if value is None:
        return None

    if not isinstance(value, str):
        return value

    value = value.replace("\n", " ")
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def unique(items):
    result = []

    for item in items:
        if item and item not in result:
            result.append(item)

    return result


# ============================================================
# EDUCATION
# ============================================================

def normalize_education(s):
    name = clean_text(s.get("name", "")) or ""
    text = name.lower()

    education = []

    # Explicit title rules
    if "pre matric" in text:
        education.append("pre_matric")

    if "post matric" in text:
        education.append("post_matric")

    if "in schools" in text:
        education.append("school")

    if "in college" in text:
        education.append("ug")

    if "technical diploma" in text:
        education.append("diploma")

    if "technical degree" in text:
        education.append("ug")

    if "under graduate and post graduate" in text:
        education = ["ug", "pg"]

    elif "under graduate" in text:
        education.append("ug")

    if "post graduate" in text:
        education.append("pg")

    # ISI
    if "under graduate and post graduate studies" in text:
        education = ["ug", "pg"]

    # ICAR NTS
    if "nts-ug" in text or "nts ug" in text:
        education = ["ug"]

    if "nts-pg" in text or "nts pg" in text:
        education = ["pg"]

    # ICAR PGS
    if "(pgs)" in text:
        education = ["pg"]

    # ICAR research fellowships
    if "junior research fellowship" in text:
        education = ["pg", "phd"]

    if "senior research fellowship" in text:
        education = ["pg", "phd"]

    # CSSS
    if "csss" in text:
        benefit = clean_text(s.get("benefit", "")) or ""

        if "graduate / postgraduate" in benefit.lower():
            education = ["ug", "pg"]

    # NMMS
    if "national means cum merit" in text:
        education = ["school"]

    # ST higher education
    if "higher education of st students" in text:
        education = ["ug", "pg"]

    # NEC higher professional courses
    if "higher professional courses" in text:
        education = ["ug", "pg"]

    # Railway scholarship
    if "ministry of railways" in text:
        education = ["ug"]

    # PM-USP J&K/Ladakh
    if "jammu kashmir and ladakh" in text:
        education = ["ug"]

    return unique(education)


# ============================================================
# CATEGORY
# ============================================================

def normalize_category(s):
    name = clean_text(s.get("name", "")) or ""
    text = name.lower()

    categories = []

    if "pm yasasvi" in text:
        if "obc" in text:
            categories.append("OBC")

        if "ebc" in text:
            categories.append("EBC")

        if "dnt" in text:
            categories.append("DNT")

    if re.search(r"\bsc\b", text) or "scs" in text:
        categories.append("SC")

    if "st students" in text:
        categories.append("ST")

    if re.search(r"\bobc\b", text):
        categories.append("OBC")

    if re.search(r"\bebc\b", text):
        categories.append("EBC")

    if re.search(r"\bdnt\b", text):
        categories.append("DNT")

    return unique(categories)


# ============================================================
# BENEFIT CLEANING
# ============================================================

def clean_benefit(benefit):
    if not benefit:
        return None

    benefit = clean_text(benefit)

    if not benefit:
        return None

    benefit = benefit.replace("Rs.2,000I.", "Rs. 2,000")
    benefit = benefit.replace("Rs 3,000/.", "Rs. 3,000")
    benefit = benefit.replace("Rs 3,000.", "Rs. 3,000")
    benefit = benefit.replace("Rs. 120001", "Rs. 12,000")
    benefit = benefit.replace("Rs. 4000", "Rs. 4,000")
    benefit = benefit.replace("2500/-", "Rs. 2,500")
    benefit = benefit.replace("3000/-", "Rs. 3,000")

    benefit = re.sub(r"\s+", " ", benefit)

    return benefit.strip()


# ============================================================
# BENEFIT NORMALIZATION
# ============================================================

def normalize_benefit(s):
    name = clean_text(s.get("name", "")) or ""
    name_lower = name.lower()

    benefit = clean_benefit(
        s.get("benefit")
    )

    # --------------------------------------------------------
    # ICAR NTS
    # --------------------------------------------------------

    if "nts-ug" in name_lower or "nts ug" in name_lower:
        return (
            "Rs. 2,000 per month for undergraduate students "
            "and Rs. 3,000 per month for postgraduate students",
            "normalized"
        )

    if "nts-pg" in name_lower or "nts pg" in name_lower:
        return (
            "Rs. 3,000 per month for postgraduate students",
            "normalized"
        )

    # --------------------------------------------------------
    # AICTE
    # --------------------------------------------------------

    if "pragati" in name_lower:
        return (
            "Rs. 50,000 per annum for every year of study",
            "normalized"
        )

    if "saksham" in name_lower:
        return (
            "Rs. 50,000 per annum for every year of study",
            "normalized"
        )

    if "swanath" in name_lower:
        return (
            "Rs. 50,000 per annum for every year of study",
            "normalized"
        )

    # --------------------------------------------------------
    # NMMS
    # --------------------------------------------------------

    if "national means cum merit" in name_lower:
        return (
            "Rs. 12,000 per annum",
            "normalized"
        )

    # --------------------------------------------------------
    # RAILWAYS
    # --------------------------------------------------------

    if "ministry of railways" in name_lower:
        return (
            "Rs. 2,500 per month for male students; "
            "Rs. 3,000 per month for female students",
            "normalized"
        )

    # --------------------------------------------------------
    # FREE COACHING
    # --------------------------------------------------------

    if "free coaching" in name_lower:
        if benefit and "4000" in benefit.replace(",", ""):
            return (
                "Rs. 4,000 per month stipend for the duration "
                "of the course, not exceeding 12 months",
                "normalized"
            )

    # --------------------------------------------------------
    # CSSS
    # --------------------------------------------------------

    if "csss" in name_lower:
        # The collector's extracted text gives scholarship count,
        # not the actual scholarship amount.
        return None, "needs_review"

    # --------------------------------------------------------
    # Bad extracted benefit patterns
    # --------------------------------------------------------

    if benefit:

        bad_patterns = [
            "recovery of paid amount",
            "receipt of financial assistance",
            "acknowledged by the fellow",
            "intellectual property",
            "selected student will be eligible",
            "stipulated in the following table",
            "quantum of financial assistance",
            "rates of scholarship",
            "amount in rs",
            "components of scholarship",
            "scholarship/financial assistance",
        ]

        lower = benefit.lower()

        if any(x in lower for x in bad_patterns):
            return None, "needs_review"

    # --------------------------------------------------------
    # Generic useful benefit
    # --------------------------------------------------------

    if benefit:

        has_money = bool(
            re.search(
                r"(rs\.?|₹|inr)\s*[\d,]+",
                benefit.lower()
            )
        )

        if has_money:
            return benefit, "accepted"

    return None, "missing"


# ============================================================
# SPECIAL REQUIREMENTS
# ============================================================

def special_requirements(s):
    name = clean_text(s.get("name", "")) or ""
    text = name.lower()

    result = []

    if "disabilities" in text or "specially abled" in text:
        result.append("disability")

    if "pragati scholarship scheme for girl" in text:
        result.append("female")

    if "girl students" in text:
        result.append("female")

    if "ner" in text or "north eastern" in text:
        result.append("northeast")

    if "jammu kashmir" in text or "ladakh" in text:
        result.append("jammu_kashmir_ladakh")

    return unique(result)


# ============================================================
# QUALITY
# ============================================================

def quality_status(s):

    flags = []
    notes = []

    education = s.get("education_level", [])
    benefit = s.get("benefit")

    specification_status = s.get(
        "specification_status"
    )

    if not education:
        flags.append("education_needs_review")
        notes.append(
            "Education level could not be determined "
            "with sufficient confidence."
        )

    if not benefit:
        flags.append("benefit_needs_review")
        notes.append(
            "No reliable benefit amount/description "
            "was available."
        )

    if specification_status == "missing_url":
        flags.append("missing_specification")
        notes.append(
            "Official specification URL was not available."
        )

    elif specification_status == "empty":
        flags.append("empty_specification")
        notes.append(
            "Specification was fetched but contained "
            "no usable extracted information."
        )

    if (
        "missing_specification" in flags
        or "empty_specification" in flags
    ):
        status = "incomplete"

    elif flags:
        status = "review"

    else:
        status = "good"

    return status, flags, notes


# ============================================================
# NORMALIZE
# ============================================================

def normalize_one(original):

    s = deepcopy(original)

    s["name"] = clean_text(
        s.get("name")
    )

    # Education
    s["education_level"] = normalize_education(s)

    # Category
    s["category"] = normalize_category(s)

    # Benefit
    benefit, benefit_source = normalize_benefit(s)

    s["benefit"] = benefit

    # Special requirements
    s["special_requirements"] = special_requirements(s)

    # Quality
    status, flags, notes = quality_status(s)

    s["data_quality"] = {
        "quality_status": status,
        "quality_flags": flags,
        "normalization_notes": notes
    }

    s["normalization"] = {
        "benefit_source": benefit_source
    }

    return s


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("          NSP NORMALIZER V2")
    print("=" * 60)

    if not os.path.exists(INPUT_FILE):
        print(
            f"\nERROR: {INPUT_FILE} not found."
        )
        return

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        scholarships = json.load(f)

    cleaned = []

    for i, scholarship in enumerate(
        scholarships,
        start=1
    ):

        result = normalize_one(
            scholarship
        )

        cleaned.append(result)

        print(
            f"\n[{i}/{len(scholarships)}] "
            f"{result.get('name')}"
        )

        print(
            "   Education:",
            result.get("education_level")
        )

        print(
            "   Category:",
            result.get("category")
        )

        print(
            "   Benefit:",
            result.get("benefit")
        )

        print(
            "   Special:",
            result.get("special_requirements")
        )

        print(
            "   Quality:",
            result["data_quality"]["quality_status"]
        )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            cleaned,
            f,
            indent=2,
            ensure_ascii=False
        )

    # ========================================================
    # SUMMARY
    # ========================================================

    good = 0
    review = 0
    incomplete = 0

    for s in cleaned:

        status = s[
            "data_quality"
        ]["quality_status"]

        if status == "good":
            good += 1

        elif status == "review":
            review += 1

        elif status == "incomplete":
            incomplete += 1

    print("\n")
    print("=" * 60)
    print("              V2 SUMMARY")
    print("=" * 60)

    print(
        "Input scholarships :",
        len(scholarships)
    )

    print(
        "Cleaned scholarships:",
        len(cleaned)
    )

    print(
        "Good               :",
        good
    )

    print(
        "Needs review       :",
        review
    )

    print(
        "Incomplete         :",
        incomplete
    )

    print(
        "\nSaved:",
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()