import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import hashlib
import json
import os


BASE_URL = "https://www.ugc.gov.in"

CANDIDATE_FILE = "data/ugc_candidates.json"


# ==================================================
# Generate stable scholarship ID
# ==================================================

def generate_scholarship_id(source, name):

    unique_text = (
        f"{source.lower()}:{name.strip().lower()}"
    )

    hash_value = hashlib.sha256(
        unique_text.encode("utf-8")
    ).hexdigest()[:12]

    return f"{source.lower()}_{hash_value}"


# ==================================================
# Fetch webpage
# ==================================================

def fetch_page(url):

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/153.0 Safari/537.36"
        )
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    return response.text


# ==================================================
# Discover UGC scholarship links
# ==================================================

def discover_scholarship_links():

    url = BASE_URL + "/Home/student_Corner"

    print("\n🌐 Fetching UGC Student Corner...")
    print(url)

    html = fetch_page(url)

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    scholarship_links = set()

    for link in soup.find_all(
        "a",
        href=True
    ):

        href = link["href"].strip()

        full_url = urljoin(
            BASE_URL,
            href
        )

        if "/Scholarships/" in full_url:

            scholarship_links.add(
                full_url
            )

    return sorted(
        scholarship_links
    )


# ==================================================
# Extract text from scholarship page
# ==================================================

def extract_lines(html):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    for element in soup(
        ["script", "style", "noscript"]
    ):

        element.decompose()

    text = soup.get_text(
        separator="\n"
    )

    lines = []

    for line in text.splitlines():

        line = line.strip()

        if line:

            lines.append(line)

    return lines


# ==================================================
# Get field value
# ==================================================

def get_field(
    lines,
    field_name
):

    for i, line in enumerate(lines):

        if line.lower() == field_name.lower():

            if i + 1 < len(lines):

                return lines[i + 1]

    return ""


# ==================================================
# Extract one scholarship
# ==================================================

def extract_scholarship(url):

    print(
        f"\n🔎 Extracting:\n{url}"
    )

    html = fetch_page(url)

    lines = extract_lines(
        html
    )

    name = get_field(
        lines,
        "Name of the Scheme:"
    )

    objective = get_field(
        lines,
        "Objective:"
    )

    eligibility = get_field(
        lines,
        "Eligibility:"
    )

    slots = get_field(
        lines,
        "Slots:"
    )

    tenure = get_field(
        lines,
        "Tenure:"
    )

    financial_assistance = get_field(
        lines,
        "Financial Assistance:"
    )

    remark = get_field(
        lines,
        "Remark:"
    )

    scholarship_id = generate_scholarship_id(
        "UGC",
        name
    )

    scholarship = {

        "id": scholarship_id,

        "name": name,

        "level": "UG/PG",

        "category": [],

        "class_range": "",

        "income_max": None,

        "marks_min": None,

        "benefit": financial_assistance,

        "documents": [],

        "how_to_apply": remark,

        "deadline": "",

        "source": "UGC",

        "source_url": url,

        "notes": (
            f"Objective: {objective}\n"
            f"Eligibility: {eligibility}\n"
            f"Slots: {slots}\n"
            f"Tenure: {tenure}"
        )
    }

    return scholarship


# ==================================================
# Validate scholarship
# ==================================================

def validate_scholarship(scholarship):

    required_fields = [
        "id",
        "name",
        "source",
        "source_url"
    ]

    missing_fields = []

    for field in required_fields:

        value = scholarship.get(field)

        if value is None or str(value).strip() == "":

            missing_fields.append(
                field
            )

    if missing_fields:

        return False, (
            "Missing required fields: "
            + ", ".join(missing_fields)
        )

    return True, "Valid"


# ==================================================
# Load existing candidates
# ==================================================

