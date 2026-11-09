"""
Catalog Raw Data Builder
한 행 = 하나의 SKU (374 variants × 6 sizes = 2,244 rows)
출력: data/catalog_raw.csv
"""

import csv
import json
import re
import os
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR         = os.path.join(os.path.dirname(__file__), "..")
COLLECTIONS_PATH = os.path.join(BASE_DIR, "data/all_collections.json")
DETAIL_PATH      = os.path.join(BASE_DIR, "palantir/data/product_catalog/variants_detail.json")
VARIANT_PATH     = os.path.join(BASE_DIR, "palantir/data/product_catalog/variant_id_resolved.csv")
OUT_PATH         = os.path.join(BASE_DIR, "palantir/data/product_catalog/catalog_raw.csv")

WOMEN_SIZES = [225, 230, 235, 240, 245, 250]
MEN_SIZES   = [255, 260, 265, 270, 275, 280]

MATERIAL_TYPE_MAP = {
    "CR": "Cow Leather",
    "PL": "Patent Cow Leather",
    "NS": "Nappa Lambskin",
    "MS": "Milled Sheepskin",
    "CE": "Exotic Leather",
    "GN": "Goat Nubuck",
    "FE": "Full-Grain Embossed",
    "SP": "Silky Suede",
    "MK": "Milled Kidskin",
}

FINISH_MAP = {
    "CR": "Smooth",
    "PL": "Patent",
    "NS": "Smooth",
    "MS": "Metallic",
    "CE": "Embossed",
    "GN": "Nubuck",
    "FE": "Embossed",
    "SP": "Suede",
    "MK": "Smooth",
}

COLOR_NAME_MAP = {
    "bk": "Black",
    "wh": "White",
    "iv": "Ivory",
    "be": "Beige",
    "br": "Brandy",
    "es": "Espresso",
    "al": "Almond",
    "tp": "Taupe",
    "mt": "Mustard",
    "gd": "Gold",
    "sv": "Silver",
    "mk": "Metallic Black",
    "pb": "Pink Beige",
    "ph": "Pure White",
    "sb": "Sky Blue",
    "ro": "Red Orange",
    "dg": "Deep Green",
    "ws": "White Sand",
    "cs": "Crimson",
    "wn": "Wine",
    "bs": "Beige Sand",
    "cc": "Charcoal",
    "dl": "Dark Leopard",
    "sl": "Snow Leopard",
    "st": "Stone",
    "nb": "Navy Blue",
    "cr": "Coral",
}

# 카테고리 키워드 (순서 중요: 더 구체적인 것 먼저)
CATEGORY_KEYWORDS = [
    ("BALLERINA", "Flat"),
    ("BALLET",    "Flat"),
    ("SANDAL",    "Sandal"),
    ("BOOT",      "Boot"),
    ("PUMP",      "Pump"),
    ("STILETTO",  "Pump"),
    ("MULE",      "Mule"),
    ("BROGUE",    "Derby"),
    ("DERBY",     "Derby"),
    ("LOAFER",    "Loafer"),
    ("MOC",       "Loafer"),
    ("MONK",      "Monk"),
    ("FLAT",      "Flat"),
    ("DRIVING",   "Driving"),
    ("LACE UP",   "Flat"),
]


def normalize_category(category_raw: str) -> str:
    upper = category_raw.upper()
    for keyword, cat in CATEGORY_KEYWORDS:
        if keyword in upper:
            return cat
    return "Other"


def parse_price(price_str: str) -> str:
    return re.sub(r"[^\d]", "", price_str)


def get_category_raw(product_name: str, collection: str, model_number: str) -> str:
    prefix = f"{collection} {model_number}"
    if product_name.upper().startswith(prefix.upper()):
        return product_name[len(prefix):].strip()
    return product_name


