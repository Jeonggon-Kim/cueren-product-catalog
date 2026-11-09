"""
Material Code Mapping
- 135개 UNKNOWN 상품에 규칙 기반으로 material_code 채우기
- 기존 파일 수정 없이 새 파일로 저장
- 출력: palantir/data/product_catalog/material_code_resolved.csv
"""

import csv
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR  = os.path.join(os.path.dirname(__file__), "..")
AUDIT_PATH  = os.path.join(BASE_DIR, "palantir/data/product_catalog/material_code_audit.csv")
DETAIL_PATH = os.path.join(BASE_DIR, "palantir/data/product_catalog/variants_detail.json")
OUT_PATH    = os.path.join(BASE_DIR, "palantir/data/product_catalog/material_code_resolved.csv")

# ── 직접 매핑 테이블 (소문자로 비교) ─────────────────────────────
DIRECT_MAP = {
    "full-grain kipskin":        "CR",
    "soft full grain":           "CR",
    "vegetable tanned leather":  "CR",
    "vegetable tanned full grain": "CR",
    "patent leather":            "PL",
    "nappa lambskin":            "NS",   # 대소문자 무관하게 처리
    "crocodile embossed":        "CE",
    "full-grain embossed":       "FE",
    "silky suede":               "SP",
    # 추론값
    "brush-off leather":         "CR",
    "hairy calf":                "CE",
    "leopard hairy calf":        "CE",
    "tumbled nubuck":            "CR",
}

METALLIC_KEYWORDS = ["silver", "gold", "metallic", "mssv", "msgd", "msmk"]


def map_material(upper_material: str, raw_color: str, collection: str) -> tuple[str, str]:
    """(material_code, source) 반환"""
    mat = upper_material.lower().strip()
    color = raw_color.lower()

    # Goat Nubuck: SEOUL=GN, 나머지=CR
    if "goat nubuck" in mat:
        code = "GN" if collection == "SEOUL" else "CR"
        return code, "MAPPED_RULE"

    # Milled Sheepskin: 광택색=MS, 나머지=NS
    if "milled sheepskin" in mat:
        code = "MS" if any(k in color for k in METALLIC_KEYWORDS) else "NS"
        return code, "MAPPED_RULE"

    # 직접 매핑
    code = DIRECT_MAP.get(mat, "")
    if code:
        source = "MAPPED_INFERRED" if mat in {
            "brush-off leather", "hairy calf", "leopard hairy calf", "tumbled nubuck"
        } else "MAPPED_RULE"
        return code, source

    return "", "UNRESOLVED"


def main():
    with open(DETAIL_PATH, encoding="utf-8") as f:
        detail = json.load(f)

    audit_rows = list(csv.DictReader(open(AUDIT_PATH, encoding="utf-8")))

    out_rows = []
    stats = {"VERCEL_KV": 0, "SOURCE_JSON": 0, "MAPPED_RULE": 0,
             "MAPPED_INFERRED": 0, "UNRESOLVED": 0}

    for row in audit_rows:
        pid = row["source_product_id"]
        d   = detail.get(pid, {})
        upper_material = d.get("upper_material", "")

        if row["extraction_source"] != "UNKNOWN":
            # 기존 확정값 그대로
            material_code   = row["material_code"]
            material_source = row["extraction_source"]
        else:
            # 규칙 매핑 적용
            material_code, material_source = map_material(
                upper_material,
                row["raw_color"],
                row["collection"],
            )

        stats[material_source] = stats.get(material_source, 0) + 1

        out_rows.append({
            "source_product_id":  pid,
            "product_name":       row["product_name"],
            "collection":         row["collection"],
            "section":            row["section"],
            "raw_color":          row["raw_color"],
            "upper_material":     upper_material,
            "material_code":      material_code,
            "material_code_source": material_source,
        })

    fieldnames = [
        "source_product_id", "product_name", "collection", "section",
        "raw_color", "upper_material", "material_code", "material_code_source",
    ]
    with open(OUT_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    # ── 요약 ──────────────────────────────────────────────────────
    print("=" * 55)
    print("Material Code Mapping 완료")
    print("=" * 55)
    print(f"  총 상품              : {len(out_rows)}")
    print(f"  VERCEL_KV (기존)     : {stats.get('VERCEL_KV', 0)}")
    print(f"  SOURCE_JSON (기존)   : {stats.get('SOURCE_JSON', 0)}")
    print(f"  MAPPED_RULE (규칙)   : {stats.get('MAPPED_RULE', 0)}")
    print(f"  MAPPED_INFERRED (추론): {stats.get('MAPPED_INFERRED', 0)}")
    print(f"  UNRESOLVED           : {stats.get('UNRESOLVED', 0)}")
    print(f"\n저장: {OUT_PATH}")

    unresolved = [r for r in out_rows if r["material_code_source"] == "UNRESOLVED"]
    if unresolved:
        print(f"\n미해결 {len(unresolved)}개:")
        for r in unresolved:
            print(f"  pid={r['source_product_id']} {r['product_name']} | {r['upper_material']!r}")


if __name__ == "__main__":
    main()
