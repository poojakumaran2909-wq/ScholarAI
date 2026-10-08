import json
import re


MASTER_FILE = "data/scholarships.json"
NSP_FILE = "data/nsp_cleaned.json"


def normalize_name(name):
    if not name:
        return ""

    name = name.lower()

    # Remove common source-specific words
    remove_words = [
        "merit based scheme",
        "welfare based scheme",
        "scholarship",
        "scheme",
        "central sector",
        "special",
        "for",
        "the",
        "and",
        "of",
        "students",
    ]

    for word in remove_words:
        name = name.replace(word, " ")

    # Normalize punctuation
    name = re.sub(
        r"[^a-z0-9\s]",
        " ",
        name
    )

    name = re.sub(
        r"\s+",
        " ",
        name
    )

    return name.strip()


def token_overlap(a, b):

    a_tokens = set(
        normalize_name(a).split()
    )

    b_tokens = set(
        normalize_name(b).split()
    )

    if not a_tokens or not b_tokens:
        return 0.0

    intersection = a_tokens & b_tokens

    smaller = min(
        len(a_tokens),
        len(b_tokens)
    )

    return len(intersection) / smaller


def main():

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

    print("=" * 70)
    print("             NSP SANITY DUPLICATE CHECK")
    print("=" * 70)

    possible = []

    for nsp_item in nsp:

        best_score = 0
        best_master = None

        for master_item in master:

            score = token_overlap(
                nsp_item.get("name", ""),
                master_item.get("name", "")
            )

            if score > best_score:

                best_score = score
                best_master = master_item

        if best_master and best_score >= 0.60:

            possible.append({
                "nsp": nsp_item,
                "master": best_master,
                "score": best_score
            })

    print(
        f"\nPossible same-name families: "
        f"{len(possible)}"
    )

    print("\n" + "=" * 70)
    print("                 POSSIBLE MATCHES")
    print("=" * 70)

    for i, item in enumerate(
        possible,
        start=1
    ):

        print(
            f"\n{i}. NSP:"
        )

        print(
            "   ",
            item["nsp"].get("name")
        )

        print(
            "   MASTER:"
        )

        print(
            "   ",
            item["master"].get("name")
        )

        print(
            "   Token overlap:",
            round(item["score"], 3)
        )

    print("\n" + "=" * 70)
    print("Done.")
    print("=" * 70)


if __name__ == "__main__":
    main()