import json
import shutil
from datetime import datetime


MASTER_FILE = "data/scholarships.json"


# ============================================================
# DUPLICATE GROUPS CONFIRMED FOR CLEANUP
# ============================================================

DUPLICATE_GROUPS = [
    {
        "canonical_name": "Ishan Uday Special Scholarship Scheme for North Eastern Region",
        "ids": [
            "ishan_uday_ne",
            "ugc_3c301904ef9f"
        ]
    }
]


# ============================================================
# BACKUP
# ============================================================

BACKUP_FILE = (
    f"data/scholarships_before_duplicate_cleanup_"
    f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
)


# ============================================================
# MERGE HELPER
# ============================================================

def merge_records(records):

    # Start with the first record
    merged = records[0].copy()

    # Fill missing information from other records
    for record in records[1:]:

        for key, value in record.items():

            current_value = merged.get(key)

            # ------------------------------------------------
            # Missing value
            # ------------------------------------------------

            if current_value is None or current_value == "" or current_value == []:

                if value is not None and value != "" and value != []:
                    merged[key] = value

                continue

            # ------------------------------------------------
            # Merge lists
            # ------------------------------------------------

            if isinstance(current_value, list) and isinstance(value, list):

                combined = current_value + value

                unique_values = []

                for item in combined:

                    if item not in unique_values:
                        unique_values.append(item)

                merged[key] = unique_values

    return merged


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("             MASTER DUPLICATE CLEANUP")
    print("=" * 70)

    # --------------------------------------------------------
    # Load master
    # --------------------------------------------------------

    with open(
        MASTER_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        master = json.load(f)

    print(
        f"\nOriginal master records : {len(master)}"
    )

    # --------------------------------------------------------
    # Backup
    # --------------------------------------------------------

    shutil.copy2(
        MASTER_FILE,
        BACKUP_FILE
    )

    print(
        f"Backup created:\n{BACKUP_FILE}"
    )

    # --------------------------------------------------------
    # Process duplicate groups
    # --------------------------------------------------------

    ids_to_remove = set()

    replacement_records = {}

    for group in DUPLICATE_GROUPS:

        target_ids = set(group["ids"])

        matching_records = [
            record
            for record in master
            if record.get("id") in target_ids
        ]

        if len(matching_records) < 2:

            print(
                f"\n⚠️ Could not find all records for:"
                f" {group['canonical_name']}"
            )

            continue

        print()
        print("-" * 70)

        print(
            f"Duplicate group:"
            f" {group['canonical_name']}"
        )

        for record in matching_records:

            print(
                f"  • {record.get('id')} | "
                f"{record.get('name')}"
            )

        # ----------------------------------------------------
        # Prefer existing master record as base
        # ----------------------------------------------------

        base_record = None

        for record in matching_records:

            if record.get("id") == "ishan_uday_ne":

                base_record = record.copy()
                break

        if base_record is None:
            base_record = matching_records[0].copy()

        # ----------------------------------------------------
        # Merge information from all duplicate records
        # ----------------------------------------------------

        merged = merge_records(
            [base_record] +
            [
                record
                for record in matching_records
                if record.get("id") != base_record.get("id")
            ]
        )

        # ----------------------------------------------------
        # Keep canonical ID
        # ----------------------------------------------------

        merged["id"] = base_record["id"]

        merged["name"] = group["canonical_name"]

        merged["duplicate_sources"] = [
            record.get("source")
            for record in matching_records
            if record.get("source")
        ]

        merged["merged_record_ids"] = [
            record.get("id")
            for record in matching_records
        ]

        merged["last_checked"] = datetime.now().strftime(
            "%Y-%m-%d"
        )

        replacement_records[
            base_record["id"]
        ] = merged

        # Remove all duplicate IDs except canonical ID
        for record in matching_records:

            if record.get("id") != base_record.get("id"):

                ids_to_remove.add(
                    record.get("id")
                )

        print(
            f"\n✅ Keeping canonical record:"
            f" {base_record['id']}"
        )

        print(
            f"🗑️ Removing duplicate:"
            f" ugc_3c301904ef9f"
        )

    # --------------------------------------------------------
    # Build cleaned master
    # --------------------------------------------------------

    cleaned_master = []

    already_added = set()

    for record in master:

        record_id = record.get("id")

        # Skip duplicate records
        if record_id in ids_to_remove:
            continue

        # Replace canonical record with merged version
        if record_id in replacement_records:

            record = replacement_records[
                record_id
            ]

        if record_id not in already_added:

            cleaned_master.append(record)

            already_added.add(record_id)

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    with open(
        MASTER_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            cleaned_master,
            f,
            indent=2,
            ensure_ascii=False
        )

    # --------------------------------------------------------
    # Result
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("CLEANUP COMPLETE")
    print("=" * 70)

    print(
        f"Before : {len(master)}"
    )

    print(
        f"Removed duplicates : "
        f"{len(master) - len(cleaned_master)}"
    )

    print(
        f"After  : {len(cleaned_master)}"
    )

    print()
    print(
        "FAISS was NOT modified."
    )

    print(
        f"Backup : {BACKUP_FILE}"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()