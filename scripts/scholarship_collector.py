import json
import requests
from bs4 import BeautifulSoup


# ==================================================
# Paths
# ==================================================

SOURCES_FILE = "data/scholarship_sources.json"


# ==================================================
# Load configured sources
# ==================================================

def load_sources():

    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        sources = json.load(f)

    return sources


# ==================================================
# Fetch webpage
# ==================================================

def fetch_page(url):

    print(f"\n🌐 Fetching: {url}")

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

    print(
        f"✅ Page fetched successfully "
        f"(Status: {response.status_code})"
    )

    return response.text


# ==================================================
# Extract visible text
# ==================================================

def extract_text(html):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # Remove unnecessary elements
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
# Collect from source
# ==================================================

def collect_source(source):

    print("\n" + "=" * 60)

    print(
        f"📚 Source: {source['name']}"
    )

    print(
        f"🔗 URL: {source['url']}"
    )

    print("=" * 60)

    try:

        html = fetch_page(
            source["url"]
        )

        lines = extract_text(
            html
        )

        print(
            f"📄 Extracted {len(lines)} text lines"
        )

        print("\n--- SAMPLE CONTENT ---")

        for line in lines[:50]:

            print(line)

        print("\n--- END SAMPLE ---")

        return lines

    except Exception as e:

        print(
            f"❌ Error collecting source: {e}"
        )

        return []


# ==================================================
# Main
# ==================================================

if __name__ == "__main__":

    print(
        "\n🚀 Starting Scholarship Collector..."
    )

    sources = load_sources()

    print(
        f"📚 Loaded {len(sources)} configured sources"
    )

    for source in sources:

        if not source.get("enabled", False):

            print(
                f"⏭️ Skipping disabled source: "
                f"{source['name']}"
            )

            continue

        collect_source(
            source
        )

    print(
        "\n🎉 Scholarship collection test completed!"
    )