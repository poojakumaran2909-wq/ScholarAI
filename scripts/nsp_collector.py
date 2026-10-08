import json
import os
import re
import hashlib
import time
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader


# ============================================================
# CONFIG
# ============================================================

NSP_URL = "https://scholarships.gov.in/All-Scholarships"

OUTPUT_FILE = "data/nsp_candidates.json"

BASE_URL = "https://scholarships.gov.in"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0.0.0 Safari/537.36"
    )
}

TIMEOUT = 30
PDF_RETRIES = 3
RETRY_DELAY = 2


# ============================================================
# JSON
# ============================================================

def save_json(file_path, data):

    folder = os.path.dirname(file_path)

    if folder:
        os.makedirs(folder, exist_ok=True)

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


# ============================================================
# TEXT HELPERS
# ============================================================

def normalize_text(text):

    if not text:
        return ""

    text = str(text)

    text = text.replace("\x00", " ")

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def normalize_name(name):

    name = normalize_text(name)

    return (
        name
        .replace("“", "")
        .replace("”", "")
        .replace('"', "")
        .strip()
    )


# ============================================================
# STABLE ID
# ============================================================

def generate_scholarship_id(
    source,
    name
):

    unique_text = (
        f"{source.lower()}:"
        f"{normalize_name(name).lower()}"
    )

    hash_value = hashlib.sha256(
        unique_text.encode("utf-8")
    ).hexdigest()[:12]

    return f"{source.lower()}_{hash_value}"


# ============================================================
# HTTP
# ============================================================

def fetch_url(
    url,
    retries=3
):

    for attempt in range(1, retries + 1):

        try:

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=TIMEOUT
            )

            response.raise_for_status()

            return response

        except requests.RequestException as e:

            print(
                f"   ⚠️ Attempt "
                f"{attempt}/{retries} failed: {e}"
            )

            if attempt < retries:

                time.sleep(RETRY_DELAY)

    return None


# ============================================================
# INVALID TITLES
# ============================================================

INVALID_TITLES = {
    "accessibility controls",
    "accessibility",
    "skip to main content",
    "skip to content",
    "screen reader access",
    "menu",
    "home",
    "login",
}


def is_valid_scholarship_name(name):

    name = normalize_text(name)

    if not name:
        return False

    lower = name.lower()

    if lower in INVALID_TITLES:
        return False

    bad_keywords = [
        "accessibility controls",
        "skip to",
        "screen reader",
        "font size",
        "change language",
    ]

    for keyword in bad_keywords:

        if keyword in lower:
            return False

    if len(name) < 15:
        return False

    return True


# ============================================================
# DATES
# ============================================================

