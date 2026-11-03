"""
쿠에른(CUEREN) 상품 스크래퍼
- 각 콜렉션 페이지에서 상품 정보를 추출
- 결과를 JSON 파일로 저장
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "https://cueren.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
}

COLLECTIONS = [
    {"name": "EZE", "cate_no": 99},
    {"name": "VENICE", "cate_no": 87},
    {"name": "VALENCIA", "cate_no": 84},
    {"name": "ROME", "cate_no": 97},
    {"name": "LONDON", "cate_no": 82},
    {"name": "DIJON", "cate_no": 131},
    {"name": "MADRID", "cate_no": 95},
    {"name": "MILANO", "cate_no": 258},
    {"name": "SEOUL", "cate_no": 332},
    {"name": "MOSCOW", "cate_no": 86},
    {"name": "TORINO", "cate_no": 101},
    {"name": "BOSTON", "cate_no": 102},
]

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def scrape_collection(name: str, cate_no: int) -> list[dict]:
    """콜렉션 페이지를 스크래핑하여 상품 리스트를 반환"""
    url = f"{BASE_URL}/product/project.html?cate_no={cate_no}&type={name}"
    print(f"[{name}] 스크래핑 중... {url}")

    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    resp.encoding = "utf-8"

    soup = BeautifulSoup(resp.text, "html.parser")

    products = []
    current_section = "WOMEN"  # 기본값

    # 섹션 헤더(MEN/WOMEN) 감지용
    section_headers = soup.find_all(["h2", "h3", "div", "p"], string=re.compile(r"^\s*(MEN|WOMEN)\s*$", re.I))
    section_map = {}
    for sh in section_headers:
        section_map[id(sh)] = sh.get_text(strip=True).upper()

    # 상품 리스트 항목 찾기 - Cafe24 구조
    # 방법 1: ul.prdList > li 구조
    product_items = soup.select("ul.prdList li.xans-record-, ul.prdList > li")
    if not product_items:
        # 방법 2: 일반적인 상품 링크 패턴
        product_items = soup.select("li[id^='anchorBoxId_']")
    if not product_items:
        # 방법 3: 모든 상품 링크에서 추출
        product_links = soup.find_all("a", href=re.compile(r"/product/.+/\d+/category/"))
        seen_ids = set()
        for link in product_links:
            href = link.get("href", "")
            match = re.search(r"/product/([^/]+)/(\d+)/category/", href)
            if not match:
                continue
            product_slug = match.group(1)
            product_id = int(match.group(2))
            if product_id in seen_ids:
                continue
            seen_ids.add(product_id)

            # URL 슬러그에서 깨끗한 상품명 생성
            # "eze-03-sandal" → "EZE 03 SANDAL"
            clean_name = product_slug.replace("-", " ").upper()

            # 이미지 찾기
            img = link.find("img")
            image_url = ""
            if img:
                image_url = img.get("src", "") or img.get("data-src", "") or img.get("data-original", "")

            # 가격 찾기
            price = ""
            parent = link.find_parent("li") or link.find_parent("div")
            if parent:
                price_el = parent.find("span", class_=re.compile(r"price|won", re.I))
                if not price_el:
                    price_el = parent.find(string=re.compile(r"[\d,]+원"))
                if price_el:
                    price_text = price_el if isinstance(price_el, str) else price_el.get_text()
                    price_match = re.search(r"([\d,]+)원", price_text)
                    if price_match:
                        price = price_match.group(1) + "원"

            # 품절 여부
            sold_out = False
            if parent:
                sold_out_el = parent.find(string=re.compile(r"sold\s*out|품절", re.I))
                if sold_out_el:
                    sold_out = True
                icon_el = parent.find("img", alt=re.compile(r"sold\s*out|품절", re.I))
                if icon_el:
                    sold_out = True
                class_check = parent.get("class", [])
                if any("sold" in c.lower() or "disabled" in c.lower() for c in class_check):
                    sold_out = True

            product_name = clean_name

            # 모델번호 추출 (예: "ROME 07 BALLET FLAT" → "07")
            model_number = ""
            model_full = ""
            if product_name:
                mn_match = re.match(rf"({name}\s*\d+)", product_name, re.I)
                if mn_match:
                    model_full = mn_match.group(1).upper()
                    num_match = re.search(r"(\d+)", model_full)
                    if num_match:
                        model_number = num_match.group(1)

            products.append({
                "product_name": product_name,
                "model": model_full,
                "model_number": model_number,
                "price": price,
                "product_id": product_id,
                "url": f"{BASE_URL}{href}",
                "image_url": image_url,
                "sold_out": sold_out,
            })

        print(f"  → 방법3(링크 추출)으로 {len(products)}개 상품 발견")
        return products

    # 방법 1, 2로 찾은 경우
    for item in product_items:
        # 섹션 감지
        prev = item.find_previous(["h2", "h3", "div", "p"], string=re.compile(r"^\s*(MEN|WOMEN)\s*$", re.I))
        if prev:
            current_section = prev.get_text(strip=True).upper()

        link = item.find("a", href=re.compile(r"/product/.+/\d+/category/"))
        if not link:
            continue

        href = link.get("href", "")
        match = re.search(r"/product/([^/]+)/(\d+)/category/", href)
        if not match:
            continue

        product_slug = match.group(1)
        product_id = int(match.group(2))

        img = link.find("img") or item.find("img")
        image_url = ""
        if img:
            image_url = img.get("src", "") or img.get("data-src", "") or img.get("data-original", "")

        # URL 슬러그에서 깨끗한 상품명 생성
        product_name = product_slug.replace("-", " ").upper()

        price = ""
        price_el = item.find(string=re.compile(r"[\d,]+원"))
        if price_el:
            price_match = re.search(r"([\d,]+)원", str(price_el))
            if price_match:
                price = price_match.group(1) + "원"

        sold_out = False
        if item.find(string=re.compile(r"sold\s*out|품절", re.I)):
            sold_out = True
        if item.find("img", alt=re.compile(r"sold\s*out|품절", re.I)):
            sold_out = True

        model_number = ""
        model_full = ""
        if product_name:
            mn_match = re.match(rf"({name}\s*\d+)", product_name, re.I)
            if mn_match:
                model_full = mn_match.group(1).upper()
                num_match = re.search(r"(\d+)", model_full)
                if num_match:
                    model_number = num_match.group(1)

        products.append({
            "product_name": product_name,
            "model": model_full,
            "model_number": model_number,
            "price": price,
            "product_id": product_id,
            "url": f"{BASE_URL}{href}",
            "image_url": image_url,
            "sold_out": sold_out,
            "section": current_section,
        })

    print(f"  → {len(products)}개 상품 발견")
    return products


def fetch_color(product_url: str, product_name: str) -> str:
    """상품 상세 페이지에서 색상 정보 추출"""
    try:
        resp = requests.get(product_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        html = resp.text

        # Schema.org에서 추출: "name":"EZE 03 SANDAL BLACK (CR)-225"
        # 상품명 뒤에 오는 색상-사이즈 패턴
        pattern = re.escape(product_name) + r'\s+(.+?)-\d{3}'
        match = re.search(pattern, html, re.I)
        if match:
            return match.group(1).strip()

        # 좀 더 유연한 패턴: "상품명 색상명-숫자" in JSON
        match = re.search(r'"name"\s*:\s*"[^"]*?' + re.escape(product_name) + r'\s+(.+?)-\d{3}', html, re.I)
        if match:
            return match.group(1).strip()

        # 옵션 셀렉트에서 추출: value="BLACK (CR)-225"
        match = re.search(r'value="([A-Z][A-Za-z &/()\.\-]+?)-\d{3}"', html)
        if match:
            return match.group(1).strip()

        # option_title 폴백: option_title="크림(CRES)-사이즈(필수)" → 괄호 안 코드 추출
        match = re.search(r'option_title="([^"]+)"', html)
        if match:
            color_part = match.group(1).split("-")[0].strip()
            # 괄호 안 영문 코드만 추출: "크림(CRES)" → "CRES"
            code_match = re.search(r'\(([A-Z][A-Z0-9]+)\)', color_part)
            if code_match:
                return code_match.group(1)
            return color_part

    except Exception:
        pass
    return ""


def enrich_colors(products: list[dict]) -> list[dict]:
    """상품 리스트에 색상 정보를 병렬로 추가"""
    total = len(products)
    print(f"  → 색상 추출 중... ({total}개 상품)")

    def fetch_one(idx_product):
        idx, p = idx_product
        color = fetch_color(p["url"], p["product_name"])
        time.sleep(0.3)  # 서버 부하 방지
        return idx, color

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_one, (i, p)): i for i, p in enumerate(products)}
        done = 0
        for future in as_completed(futures):
            idx, color = future.result()
            products[idx]["color"] = color
            done += 1
            if done % 10 == 0 or done == total:
                print(f"    {done}/{total} 완료")

    found = sum(1 for p in products if p.get("color"))
    print(f"  → 색상 추출 완료: {found}/{total}개 성공")
    return products


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    all_data = {}

    for col in COLLECTIONS:
        try:
            products = scrape_collection(col["name"], col["cate_no"])
            products = enrich_colors(products)
            all_data[col["name"]] = {
                "collection": col["name"],
                "cate_no": col["cate_no"],
                "url": f"{BASE_URL}/product/project.html?cate_no={col['cate_no']}&type={col['name']}",
                "total_products": len(products),
                "products": products,
            }

            # 콜렉션별 개별 JSON 저장
            filepath = os.path.join(OUTPUT_DIR, f"{col['name'].lower()}.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(all_data[col["name"]], f, ensure_ascii=False, indent=2)
            print(f"  → 저장 완료: {filepath}")

        except Exception as e:
            print(f"  → [오류] {col['name']}: {e}")

        time.sleep(1)  # 서버 부하 방지

    # 전체 데이터 통합 JSON 저장
    all_filepath = os.path.join(OUTPUT_DIR, "all_collections.json")
    with open(all_filepath, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"\n전체 데이터 저장 완료: {all_filepath}")

    # 요약 출력
    print("\n=== 스크래핑 결과 요약 ===")
    total = 0
    for name, data in all_data.items():
        count = data["total_products"]
        total += count
        print(f"  {name:12s}: {count:3d}개 상품")
    print(f"  {'합계':12s}: {total:3d}개 상품")


if __name__ == "__main__":
    main()
