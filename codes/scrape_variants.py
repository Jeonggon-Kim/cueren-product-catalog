"""
CUEREN 전체 Variant 상세 페이지 스크래퍼
- all_collections.json의 376개 상품 URL을 병렬로 접속
- DESCRIPTION + MATERIAL(어퍼) 추출
- 결과를 data/variants_detail.json 으로 저장
"""

import json
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR  = os.path.join(os.path.dirname(__file__), "..")
JSON_PATH = os.path.join(BASE_DIR, "data", "all_collections.json")
OUT_PATH  = os.path.join(BASE_DIR, "data", "variants_detail.json")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
}
MAX_WORKERS = 8
REQUEST_TIMEOUT = 20


def parse_page(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    lines = [l.strip() for l in soup.get_text(separator="\n").splitlines() if l.strip()]

    result = {"upper_material": "", "description": ""}

    # ── MATERIAL 섹션에서 어퍼 추출 ───────────────────────────────
    # 라벨: "어퍼" 또는 "겉감" (컬렉션에 따라 다름)
    UPPER_LABELS = ("어퍼", "겉감")

    for i, line in enumerate(lines):
        if line == "MATERIAL":
            for j in range(i + 1, min(i + 10, len(lines))):
                # 케이스 1: "어퍼 Nappa Lambskin" — 라벨+소재 한 줄
                for label in UPPER_LABELS:
                    if lines[j].startswith(label):
                        material = lines[j].replace(label, "").strip()
                        if material:
                            result["upper_material"] = material
                        # 케이스 2: "어퍼" 단독 줄 → 다음 줄이 소재명
                        elif j + 1 < len(lines):
                            result["upper_material"] = lines[j + 1].strip()
                        break
                if result["upper_material"]:
                    break
            break

    # ── DESCRIPTION 섹션 추출 ─────────────────────────────────────
    # "DESCRIPTION" 이후 ~ "MATERIAL" / "SHIPPING" / "CARE" 이전까지
    desc_lines = []
    in_desc = False
    for line in lines:
        if line == "DESCRIPTION":
            in_desc = True
            continue
        if in_desc:
            if line in ("MATERIAL", "SHIPPING & RETURNS", "CARE GUIDE", "A/S & WARRANTY", "CONTACT"):
                break
            desc_lines.append(line)

    result["description"] = " ".join(desc_lines).strip()

    return result


def fetch_one(product: dict) -> dict:
    pid = product["product_id"]
    url = product["url"]
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        parsed = parse_page(resp.text)
        return {
            "product_id":      pid,
            "product_name":    product["product_name"],
            "collection":      product.get("collection", ""),
            "section":         product.get("section", ""),
            "color":           product.get("color", ""),
            "url":             url,
            "upper_material":  parsed["upper_material"],
            "description":     parsed["description"],
            "scrape_status":   "OK" if parsed["upper_material"] else "MATERIAL_NOT_FOUND",
        }
    except Exception as e:
        return {
            "product_id":      pid,
            "product_name":    product["product_name"],
            "collection":      product.get("collection", ""),
            "section":         product.get("section", ""),
            "color":           product.get("color", ""),
            "url":             url,
            "upper_material":  "",
            "description":     "",
            "scrape_status":   f"ERROR: {e}",
        }


def main():
    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    # 전체 상품 목록 수집 (collection 필드 주입)
    all_products = []
    for col_name, col_data in data.items():
        for p in col_data["products"]:
            p_copy = dict(p)
            p_copy["collection"] = col_name
            all_products.append(p_copy)

    total = len(all_products)
    print(f"총 {total}개 상품 스크래핑 시작 (workers={MAX_WORKERS})")
    print("-" * 50)

    results = [None] * total
    done = 0
    errors = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_idx = {
            executor.submit(fetch_one, p): i
            for i, p in enumerate(all_products)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            row = future.result()
            results[idx] = row
            done += 1
            if "ERROR" in row["scrape_status"]:
                errors += 1
                print(f"  [ERR] pid={row['product_id']} {row['product_name']} → {row['scrape_status']}")
            elif row["scrape_status"] == "MATERIAL_NOT_FOUND":
                print(f"  [?]   pid={row['product_id']} {row['product_name']} — material 미확인")
            if done % 50 == 0 or done == total:
                print(f"  진행: {done}/{total}")

    # ── 저장 ──────────────────────────────────────────────────────
    # product_id → detail 딕셔너리로 저장
    output = {str(r["product_id"]): r for r in results if r}
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # ── 요약 ──────────────────────────────────────────────────────
    ok            = sum(1 for r in results if r and r["scrape_status"] == "OK")
    not_found     = sum(1 for r in results if r and r["scrape_status"] == "MATERIAL_NOT_FOUND")

    print()
    print("=" * 50)
    print("스크래핑 완료")
    print("=" * 50)
    print(f"  성공 (material 추출)  : {ok}")
    print(f"  material 미확인       : {not_found}")
    print(f"  오류                  : {errors}")
    print(f"  저장 위치             : {OUT_PATH}")

    # 소재명 분포 (상위 15)
    from collections import Counter
    mat_dist = Counter(r["upper_material"] for r in results if r and r["upper_material"])
    print()
    print("어퍼 소재명 분포 (상위 15):")
    for mat, cnt in mat_dist.most_common(15):
        print(f"  {cnt:3d}  {mat}")


if __name__ == "__main__":
    main()
