"""
Material Code Audit Generator
- Vercel KV product_codes.json를 최우선으로 사용
- KV에 없는 상품은 all_collections.json의 color 필드에서 추출
- 충돌/미확인 상품을 별도 플래그
"""

import json
import re
import csv
import os
import sys

# Windows 콘솔 UTF-8 출력
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
KV_PATH   = os.path.join(BASE_DIR, "data", "product_codes.json")
JSON_PATH = os.path.join(BASE_DIR, "data", "all_collections.json")
OUT_PATH  = os.path.join(BASE_DIR, "data", "material_code_audit.csv")

# 의미가 확인된 material code
KNOWN_MATERIALS = {
    "CR": ("Cow leather",   "Matte"),
    "PL": ("Cow leather",   "Glossy"),
    "NS": ("Sheep leather", "Matte"),
    "MS": ("Sheep leather", "Glossy"),
}
# 존재는 확인됐으나 의미 미상
CONFIRMED_UNKNOWN = {"CE", "GN", "FE", "MK", "SP"}
ALL_KNOWN_CODES = set(KNOWN_MATERIALS) | CONFIRMED_UNKNOWN


def mat_from_kv_code(variant_code: str):
    """'wvn09-crwh' → 'CR'  (대시 뒤 첫 2자)"""
    if "-" not in variant_code:
        return None
    suffix = variant_code.split("-", 1)[1]   # e.g. 'crwh'
    return suffix[:2].upper()


def mat_from_color_field(color: str):
    """
    JSON color 필드에서 material code 추출.
    패턴 1: 'BLACK (CR)'       → 'CR'
    패턴 2: 'CRBK', 'NSBE' 등 → 'CR', 'NS'
    """
    if not color:
        return None
    # 패턴 1: "COLOR (CODE)"
    m = re.match(r"^.+\s+\(([A-Z]{2,3})\)\s*$", color.strip())
    if m:
        return m.group(1)
    # 패턴 2: 4~6자 대문자, 앞 2자가 알려진 material
    if re.match(r"^[A-Z]{4,6}$", color):
        prefix = color[:2]
        if prefix in ALL_KNOWN_CODES:
            return prefix
    return None