def main():
    # ── 1. 데이터 로드 ────────────────────────────────────────
    with open(COLLECTIONS_PATH, encoding="utf-8") as f:
        collections = json.load(f)
    ac_flat = {}
    for col_data in collections.values():
        for p in col_data["products"]:
            ac_flat[str(p["product_id"])] = p

    with open(DETAIL_PATH, encoding="utf-8") as f:
        detail = {str(k): v for k, v in json.load(f).items()}

    variants = list(csv.DictReader(open(VARIANT_PATH, encoding="utf-8-sig")))

    # ── 2. 생성 ──────────────────────────────────────────────
    out_rows = []
    errors   = []

    for row in variants:
        pid = str(row["source_product_id"])

        ac = ac_flat.get(pid)
        vd = detail.get(pid)
        if ac is None:
            errors.append(f"all_collections 미발견: pid={pid} ({row['product_name']})")
            continue
        if vd is None:
            errors.append(f"variants_detail 미발견: pid={pid} ({row['product_name']})")
            continue

        variant_id    = row["variant_id"]
        product_id    = variant_id.split("-")[0].upper()     # WEZ03
        material_code = row["material_code"].upper()         # CR
        color_code    = row["color_code"]                    # bk
        section       = row["section"]                       # WOMEN / MEN
        collection    = row["collection"]
        model_number  = ac.get("model_number", row.get("model_no", ""))

        cat_raw  = get_category_raw(ac["product_name"], collection, model_number)
        category = normalize_category(cat_raw)

        color_name = COLOR_NAME_MAP.get(color_code, color_code.upper())
        finish     = FINISH_MAP.get(material_code, "")
        mat_type   = MATERIAL_TYPE_MAP.get(material_code, "")

        sizes = WOMEN_SIZES if section == "WOMEN" else MEN_SIZES

        for size in sizes:
            sku_id = f"{variant_id.upper()}-{size}"
            out_rows.append({
                "source_product_id": pid,
                "product_id":        product_id,
                "variant_id":        variant_id,
                "sku_id":            sku_id,
                "product_name":      ac["product_name"],
                "collection":        collection,
                "model_number":      model_number,
                "section":           section,
                "category_raw":      cat_raw,
                "category":          category,
                "material_code":     material_code,
                "material_type":     mat_type,
                "finish":            finish,
                "color_code":        color_code,
                "color_name":        color_name,
                "raw_color":         row["raw_color"],
                "size_mm":           size,
                "price_krw":         parse_price(ac.get("price", "")),
                "image_url":         ac.get("image_url", ""),
                "product_url":       vd.get("url", ac.get("url", "")),
                "source_sold_out":   str(ac.get("sold_out", "")),
                "raw_description":   vd.get("description", ""),
                "raw_material":      vd.get("upper_material", ""),
            })

    # ── 3. 저장 ──────────────────────────────────────────────
    fieldnames = [
        "source_product_id", "product_id", "variant_id", "sku_id",
        "product_name", "collection", "model_number", "section",
        "category_raw", "category",
        "material_code", "material_type", "finish",
        "color_code", "color_name", "raw_color",
        "size_mm", "price_krw",
        "image_url", "product_url", "source_sold_out",
        "raw_description", "raw_material",
    ]
    with open(OUT_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    # ── 4. 검증 ──────────────────────────────────────────────
    verify = list(csv.DictReader(open(OUT_PATH, encoding="utf-8-sig")))

    expected_variants = 374
    expected_skus     = expected_variants * 6  # 2,244

    checks = []

    # ① 원본 상품 374개
    unique_src = len(set(r["source_product_id"] for r in verify))
    checks.append(("① 원본 상품 374개", unique_src == expected_variants, f"{unique_src}개"))

    # ② Variant ID 374개, 중복 없음
    unique_vids = len(set(r["variant_id"] for r in verify))
    checks.append(("② Variant ID 374개, 중복 없음", unique_vids == expected_variants, f"{unique_vids}개"))

    # ③ 총 SKU 행 2,244개
    checks.append(("③ 총 SKU 행 2,244개", len(verify) == expected_skus, f"{len(verify)}개"))

    # ④ SKU ID 2,244개 고유
    dup_skus = [k for k, v in Counter(r["sku_id"] for r in verify).items() if v > 1]
    checks.append(("④ SKU ID 고유", len(dup_skus) == 0, f"중복 {len(dup_skus)}개"))

    # ⑤ WOMEN→W, MEN→M
    gender_bad = [r for r in verify if
        (r["section"] == "WOMEN" and r["product_id"][0] != "W") or
        (r["section"] == "MEN"   and r["product_id"][0] != "M")]
    checks.append(("⑤ gender prefix (W/M)", len(gender_bad) == 0, f"이상 {len(gender_bad)}개"))

    # ⑥ 각 Variant 정확히 6개 사이즈
    bad_sizes = {k: v for k, v in Counter(r["variant_id"] for r in verify).items() if v != 6}
    checks.append(("⑥ 각 Variant 정확히 6개 사이즈", len(bad_sizes) == 0, f"이상 {len(bad_sizes)}개"))

    # ⑦ product_id ↔ variant_id 일관성
    pid_vid_bad = [r for r in verify if not r["variant_id"].upper().startswith(r["product_id"])]
    checks.append(("⑦ product_id ↔ variant_id 일관성", len(pid_vid_bad) == 0, f"이상 {len(pid_vid_bad)}개"))

    # ⑧ SKU → Variant ID 참조
    sku_vid_bad = [r for r in verify if not r["sku_id"].startswith(r["variant_id"].upper())]
    checks.append(("⑧ SKU → Variant ID 참조", len(sku_vid_bad) == 0, f"이상 {len(sku_vid_bad)}개"))

    # ⑨ DESCRIPTION/MATERIAL 보존
    empty_desc = len(set(r["variant_id"] for r in verify if not r["raw_description"]))
    empty_mat  = len(set(r["variant_id"] for r in verify if not r["raw_material"]))
    checks.append(("⑨ DESCRIPTION/MATERIAL 보존",
                   empty_desc == 0 and empty_mat == 0,
                   f"빈 description {empty_desc}개 variant, 빈 material {empty_mat}개 variant"))

    # ⑩ 필수 정보 누락
    missing = {
        "variant_id":  sum(1 for r in verify if not r["variant_id"]),
        "product_id":  sum(1 for r in verify if not r["product_id"]),
        "collection":  sum(1 for r in verify if not r["collection"]),
        "price_krw":   sum(1 for r in verify if not r["price_krw"]),
    }
    ok10 = all(v == 0 for v in missing.values())
    checks.append(("⑩ 필수 정보 누락 없음", ok10,
                   " / ".join(f"{k}={v}" for k, v in missing.items() if v > 0) or "없음"))

    # 결과 출력
    print("=" * 60)
    print("검증 결과")
    print("=" * 60)
    all_pass = True
    for name, ok, detail_str in checks:
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {name}" + (f"  ({detail_str})" if detail_str else ""))
        if not ok:
            all_pass = False

    if errors:
        print(f"\n조인 오류 {len(errors)}건:")
        for e in errors:
            print(f"  - {e}")

    print(f"\n{'전체 통과' if all_pass and not errors else '일부 실패'}")
    print(f"저장: {OUT_PATH}")
    print(f"총 {len(out_rows):,}행 ({expected_variants} variants x 6 sizes)")


if __name__ == "__main__":
    main()