def load_existing_candidates():

    if not os.path.exists(
        CANDIDATE_FILE
    ):

        return []

    try:

        with open(
            CANDIDATE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

            if isinstance(data, list):

                return data

            return []

    except json.JSONDecodeError:

        print(
            "⚠️ Existing candidate file is invalid."
        )

        return []


# ==================================================
# Save candidates
# ==================================================

def save_candidates(
    scholarships
):

    os.makedirs(
        os.path.dirname(
            CANDIDATE_FILE
        ),
        exist_ok=True
    )

    with open(
        CANDIDATE_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            scholarships,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(
        f"\n💾 Saved {len(scholarships)} "
        f"candidate scholarship(s)"
    )

    print(
        f"📁 File: {CANDIDATE_FILE}"
    )


# ==================================================
# Remove duplicate scholarships
# ==================================================

def remove_duplicates(
    scholarships
):

    unique = {}

    for scholarship in scholarships:

        scholarship_id = scholarship.get(
            "id"
        )

        if scholarship_id:

            unique[
                scholarship_id
            ] = scholarship

    return list(
        unique.values()
    )


# ==================================================
# Process collected scholarships
# ==================================================

def process_candidates(
    collected_scholarships
):

    existing = load_existing_candidates()

    print(
        f"\n📂 Existing candidates: "
        f"{len(existing)}"
    )

    valid_scholarships = []

    # --------------------------------------------------
    # Validate newly collected records
    # --------------------------------------------------

    for scholarship in collected_scholarships:

        is_valid, message = validate_scholarship(
            scholarship
        )

        if not is_valid:

            print(
                "\n❌ Invalid scholarship:"
            )

            print(
                scholarship.get(
                    "name",
                    "Unknown"
                )
            )

            print(
                f"   Reason: {message}"
            )

            continue

        print(
            "\n✅ Valid:",
            scholarship["name"]
        )

        valid_scholarships.append(
            scholarship
        )

    # --------------------------------------------------
    # Combine old + new
    # --------------------------------------------------

    combined = (
        existing
        + valid_scholarships
    )

    # --------------------------------------------------
    # Remove duplicates using stable ID
    # --------------------------------------------------

    before_count = len(
        combined
    )

    combined = remove_duplicates(
        combined
    )

    after_count = len(
        combined
    )

    duplicates_removed = (
        before_count - after_count
    )

    print(
        f"\n♻️ Duplicates removed: "
        f"{duplicates_removed}"
    )

    return combined


# ==================================================
# Display scholarship
# ==================================================

def display_scholarship(
    scholarship,
    number
):

    print(
        "\n" + "=" * 60
    )

    print(
        f"🎓 SCHOLARSHIP {number}"
    )

    print(
        "=" * 60
    )

    print(
        "ID:",
        scholarship["id"]
    )

    print(
        "Name:",
        scholarship["name"]
    )

    print(
        "Benefit:",
        scholarship["benefit"]
    )

    print(
        "Source:",
        scholarship["source"]
    )

    print(
        "URL:",
        scholarship["source_url"]
    )


# ==================================================
# Main
# ==================================================

if __name__ == "__main__":

    print(
        "\n🚀 Starting UGC Scholarship Collector..."
    )

    try:

        # --------------------------------------------------
        # Step 1: Discover
        # --------------------------------------------------

        links = discover_scholarship_links()

        print(
            f"\n🎓 Found {len(links)} "
            f"UGC scholarship link(s)"
        )

        # --------------------------------------------------
        # Step 2: Extract
        # --------------------------------------------------

        scholarships = []

        for link in links:

            try:

                scholarship = extract_scholarship(
                    link
                )

                scholarships.append(
                    scholarship
                )

            except Exception as e:

                print(
                    f"\n❌ Failed to extract:"
                )

                print(link)

                print(
                    f"   Error: {e}"
                )

        # --------------------------------------------------
        # Step 3: Validate + deduplicate
        # --------------------------------------------------

        final_candidates = process_candidates(
            scholarships
        )

        # --------------------------------------------------
        # Step 4: Save candidates
        # --------------------------------------------------

        save_candidates(
            final_candidates
        )

        # --------------------------------------------------
        # Step 5: Display
        # --------------------------------------------------

        print(
            "\n\n" + "#" * 60
        )

        print(
            "📚 UGC CANDIDATE SCHOLARSHIPS"
        )

        print(
            "#" * 60
        )

        for index, scholarship in enumerate(
            final_candidates,
            start=1
        ):

            display_scholarship(
                scholarship,
                index
            )

        print(
            "\n🎉 UGC collection completed!"
        )

        print(
            "\n⚠️ Production scholarships.json "
            "was NOT modified."
        )

        print(
            "⚠️ FAISS was NOT modified."
        )

    except Exception as e:

        print(
            f"\n❌ Collector failed:"
        )

        print(e)