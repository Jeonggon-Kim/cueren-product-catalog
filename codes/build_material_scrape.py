"""
build_material_scrape.py

Scrape 135 product pages from cueren.com, extract Upper material info,
cross-reference with partial audit, and generate a final audit CSV.
"""

import csv
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT_CSV          = os.path.join(BASE_DIR, "data", "material_code_audit.csv")
ALL_COLLECTIONS    = os.path.join(BASE_DIR, "data", "all_collections.json")
PARTIAL_AUDIT_CSV  = os.path.join(BASE_DIR, "data", "palantir", "cueren_material_official_audit_partial.csv")
OUTPUT_CSV         = os.path.join(BASE_DIR, "data", "palantir", "material_code_full_audit.csv")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Korean prefix for upper material label
UPPER_PREFIX = "\uc5b4\ud37c "   # "어퍼 "
MATERIAL_HEADER = "MATERIAL"

# ---------------------------------------------------------------------------
# 1. Load inputs
# ---------------------------------------------------------------------------
def load_audit_unknowns():
    """Return list of dicts for rows with extraction_source == 'UNKNOWN'."""
    with open(AUDIT_CSV, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    return [r for r in rows if r.get("extraction_source", "").strip() == "UNKNOWN"]


def load_url_map():
    """Return dict: product_id (str) -> url (str)."""
    with open(ALL_COLLECTIONS, "r", encoding="utf-8") as f:
        data = json.load(f)
    url_map = {}
    for col_data in data.values():
        for prod in col_data.get("products", []):
            pid = str(prod.get("product_id", ""))
            url = prod.get("url", "")
            if pid and url:
                url_map[pid] = url
    return url_map


def load_partial_audit():
    """Return dict: source_product_id (str) -> dict row from partial audit."""
    partial = {}
    with open(PARTIAL_AUDIT_CSV, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            pid = str(row.get("source_product_id", "")).strip()
            if pid:
                partial[pid] = row
    return partial


# ---------------------------------------------------------------------------
# 2. Scrape one page
# ---------------------------------------------------------------------------
def scrape_upper_material(url: str) -> str:
    """
    GET the product page and extract the upper material string.
    Returns the material string, or "" if not found / error.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.content, "html.parser")
        lines = [l.strip() for l in soup.get_text(separator="\n").split("\n") if l.strip()]

        for i, line in enumerate(lines):
            if line == MATERIAL_HEADER:
                # Look ahead for the upper material line
                for j in range(i + 1, min(len(lines), i + 20)):
                    if lines[j].startswith(UPPER_PREFIX):
                        return lines[j][len(UPPER_PREFIX):].strip()
                break   # Found MATERIAL section but no upper line in range
        return ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# 3. Parallel scrape with rate limiting
# ---------------------------------------------------------------------------
def scrape_all(products, url_map, max_workers=4, sleep_between=0.4):
    """
    Scrape all products with ThreadPoolExecutor.
    Returns dict: product_id -> upper_material_scraped (str)
    """
    results = {}

    def task(row):
        pid = str(row["source_product_id"]).strip()
        url = url_map.get(pid, "")
        if not url:
            return pid, ""
        time.sleep(sleep_between)
        mat = scrape_upper_material(url)
        return pid, mat

    done = 0
    total = len(products)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(task, row): row for row in products}
        for future in as_completed(futures):
            pid, mat = future.result()
            results[pid] = mat
            done += 1
            if done % 20 == 0 or done == total:
                print(f"  Scraped {done}/{total} ...", flush=True)

    return results


# ---------------------------------------------------------------------------
# 4. Cross-reference & determine match status
# ---------------------------------------------------------------------------
def compare_materials(scraped: str, official: str) -> str:
    """Return match status string."""
    has_scraped  = bool(scraped.strip())
    has_official = bool(official.strip())

    if not has_scraped and not has_official:
        return "NOT_FOUND"
    if has_scraped and not has_official:
        return "SCRAPE_ONLY"
    if not has_scraped and has_official:
        return "PARTIAL_ONLY"

    # Both present — compare ignoring whitespace and case
    if scraped.strip().lower() == official.strip().lower():
        return "MATCH"
    return "CONFLICT"


def determine_material_code(scraped: str):
    """
    Conservative rule:
    - Patent (case-insensitive) in scraped material → PL
    - Else → ""
    """
    if scraped and "patent" in scraped.lower():
        return "PL", "SCRAPE_CONFIRMED"
    return "", ""


# ---------------------------------------------------------------------------
# 5. Build output rows
# ---------------------------------------------------------------------------
def build_output_rows(unknowns, scraped_map, partial_map):
    rows = []
    for prod in unknowns:
        pid = str(prod["source_product_id"]).strip()
        scraped_mat  = scraped_map.get(pid, "")
        partial_row  = partial_map.get(pid, {})
        official_mat = partial_row.get("upper_material_official", "").strip()

        match_status = compare_materials(scraped_mat, official_mat)
        mat_code, evidence = determine_material_code(scraped_mat)

        notes = ""
        if match_status == "CONFLICT":
            notes = f"scraped='{scraped_mat}' vs partial='{official_mat}'"

        rows.append({
            "source_product_id":    pid,
            "product_name":         prod.get("product_name", "").strip(),
            "collection":           prod.get("collection", "").strip(),
            "section":              prod.get("section", "").strip(),
            "raw_color":            prod.get("raw_color", "").strip(),
            "upper_material_scraped": scraped_mat,
            "upper_material_partial": official_mat,
            "scrape_match_status":  match_status,
            "material_code":        mat_code,
            "material_code_evidence": evidence,
            "notes":                notes,
        })
    return rows


# ---------------------------------------------------------------------------
# 6. Write CSV
# ---------------------------------------------------------------------------
FIELDNAMES = [
    "source_product_id", "product_name", "collection", "section",
    "raw_color",
    "upper_material_scraped",
    "upper_material_partial",
    "scrape_match_status",
    "material_code",
    "material_code_evidence",
    "notes",
]

def write_csv(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# 7. Report
# ---------------------------------------------------------------------------
def print_report(rows, partial_map):
    total = len(rows)
    scraped_ok  = sum(1 for r in rows if r["upper_material_scraped"])
    not_found   = total - scraped_ok
    in_partial  = sum(1 for r in rows if r["source_product_id"] in partial_map)

    statuses = {}
    for r in rows:
        s = r["scrape_match_status"]
        statuses[s] = statuses.get(s, 0) + 1

    pl_count    = sum(1 for r in rows if r["material_code"] == "PL")
    empty_code  = total - pl_count

    # Count materials
    mat_counts = {}
    for r in rows:
        m = r["upper_material_scraped"] or "(empty)"
        mat_counts[m] = mat_counts.get(m, 0) + 1
    top15 = sorted(mat_counts.items(), key=lambda x: -x[1])[:15]

    print("=" * 60)
    print("MATERIAL CODE FULL AUDIT — REPORT")
    print("=" * 60)
    print(f"Total products:                    {total}")
    print(f"Successfully scraped (mat found):  {scraped_ok}")
    print(f"Not found on page:                 {not_found}")
    print(f"Covered in partial audit:          {in_partial}  (of 45 total partial entries)")
    print()
    print("Match status breakdown:")
    for status, cnt in sorted(statuses.items()):
        print(f"  {status:<20} {cnt}")
    print()
    print(f"material_code assigned (PL):       {pl_count}")
    print(f"material_code still empty:         {empty_code}")
    print()
    print("Top 15 upper_material_scraped values:")
    for mat, cnt in top15:
        print(f"  {cnt:>4}  {mat}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("Loading data...", flush=True)
    unknowns    = load_audit_unknowns()
    url_map     = load_url_map()
    partial_map = load_partial_audit()

    print(f"  UNKNOWN products to scrape:   {len(unknowns)}")
    print(f"  URLs available:               {sum(1 for r in unknowns if str(r['source_product_id']) in url_map)}")
    print(f"  Partial audit entries loaded: {len(partial_map)}")
    print()

    print("Scraping product pages (4 workers, 0.4s delay)...", flush=True)
    scraped_map = scrape_all(unknowns, url_map, max_workers=4, sleep_between=0.4)
    print()

    print("Building output rows...", flush=True)
    rows = build_output_rows(unknowns, scraped_map, partial_map)

    print(f"Writing CSV to: {OUTPUT_CSV}", flush=True)
    write_csv(rows, OUTPUT_CSV)
    print("Done.", flush=True)
    print()

    print_report(rows, partial_map)


if __name__ == "__main__":
    main()
