import json
import os


MASTER_FILE = "data/scholarships.json"
CANDIDATE_FILE = "data/ugc_candidates.json"


# ==================================================
# Load JSON
# ==================================================

def load_json(file_path):

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# ==================================================
# Save JSON
# ==================================================

def save_json(
    file_path,
    data
):

    with open(
        file_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )


# ==================================================
# Compare scholarship content
# ==================================================

def scholarship_changed(
    old,
    new
):

    # Ignore these fields when comparing
    ignored_fields = {
        "content_hash"
    }

    old_data = {
        key: value
        for key, value in old.items()
        if key not in ignored_fields
    }

    new_data = {
        key: value
        for key, value in new.items()
        if key not in ignored_fields
    }

    return old_data != new_data


# ==================================================
# Merge candidates
# ==================================================

def merge_scholarships(
    master,
    candidates
):

    # --------------------------------------------------
    # Create ID → scholarship map
    # --------------------------------------------------

    master_map = {}

    for scholarship in master:

        scholarship_id = scholarship.get(
            "id"
        )

        if scholarship_id:

            master_map[
                str(scholarship_id)
            ] = scholarship

    added = []
    updated = []
    unchanged = []

    # --------------------------------------------------
    # Process candidates
    # --------------------------------------------------

    for candidate in candidates:

        candidate_id = candidate.get(
            "id"
        )

        if not candidate_id:

            print(
                "⚠️ Skipping candidate without ID:",
                candidate.get(
                    "name",
                    "Unknown"
                )
            )

            continue

        candidate_id = str(
            candidate_id
        )

        # --------------------------------------------------
        # NEW
        # --------------------------------------------------

        if candidate_id not in master_map:

            master.append(
                candidate
            )

            master_map[
                candidate_id
            ] = candidate

            added.append(
                candidate
            )

        # --------------------------------------------------
        # EXISTING
        # --------------------------------------------------

        else:

            existing = master_map[
                candidate_id
            ]

            if scholarship_changed(
                existing,
                candidate
            ):

                # Find original record
                for index, scholarship in enumerate(
                    master
                ):

                    if str(
                        scholarship.get("id")
                    ) == candidate_id:

                        master[index] = candidate

                        break

                master_map[
                    candidate_id
                ] = candidate

                updated.append(
                    candidate
                )

            else:

                unchanged.append(
                    candidate
                )

    return (
        master,
        added,
        updated,
        unchanged
    )


# ==================================================
# Main
# ==================================================

if __name__ == "__main__":

    print(
        "\n🚀 Starting Scholarship Merge..."
    )

    # --------------------------------------------------
    # Check files
    # --------------------------------------------------

    if not os.path.exists(
        MASTER_FILE
    ):

        print(
            f"❌ Master file not found: "
            f"{MASTER_FILE}"
        )

        exit()

    if not os.path.exists(
        CANDIDATE_FILE
    ):

        print(
            f"❌ Candidate file not found: "
            f"{CANDIDATE_FILE}"
        )

        exit()

    # --------------------------------------------------
    # Load files
    # --------------------------------------------------

    master = load_json(
        MASTER_FILE
    )

    candidates = load_json(
        CANDIDATE_FILE
    )

    print(
        f"📚 Master scholarships: "
        f"{len(master)}"
    )

    print(
        f"📥 Candidate scholarships: "
        f"{len(candidates)}"
    )

    # --------------------------------------------------
    # Merge
    # --------------------------------------------------

    (
        master,
        added,
        updated,
        unchanged
    ) = merge_scholarships(
        master,
        candidates
    )

    # --------------------------------------------------
    # Display results
    # --------------------------------------------------

    print(
        f"\n🆕 Added: {len(added)}"
    )

    for scholarship in added:

        print(
            "   ➕",
            scholarship.get(
                "name",
                "Unknown"
            )
        )

    print(
        f"\n🔄 Updated: {len(updated)}"
    )

    for scholarship in updated:

        print(
            "   🔄",
            scholarship.get(
                "name",
                "Unknown"
            )
        )

    print(
        f"\n✅ Unchanged: {len(unchanged)}"
    )

    for scholarship in unchanged:

        print(
            "   ⏭️",
            scholarship.get(
                "name",
                "Unknown"
            )
        )

    # --------------------------------------------------
    # Save master file
    # --------------------------------------------------

    save_json(
        MASTER_FILE,
        master
    )

    print(
        f"\n💾 Master dataset saved."
    )

    print(
        f"📊 Total scholarships now: "
        f"{len(master)}"
    )

    print(
        "\n🎉 Scholarship merge completed!"
    )