def main():
    with open(KV_PATH, encoding="utf-8") as f:
        kv: dict = json.load(f)   # {"1234": "wvn09-crwh", ...}

    with open(JSON_PATH, encoding="utf-8") as f:
        collections: dict = json.load(f)

    rows = []
    conflict_log = []

    for col_name, col_data in collections.items():
        for p in col_data["products"]:
            pid        = str(p["product_id"])
            raw_color  = p.get("color", "")
            kv_code    = kv.get(pid, "")

            material_code     = None
            extraction_source = "UNKNOWN"
            status            = "UNKNOWN"

            # ── 1순위: Vercel KV ──────────────────────────────────────
            if kv_code:
                mat_kv = mat_from_kv_code(kv_code)
                material_code     = mat_kv
                extraction_source = "VERCEL_KV"
                status            = "CONFIRMED"

                # JSON color에서도 추출해 충돌 검사
                mat_json = mat_from_color_field(raw_color)
                if mat_json and mat_json != mat_kv:
                    status = "CONFLICT"
                    conflict_log.append({
                        "pid":      pid,
                        "name":     p["product_name"],
                        "kv_code":  kv_code,
                        "mat_kv":   mat_kv,
                        "raw_color": raw_color,
                        "mat_json": mat_json,
                    })

            # ── 2순위: JSON color 필드 ────────────────────────────────
            else:
                mat_json = mat_from_color_field(raw_color)
                if mat_json:
                    material_code     = mat_json
                    extraction_source = "SOURCE_JSON"
                    # 의미가 확인된 코드면 CONFIRMED, 미상 코드면 UNKNOWN
                    status = "CONFIRMED" if mat_json in KNOWN_MATERIALS else "UNKNOWN"

            rows.append({
                "source_product_id":   p["product_id"],
                "product_name":        p["product_name"],
                "collection":          col_name,
                "section":             p.get("section", ""),
                "raw_color":           raw_color,
                "existing_variant_code": kv_code,
                "material_code":       material_code or "",
                "extraction_source":   extraction_source,
                "status":              status,
            })

    # ── CSV 저장 ──────────────────────────────────────────────────────
    fieldnames = [
        "source_product_id", "product_name", "collection", "section",
        "raw_color", "existing_variant_code",
        "material_code", "extraction_source", "status",
    ]
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # ── 요약 보고 ─────────────────────────────────────────────────────
    total = len(rows)
    kv_count      = sum(1 for r in rows if r["extraction_source"] == "VERCEL_KV")
    json_count    = sum(1 for r in rows if r["extraction_source"] == "SOURCE_JSON")
    unknown_count = sum(1 for r in rows if r["extraction_source"] == "UNKNOWN")
    confirmed     = sum(1 for r in rows if r["status"] == "CONFIRMED")
    conflicts     = sum(1 for r in rows if r["status"] == "CONFLICT")

    print("=" * 60)
    print("Material Code Audit 요약")
    print("=" * 60)
    print(f"  총 상품 수           : {total}")
    print(f"  Vercel KV 조회       : {kv_count} ({kv_count/total*100:.1f}%)")
    print(f"  JSON color 추출      : {json_count} ({json_count/total*100:.1f}%)")
    print(f"  추출 불가 (UNKNOWN)  : {unknown_count} ({unknown_count/total*100:.1f}%)")
    print(f"  CONFIRMED            : {confirmed}")
    print(f"  CONFLICT             : {conflicts}")
    print()

    # 콜렉션별 KV 커버리지
    from collections import Counter
    kv_by_col   = Counter(r["collection"] for r in rows if r["extraction_source"] == "VERCEL_KV")
    total_by_col = Counter(r["collection"] for r in rows)
    print("콜렉션별 KV 커버리지:")
    for col in total_by_col:
        t = total_by_col[col]
        k = kv_by_col.get(col, 0)
        print(f"  {col:12s}: {k:3d}/{t:3d}")
    print()

    # material_code 분포
    mat_dist = Counter(r["material_code"] for r in rows if r["material_code"])
    print("Material Code 분포:")
    for mat, cnt in sorted(mat_dist.items(), key=lambda x: -x[1]):
        meaning = KNOWN_MATERIALS.get(mat, ("(의미 미상)", ""))
        print(f"  {mat}: {cnt:3d}  → {meaning[0]} / {meaning[1]}")
    print()

    # 미상 코드 목록
    unknown_mats = {r["material_code"] for r in rows
                    if r["material_code"] and r["material_code"] not in KNOWN_MATERIALS}
    if unknown_mats:
        print(f"⚠ 의미 미상 Material Code: {sorted(unknown_mats)}")
        for mat in sorted(unknown_mats):
            examples = [(r["collection"], r["product_name"], r["raw_color"])
                        for r in rows if r["material_code"] == mat][:3]
            for col, name, color in examples:
                print(f"    [{mat}] {col} / {name} / color={color!r}")
        print()

    # 충돌 목록
    if conflict_log:
        print(f"⚠ KV ↔ JSON 충돌 ({len(conflict_log)}건):")
        for c in conflict_log:
            print(f"  pid={c['pid']} {c['name']}")
            print(f"    KV: {c['kv_code']} → mat={c['mat_kv']}")
            print(f"    JSON color: {c['raw_color']!r} → mat={c['mat_json']}")
    else:
        print("✓ KV ↔ JSON 충돌 없음")

    # UNKNOWN 샘플
    unknowns = [r for r in rows if r["status"] == "UNKNOWN"]
    if unknowns:
        print(f"\n추출 불가 상품 샘플 (최대 10개):")
        for r in unknowns[:10]:
            print(f"  pid={r['source_product_id']} {r['collection']:10s} {r['product_name']:30s} color={r['raw_color']!r}")

    print(f"\n저장 완료: {OUT_PATH}")


if __name__ == "__main__":
    main()