def extract_open_date(text):

    patterns = [

        r"Scheme\s+Open\s+from"
        r"(?:\s*\(for\s+Renewal\))?"
        r"\s*:\s*(\d{2}-\d{2}-\d{4})",

        r"Scheme\s+Open\s+from"
        r"\s*:\s*(\d{2}-\d{2}-\d{4})",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            return match.group(1)

    return None


def extract_deadline(text):

    patterns = [

        r"Student\s+Application\s+Open\s+till"
        r"(?:\s*\(for\s+Renewal\))?"
        r"\s*:\s*(\d{2}-\d{2}-\d{4})",

        r"Student\s+Application\s+Closed\s+on"
        r"(?:\s*\(for\s+Renewal\))?"
        r"\s*:\s*(\d{2}-\d{2}-\d{4})",

        r"Student\s+Application\s+Open\s+till"
        r"\s*:\s*(\d{2}-\d{2}-\d{4})",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            return match.group(1)

    return None


# ============================================================
# SCHEME TYPE
# ============================================================

def extract_scheme_type(
    name,
    text
):

    combined = (
        normalize_text(name)
        + " "
        + normalize_text(text)
    ).lower()

    if "merit based scheme" in combined:
        return "merit_based"

    if "welfare based scheme" in combined:
        return "welfare_based"

    return None


# ============================================================
# FIND SCHOLARSHIP CARDS
# ============================================================

def find_scholarship_cards(soup):

    cards = []

    headings = soup.find_all(
        [
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
        ]
    )

    for heading in headings:

        name = normalize_name(
            heading.get_text(
                " ",
                strip=True
            )
        )

        if not is_valid_scholarship_name(name):
            continue

        current = heading
        found_card = None

        for _ in range(8):

            current = current.parent

            if current is None:
                break

            spec_link = current.find(
                "a",
                string=lambda text:
                text and
                "Specifications" in text
            )

            if spec_link:

                found_card = current
                break

        if found_card is None:
            continue

        spec_link = found_card.find(
            "a",
            string=lambda text:
            text and
            "Specifications" in text
        )

        if spec_link is None:
            continue

        href = spec_link.get("href")

        if not href:

            specification_url = None

        elif href.lower().strip() in {
            "null",
            "#",
            "javascript:void(0)",
            "javascript:void(0);",
        }:

            specification_url = None

        else:

            specification_url = urljoin(
                BASE_URL,
                href
            )

        card_text = normalize_text(
            found_card.get_text(
                " ",
                strip=True
            )
        )

        if any(
            item["name"] == name
            for item in cards
        ):
            continue

        cards.append({
            "name": name,
            "card_text": card_text,
            "specification_url":
                specification_url
        })

    return cards


# ============================================================
# PDF EXTRACTION
# ============================================================

def extract_pdf_text(pdf_bytes):

    temp_file = "data/_nsp_temp.pdf"

    try:

        os.makedirs(
            "data",
            exist_ok=True
        )

        with open(
            temp_file,
            "wb"
        ) as f:

            f.write(pdf_bytes)

        reader = PdfReader(
            temp_file
        )

        pages = []

        for page in reader.pages:

            try:

                text = page.extract_text()

                if text:
                    pages.append(text)

            except Exception:
                continue

        return "\n".join(pages)

    except Exception as e:

        print(
            "   ⚠️ PDF parsing failed:",
            e
        )

        return ""

    finally:

        try:

            if os.path.exists(temp_file):
                os.remove(temp_file)

        except Exception:
            pass


def clean_pdf_text(text):

    if not text:
        return ""

    text = text.replace(
        "\x00",
        " "
    )

    # Normalize common PDF spacing problems
    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


# ============================================================
# SECTION EXTRACTION
# ============================================================

def get_lines(text):

    return [
        normalize_text(line)
        for line in text.splitlines()
        if normalize_text(line)
    ]


def find_section(
    lines,
    start_keywords,
    end_keywords=None,
    max_lines=30
):

    end_keywords = end_keywords or []

    start_index = None

    for i, line in enumerate(lines):

        lower = line.lower()

        if any(
            keyword in lower
            for keyword in start_keywords
        ):

            start_index = i
            break

    if start_index is None:
        return []

    collected = []

    for line in lines[start_index + 1:]:

        lower = line.lower()

        if any(
            keyword in lower
            for keyword in end_keywords
        ):

            break

        if line:
            collected.append(line)

        if len(collected) >= max_lines:
            break

    return collected


# ============================================================
# EDUCATION LEVEL - V4
# ============================================================

def extract_education_level(
    name,
    pdf_text
):

    """
    IMPORTANT:
    Do NOT scan the entire PDF for UG/PG.

    First use scholarship title.
    Then use the eligibility section.
    """

    name_lower = normalize_text(
        name
    ).lower()

    levels = []

    # --------------------------------------------------------
    # 1. Strong title-based rules
    # --------------------------------------------------------

    if (
        "pre matric" in name_lower
        or "pre-matric" in name_lower
    ):

        levels.append("pre_matric")

    if (
        "post matric" in name_lower
        or "post-matric" in name_lower
    ):

        levels.append("post_matric")

    if (
        "technical diploma" in name_lower
        or "diploma" in name_lower
    ):

        levels.append("diploma")

    if (
        "technical degree" in name_lower
        or "under graduate" in name_lower
        or "undergraduate" in name_lower
        or "under-graduate" in name_lower
    ):

        levels.append("ug")

    if (
        "post graduate" in name_lower
        or "postgraduate" in name_lower
        or "post-graduate" in name_lower
    ):

        levels.append("pg")

    if (
        "ph.d" in name_lower
        or "phd" in name_lower
        or "doctoral" in name_lower
    ):

        levels.append("phd")

    # --------------------------------------------------------
    # 2. Special title cases
    # --------------------------------------------------------

    if (
        "under graduate and post graduate"
        in name_lower
    ):

        levels = [
            "ug",
            "pg"
        ]

    if (
        "under graduate"
        in name_lower
        and
        "post graduate"
        in name_lower
    ):

        levels = [
            "ug",
            "pg"
        ]

    # --------------------------------------------------------
    # 3. Use eligibility section ONLY if title
    #    didn't provide enough information
    # --------------------------------------------------------

    if not levels:

        lines = get_lines(pdf_text)

        eligibility_lines = find_section(
            lines,
            [
                "eligibility criteria",
                "eligibility for scholarship",
                "eligibility",
            ],
            [
                "amount of scholarship",
                "quantum of financial assistance",
                "rate of scholarship",
                "documents",
                "how to apply",
            ],
            max_lines=25
        )

        eligibility_text = " ".join(
            eligibility_lines
        ).lower()

        # Explicit phrases only
        if re.search(
            r"\bclass\s*(?:9|10|11|12)\b",
            eligibility_text
        ):

            # School-level evidence
            if (
                "class 9" in eligibility_text
                or "class 10" in eligibility_text
                or "class 11" in eligibility_text
                or "class 12" in eligibility_text
            ):

                levels.append(
                    "school"
                )

        if (
            "under graduate"
            in eligibility_text
            or "undergraduate"
            in eligibility_text
        ):

            levels.append("ug")

        if (
            "post graduate"
            in eligibility_text
            or "postgraduate"
            in eligibility_text
        ):

            levels.append("pg")

        if (
            "ph.d"
            in eligibility_text
            or "phd"
            in eligibility_text
            or "doctoral"
            in eligibility_text
        ):

            levels.append("phd")

    return list(
        dict.fromkeys(levels)
    )


# ============================================================
# CATEGORY
# ============================================================

def extract_categories(
    name,
    pdf_text
):

    name_lower = normalize_text(
        name
    ).lower()

    # Use title strongly first
    category_map = {

        "SC": [
            "sc",
            "scheduled caste",
            "scheduled castes"
        ],

        "ST": [
            "st",
            "scheduled tribe",
            "scheduled tribes"
        ],

        "OBC": [
            "obc",
            "other backward class",
            "other backward classes"
        ],

        "EBC": [
            "ebc",
            "economically backward class"
        ],

        "DNT": [
            "dnt",
            "denotified tribe"
        ],

        "Minority": [
            "minority",
            "minorities"
        ],
    }

    categories = []

    for category, keywords in category_map.items():

        for keyword in keywords:

            # Avoid treating random "st" letters as ST
            if keyword in {
                "sc",
                "st"
            }:

                found = re.search(
                    rf"\b{keyword}\b",
                    name_lower
                )

            else:

                found = keyword in name_lower

            if found:

                categories.append(category)
                break

    # If title has no category, inspect only
    # eligibility section.
    if not categories:

        lines = get_lines(pdf_text)

        eligibility_lines = find_section(
            lines,
            [
                "eligibility criteria",
                "eligibility for scholarship",
                "eligibility",
            ],
            [
                "amount of scholarship",
                "quantum of financial assistance",
                "documents",
                "how to apply",
            ],
            max_lines=25
        )

        text = " ".join(
            eligibility_lines
        ).lower()

        for category, keywords in category_map.items():

            for keyword in keywords:

                if keyword in {
                    "sc",
                    "st"
                }:

                    found = re.search(
                        rf"\b{keyword}\b",
                        text
                    )

                else:

                    found = keyword in text

                if found:

                    categories.append(
                        category
                    )

                    break

    return list(
        dict.fromkeys(categories)
    )


# ============================================================
# INCOME
# ============================================================

def extract_income_max(pdf_text):

    if not pdf_text:
        return None

    lines = get_lines(pdf_text)

    eligibility_lines = find_section(
        lines,
        [
            "eligibility criteria",
            "eligibility for scholarship",
            "eligibility",
        ],
        [
            "amount of scholarship",
            "quantum of financial assistance",
            "rate of scholarship",
            "documents",
            "how to apply",
        ],
        max_lines=30
    )

    text = " ".join(
        eligibility_lines
    ).lower()

    if not text:
        text = pdf_text.lower()

    # Lakhs
    patterns = [

        r"(?:family\s+income|"
        r"parental\s+income|"
        r"annual\s+family\s+income|"
        r"income\s+from\s+all\s+sources)"
        r".{0,180}?"
        r"rs\.?\s*"
        r"([\d,.]+)"
        r"\s*(?:lakh|lakhs|lac|lacs)",

        r"(?:family\s+income|"
        r"parental\s+income|"
        r"annual\s+family\s+income|"
        r"income\s+from\s+all\s+sources)"
        r".{0,180}?"
        r"₹\s*"
        r"([\d,.]+)"
        r"\s*(?:lakh|lakhs|lac|lacs)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            try:

                value = float(
                    match.group(1)
                    .replace(",", "")
                )

                return value * 100000

            except ValueError:
                pass

    # Direct rupees
    direct_patterns = [

        r"(?:family\s+income|"
        r"parental\s+income|"
        r"income\s+from\s+all\s+sources)"
        r".{0,150}?"
        r"rs\.?\s*"
        r"([\d,]+)"
        r"\s*(?:per annum|per year|annually)",

        r"(?:family\s+income|"
        r"parental\s+income)"
        r".{0,150}?"
        r"₹\s*"
        r"([\d,]+)"
        r"\s*(?:per annum|per year|annually)",
    ]

    for pattern in direct_patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            try:

                return float(
                    match.group(1)
                    .replace(",", "")
                )

            except ValueError:
                pass

    return None


# ============================================================
# MARKS
# ============================================================

def extract_marks_min(pdf_text):

    if not pdf_text:
        return None

    lines = get_lines(pdf_text)

    eligibility_lines = find_section(
        lines,
        [
            "eligibility criteria",
            "eligibility for scholarship",
            "eligibility",
        ],
        [
            "amount of scholarship",
            "quantum of financial assistance",
            "documents",
            "how to apply",
        ],
        max_lines=30
    )

    text = " ".join(
        eligibility_lines
    ).lower()

    patterns = [

        r"(?:minimum|at least)"
        r".{0,80}?"
        r"(\d+(?:\.\d+)?)\s*%"
        r".{0,80}?"
        r"(?:marks|percentage)",

        r"(?:marks|percentage)"
        r".{0,80}?"
        r"(?:minimum|at least)"
        r".{0,80}?"
        r"(\d+(?:\.\d+)?)\s*%",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            try:
                return float(
                    match.group(1)
                )

            except ValueError:
                pass

    return None


# ============================================================
# BENEFIT - V4
# ============================================================

def extract_benefit(pdf_text):

    if not pdf_text:
        return None

    lines = get_lines(pdf_text)

    # --------------------------------------------------------
    # Look specifically for benefit headings.
    # --------------------------------------------------------

    benefit_headings = [
        "amount of scholarship",
        "quantum of financial assistance",
        "rate of scholarship",
        "scholarship amount",
        "amount of financial assistance",
        "financial assistance",
        "scholarship will be",
        "scholarship shall be",
    ]

    end_headings = [
        "documents to be uploaded",
        "documents required",
        "documents to be submitted",
        "how to apply",
        "application process",
        "selection procedure",
        "renewal",
        "payment procedure",
        "terms and conditions",
    ]

    # --------------------------------------------------------
    # Find best heading
    # --------------------------------------------------------

    start_index = None

    for i, line in enumerate(lines):

        lower = line.lower()

        # Prefer explicit amount/rate headings
        if any(
            heading in lower
            for heading in benefit_headings[:6]
        ):

            start_index = i
            break

    # If no heading exists, look for
    # actual amount-bearing lines.
    if start_index is None:

        amount_pattern = re.compile(
            r"(₹|rs\.?)\s*[\d,]+",
            re.IGNORECASE
        )

        for i, line in enumerate(lines):

            lower = line.lower()

            if (
                amount_pattern.search(line)
                and (
                    "scholarship" in lower
                    or "stipend" in lower
                    or "allowance" in lower
                    or "financial assistance" in lower
                )
            ):

                start_index = i
                break

    if start_index is None:
        return None

    # --------------------------------------------------------
    # Collect only a small benefit section
    # --------------------------------------------------------

    collected = []

    for line in lines[start_index:]:

        lower = line.lower()

        # Stop at next major section
        if (
            len(collected) > 0
            and any(
                heading in lower
                for heading in end_headings
            )
        ):

            break

        # Don't accidentally absorb income conditions
        if (
            "family income"
            in lower
            and "amount" not in lower
            and "rate" not in lower
        ):

            continue

        if (
            "income from all sources"
            in lower
        ):

            continue

        if line:

            collected.append(line)

        if len(collected) >= 8:
            break

    if not collected:
        return None

    # --------------------------------------------------------
    # Clean OCR/PDF garbage
    # --------------------------------------------------------

    text = " ".join(
        collected
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    text = re.sub(
        r"\b\d+\.?\d*\s*$",
        "",
        text
    )

    text = text.strip(
        " :-"
    )

    # Don't return huge paragraphs
    if len(text) > 500:

        # Try to keep sentences containing
        # actual monetary information.
        sentences = re.split(
            r"(?<=[.!?])\s+",
            text
        )

        useful = []

        for sentence in sentences:

            lower = sentence.lower()

            if (
                "rs." in lower
                or "₹" in sentence
                or "per month" in lower
                or "per annum" in lower
                or "stipend" in lower
                or "allowance" in lower
            ):

                useful.append(
                    sentence
                )

        if useful:

            text = " ".join(
                useful[:3]
            )

    if len(text) > 500:

        text = text[:500].rstrip() + "..."

    return text if text else None


# ============================================================
# DOCUMENTS
# ============================================================

def extract_documents(pdf_text):

    if not pdf_text:
        return []

    lines = get_lines(pdf_text)

    document_lines = find_section(
        lines,
        [
            "documents to be uploaded",
            "documents required",
            "documents to be submitted",
            "documents needed",
        ],
        [
            "how to apply",
            "application process",
            "selection procedure",
            "renewal",
        ],
        max_lines=30
    )

    documents = []

    for line in document_lines:

        if len(line) < 8:
            continue

        if len(line) > 300:
            continue

        lower = line.lower()

        if (
            "page" in lower
            and len(line) < 30
        ):
            continue

        documents.append(line)

    return list(
        dict.fromkeys(documents)
    )


# ============================================================
# ELIGIBILITY
# ============================================================

def extract_eligibility(pdf_text):

    if not pdf_text:
        return None

    lines = get_lines(pdf_text)

    eligibility_lines = find_section(
        lines,
        [
            "eligibility criteria",
            "eligibility for scholarship",
            "eligibility",
        ],
        [
            "amount of scholarship",
            "quantum of financial assistance",
            "rate of scholarship",
            "documents",
            "how to apply",
        ],
        max_lines=15
    )

    if not eligibility_lines:
        return None

    text = " ".join(
        eligibility_lines
    )

    if len(text) > 1500:
        text = text[:1500].rstrip() + "..."

    return text


# ============================================================
# NOTES
# ============================================================

def build_notes(
    scheme_type,
    pdf_text
):

    notes = []

    if scheme_type:

        notes.append(
            f"Scheme type: {scheme_type}."
        )

    lower = pdf_text.lower()

    if (
        "national scholarship portal"
        in lower
    ):

        notes.append(
            "Application information "
            "references the National "
            "Scholarship Portal."
        )

    if "dbt" in lower:

        notes.append(
            "The official guidelines "
            "mention DBT/payment transfer."
        )

    if not notes:
        return None

    return " ".join(notes)


# ============================================================
# DEEP EXTRACTION
# ============================================================

def enrich_from_specification(
    scholarship
):

    url = scholarship.get(
        "specification_url"
    )

    if not url:

        scholarship[
            "specification_status"
        ] = "missing_url"

        return scholarship

    print(
        "   📄 Fetching specification..."
    )

    response = fetch_url(
        url,
        retries=PDF_RETRIES
    )

    if response is None:

        scholarship[
            "specification_status"
        ] = "failed"

        return scholarship

    content_type = response.headers.get(
        "Content-Type",
        ""
    ).lower()

    if (
        "html" in content_type
        and not response.content.startswith(
            b"%PDF"
        )
    ):

        scholarship[
            "specification_status"
        ] = "not_pdf"

        return scholarship

    pdf_text = extract_pdf_text(
        response.content
    )

    pdf_text = clean_pdf_text(
        pdf_text
    )

    if not pdf_text:

        scholarship[
            "specification_status"
        ] = "empty"

        return scholarship

    # --------------------------------------------------------
    # Extract
    # --------------------------------------------------------

    education = extract_education_level(
        scholarship["name"],
        pdf_text
    )

    categories = extract_categories(
        scholarship["name"],
        pdf_text
    )

    income = extract_income_max(
        pdf_text
    )

    marks = extract_marks_min(
        pdf_text
    )

    benefit = extract_benefit(
        pdf_text
    )

    documents = extract_documents(
        pdf_text
    )

    eligibility = extract_eligibility(
        pdf_text
    )

    notes = build_notes(
        scholarship.get("scheme_type"),
        pdf_text
    )

    # --------------------------------------------------------
    # Save extracted fields
    # --------------------------------------------------------

    scholarship[
        "education_levels"
    ] = education

    scholarship[
        "category"
    ] = categories

    scholarship[
        "income_max"
    ] = income

    scholarship[
        "marks_min"
    ] = marks

    scholarship[
        "benefit"
    ] = benefit

    scholarship[
        "documents"
    ] = documents

    scholarship[
        "eligibility"
    ] = eligibility

    scholarship[
        "notes"
    ] = notes

    scholarship[
        "specification_status"
    ] = "success"

    return scholarship


# ============================================================
# VALIDATION
# ============================================================

def validate_scholarship(
    scholarship
):

    required_fields = [
        "id",
        "name",
        "source",
        "source_url",
    ]

    for field in required_fields:

        if not scholarship.get(field):

            return False

    if not is_valid_scholarship_name(
        scholarship["name"]
    ):

        return False

    return True


# ============================================================
# DEDUPLICATION
# ============================================================

def deduplicate_scholarships(
    scholarships
):

    unique = {}
    duplicates = 0

    for scholarship in scholarships:

        scholarship_id = scholarship.get(
            "id"
        )

        if not scholarship_id:
            continue

        if scholarship_id in unique:

            duplicates += 1
            continue

        unique[
            scholarship_id
        ] = scholarship

    return (
        list(unique.values()),
        duplicates
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print(
        "\n" + "=" * 60
    )

    print(
        "🎓 NSP SCHOLARSHIP COLLECTOR v4"
    )

    print(
        "=" * 60
    )

    # --------------------------------------------------------
    # FETCH NSP
    # --------------------------------------------------------

    print(
        "\n🌐 Fetching official NSP page..."
    )

    print(
        "URL:",
        NSP_URL
    )

    response = fetch_url(
        NSP_URL,
        retries=3
    )

    if response is None:

        print(
            "\n❌ Could not fetch NSP."
        )

        exit()

    print(
        "HTTP status:",
        response.status_code
    )

    # --------------------------------------------------------
    # PARSE
    # --------------------------------------------------------

    print(
        "\n📥 Parsing NSP scholarship cards..."
    )

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    cards = find_scholarship_cards(
        soup
    )

    print(
        "\n🔎 Scholarship cards found:",
        len(cards)
    )

    # --------------------------------------------------------
    # CREATE RECORDS
    # --------------------------------------------------------

    scholarships = []

    for card in cards:

        name = card["name"]

        card_text = card["card_text"]

        specification_url = (
            card["specification_url"]
        )

        scholarship = {

            "id": generate_scholarship_id(
                "nsp",
                name
            ),

            "name": name,

            "level": None,

            "category": [],

            "class_range": None,

            "education_levels": [],

            "income_max": None,

            "marks_min": None,

            "benefit": None,

            "deadline": extract_deadline(
                card_text
            ),

            "open_date": extract_open_date(
                card_text
            ),

            "documents": [],

            "eligibility": None,

            "how_to_apply": (
                "Apply through the "
                "National Scholarship Portal."
            ),

            "source": (
                "National Scholarship Portal"
            ),

            "source_url": NSP_URL,

            "specification_url":
                specification_url,

            "scheme_type":
                extract_scheme_type(
                    name,
                    card_text
                ),

            "notes": None,

            "active": True,

            "specification_status":
                "pending",

            "last_checked":
                datetime.now(
                    timezone.utc
                ).isoformat(),
        }

        scholarships.append(
            scholarship
        )

    # --------------------------------------------------------
    # DEDUPLICATE
    # --------------------------------------------------------

    scholarships, duplicate_count = (
        deduplicate_scholarships(
            scholarships
        )
    )

    # --------------------------------------------------------
    # DEEP EXTRACTION
    # --------------------------------------------------------

    print(
        "\n" + "=" * 60
    )

    print(
        "📄 DEEP EXTRACTION"
    )

    print(
        "=" * 60
    )

    total = len(
        scholarships
    )

    for index, scholarship in enumerate(
        scholarships,
        start=1
    ):

        print(
            f"\n[{index}/{total}] "
            f"{scholarship['name']}"
        )

        enrich_from_specification(
            scholarship
        )

        print(
            "   Open:",
            scholarship.get(
                "open_date"
            )
        )

        print(
            "   Deadline:",
            scholarship.get(
                "deadline"
            )
        )

        print(
            "   Type:",
            scholarship.get(
                "scheme_type"
            )
        )

        print(
            "   Education:",
            scholarship.get(
                "education_levels"
            )
        )

        print(
            "   Category:",
            scholarship.get(
                "category"
            )
        )

        print(
            "   Income max:",
            scholarship.get(
                "income_max"
            )
        )

        print(
            "   Marks min:",
            scholarship.get(
                "marks_min"
            )
        )

        benefit = scholarship.get(
            "benefit"
        )

        if benefit and len(benefit) > 180:

            benefit_display = (
                benefit[:180]
                + "..."
            )

        else:

            benefit_display = benefit

        print(
            "   Benefit:",
            benefit_display
        )

        print(
            "   Specification:",
            scholarship.get(
                "specification_status"
            )
        )

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    valid = []
    invalid = 0

    for scholarship in scholarships:

        if validate_scholarship(
            scholarship
        ):

            valid.append(
                scholarship
            )

        else:

            invalid += 1

            print(
                "\n⚠️ Invalid scholarship:",
                scholarship.get(
                    "name",
                    "Unknown"
                )
            )

    scholarships = valid

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    save_json(
        OUTPUT_FILE,
        scholarships
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    successful_specs = sum(
        1
        for scholarship in scholarships
        if scholarship.get(
            "specification_status"
        ) == "success"
    )

    failed_specs = sum(
        1
        for scholarship in scholarships
        if scholarship.get(
            "specification_status"
        ) == "failed"
    )

    missing_urls = sum(
        1
        for scholarship in scholarships
        if scholarship.get(
            "specification_status"
        ) == "missing_url"
    )

    empty_specs = sum(
        1
        for scholarship in scholarships
        if scholarship.get(
            "specification_status"
        ) == "empty"
    )

    not_pdf = sum(
        1
        for scholarship in scholarships
        if scholarship.get(
            "specification_status"
        ) == "not_pdf"
    )

    print(
        "\n" + "=" * 60
    )

    print(
        "📊 NSP COLLECTION SUMMARY"
    )

    print(
        "=" * 60
    )

    print(
        "Raw scholarships:",
        len(cards)
    )

    print(
        "Duplicates removed:",
        duplicate_count
    )

    print(
        "Valid scholarships:",
        len(scholarships)
    )

    print(
        "Invalid scholarships:",
        invalid
    )

    print(
        "Specification success:",
        successful_specs
    )

    print(
        "Specification failed:",
        failed_specs
    )

    print(
        "Missing specification URL:",
        missing_urls
    )

    print(
        "Empty specification:",
        empty_specs
    )

    print(
        "Not PDF:",
        not_pdf
    )

    print(
        "\n💾 Saved to:",
        OUTPUT_FILE
    )

    print(
        "\n🎉 NSP collection completed!"
    )

    print(
        "=" * 60
    )