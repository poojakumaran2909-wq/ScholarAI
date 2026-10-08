import json
from collections import Counter

MASTER_FILE = "data/scholarships.json"
OUTPUT_FILE = "data/master_validation_report.json"


def is_empty(value):
    return value is None or value == "" or value == [] or value == {}


def get_list(record, key):
    value = record.get(key)

    if value is None:
        return []

    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]

    if isinstance(value, str) and value.strip():
        return [value.strip()]

    return []


def validate_record(record, index):

    errors = []
    warnings = []

    # Only these are truly required
    required_fields = [
        "id",
        "name",
        "source",
    ]

    for field in required_fields:
        if is_empty(record.get(field)):
            errors.append(
                f"Missing required field: {field}"
            )

    # source_url is useful but not mandatory
    if is_empty(record.get("source_url")):
        warnings.append("Source URL is missing")

    # Education
    education = get_list(
        record,
        "education_level"
    )

    valid_education = {
        "school",
        "pre_matric",
        "post_matric",
        "diploma",
        "ug",
        "pg",
        "phd",
    }

    invalid_education = [
        x for x in education
        if x.lower() not in valid_education
    ]

    if invalid_education:
        warnings.append(
            "Unknown education level: "
            + ", ".join(invalid_education)
        )

    if not education:
        warnings.append(
            "Education level is missing"
        )

    # Category
    if not get_list(record, "category"):
        warnings.append(
            "Category is missing"
        )

    # Eligibility
    if is_empty(record.get("eligibility")):
        warnings.append(
            "Eligibility information is missing"
        )

    # Benefit
    if is_empty(record.get("benefit")):
        warnings.append(
            "Benefit information is missing"
        )

    # Documents
    if not get_list(record, "documents"):
        warnings.append(
            "Documents list is missing"
        )

    # Deadline
    if is_empty(record.get("deadline")):
        warnings.append(
            "Deadline is missing"
        )

    # URL checks
    source_url = record.get("source_url")

    if source_url:
        if not str(source_url).startswith(
            ("http://", "https://")
        ):
            warnings.append(
                "Source URL does not look valid"
            )

    application_url = record.get(
        "application_url"
    )

    if application_url:
        if not str(application_url).startswith(
            ("http://", "https://")
        ):
            warnings.append(
                "Application URL does not look valid"
            )

    return {
        "index": index,
        "id": record.get("id"),
        "name": record.get("name"),
        "errors": errors,
        "warnings": warnings,
    }


def main():

    print("=" * 70)
    print("          MASTER SCHOLARSHIP VALIDATOR V2")
    print("=" * 70)

    with open(
        MASTER_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        scholarships = json.load(f)

    print(
        f"\nTotal scholarships : {len(scholarships)}"
    )

    results = []

    for index, scholarship in enumerate(
        scholarships
    ):
        results.append(
            validate_record(
                scholarship,
                index
            )
        )

    # Duplicate IDs
    ids = [
        x.get("id")
        for x in scholarships
        if x.get("id")
    ]

    counts = Counter(ids)

    duplicate_ids = {
        key: value
        for key, value in counts.items()
        if value > 1
    }

    # Classify
    invalid = []
    review = []
    good = []

    for result in results:

        if result["errors"]:
            invalid.append(result)

        elif result["warnings"]:
            review.append(result)

        else:
            good.append(result)

    report = {
        "summary": {
            "total": len(scholarships),
            "good": len(good),
            "needs_review": len(review),
            "invalid": len(invalid),
            "duplicate_ids": len(duplicate_ids),
        },
        "duplicate_ids": duplicate_ids,
        "invalid_records": invalid,
        "needs_review": review,
        "good_records": good,
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

    print("\n" + "=" * 70)
    print("VALIDATION RESULT")
    print("=" * 70)

    print(
        f"Total records : {len(scholarships)}"
    )

    print(
        f"Good          : {len(good)}"
    )

    print(
        f"Needs review  : {len(review)}"
    )

    print(
        f"Invalid       : {len(invalid)}"
    )

    print(
        f"Duplicate IDs : {len(duplicate_ids)}"
    )

    if invalid:

        print("\n" + "=" * 70)
        print("INVALID RECORDS")
        print("=" * 70)

        for item in invalid:

            print(
                f"\n❌ {item['name']}"
            )

            for error in item["errors"]:
                print(
                    f"   ERROR: {error}"
                )

    print("\n" + "=" * 70)
    print(
        f"Report saved to: {OUTPUT_FILE}"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()