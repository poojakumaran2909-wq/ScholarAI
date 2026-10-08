import json
import shutil
from datetime import datetime


MASTER_FILE = "data/scholarships.json"
NSP_FILE = "data/nsp_cleaned.json"
MATCH_FILE = "data/nsp_canonical_matches.json"

BACKUP_FILE = (
    f"data/scholarships_backup_"
    f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
)


def main():

    print("=" * 70)
    print("              SAFE NSP SCHOLARSHIP MERGE")
    print("=" * 70)

    # --------------------------------------------------------
    # Load files
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

    with open(
        MATCH_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        match_report = json.load(f)

    print(
        f"\nExisting master records : {len(master)}"
    )

    print(
        f"NSP records             : {len(nsp)}"
    )

    # --------------------------------------------------------
    # Create backup
    # --------------------------------------------------------

    shutil.copy2(
        MASTER_FILE,
        BACKUP_FILE
    )

    print(
        f"\nBackup created:"
        f"\n{BACKUP_FILE}"
    )

    # --------------------------------------------------------
    # IDs already in master
    # --------------------------------------------------------

    existing_ids = {
        item.get("id")
        for item in master
        if item.get("id")
    }

    # --------------------------------------------------------
    # Only accept records classified as NEW
    # --------------------------------------------------------

    new_results = match_report.get(
        "new_scholarships",
        []
    )

    review_results = match_report.get(
        "needs_review",
        []
    )

    duplicate_results = match_report.get(
        "likely_duplicates",
        []
    )

    print(
        f"\nLikely duplicates : "
        f"{len(duplicate_results)}"
    )

    print(
        f"Needs review      : "
        f"{len(review_results)}"
    )

    print(
        f"New candidates    : "
        f"{len(new_results)}"
    )

    # --------------------------------------------------------
    # Create lookup from NSP ID
    # --------------------------------------------------------

    nsp_by_id = {
        item.get("id"): item
        for item in nsp
        if item.get("id")
    }

    added = []
    skipped_existing = []

    # --------------------------------------------------------
    # Add NEW records only
    # --------------------------------------------------------

    for result in new_results:

        nsp_id = result.get("nsp_id")

        if not nsp_id:
            continue

        # Safety check
        if nsp_id in existing_ids:

            skipped_existing.append(
                result.get("nsp_name")
            )

            continue

        scholarship = nsp_by_id.get(
            nsp_id
        )

        if not scholarship:
            print(
                f"\n⚠ Could not find NSP record:"
                f" {nsp_id}"
            )
            continue

        # Add source tracking
        scholarship["source"] = (
            scholarship.get(
                "source",
                "NSP"
            )
        )

        scholarship["source_url"] = (
            scholarship.get(
                "source_url",
                "https://scholarships.gov.in/"
            )
        )

        scholarship["added_from"] = "NSP"

        scholarship["added_at"] = (
            datetime.now().isoformat()
        )

        master.append(
            scholarship
        )

        existing_ids.add(
            nsp_id
        )

        added.append(
            scholarship.get("name")
        )

    # --------------------------------------------------------
    # Save updated master
    # --------------------------------------------------------

    with open(
        MASTER_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            master,
            f,
            indent=2,
            ensure_ascii=False
        )

    # ========================================================
    # RESULT
    # ========================================================

    print(
        "\n" + "=" * 70
    )

    print(
        "MERGE COMPLETE"
    )

    print(
        "=" * 70
    )

    print(
        f"Before merge : "
        f"{len(master) - len(added)}"
    )

    print(
        f"Added        : "
        f"{len(added)}"
    )

    print(
        f"After merge  : "
        f"{len(master)}"
    )

    # --------------------------------------------------------
    # Added scholarships
    # --------------------------------------------------------

    print(
        "\n" + "=" * 70
    )

    print(
        "ADDED SCHOLARSHIPS"
    )

    print(
        "=" * 70
    )

    for name in added:

        print(
            f"➕ {name}"
        )

    # --------------------------------------------------------
    # Safety information
    # --------------------------------------------------------

    print(
        "\n" + "=" * 70
    )

    print(
        "NOT MERGED"
    )

    print(
        "=" * 70
    )

    print(
        f"Duplicates skipped : "
        f"{len(duplicate_results)}"
    )

    print(
        f"Reviews skipped    : "
        f"{len(review_results)}"
    )

    print(
        "\nFAISS was NOT modified."
    )

    print(
        "Backup available at:"
    )

    print(
        BACKUP_FILE
    )

    print(
        "=" * 70
    )


if __name__ == "__main__":
    main()