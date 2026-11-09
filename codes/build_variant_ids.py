"""
Variant ID Builder
- KV 확정 코드 (135개): 그대로 사용
- 나머지 (241개): 규칙 기반으로 variant_id 생성
- 출력: palantir/data/product_catalog/variant_id_resolved.csv
"""

import csv
import re
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR      = os.path.join(os.path.dirname(__file__), "..")
AUDIT_PATH    = os.path.join(BASE_DIR, "palantir/data/product_catalog/material_code_audit.csv")
RESOLVED_PATH = os.path.join(BASE_DIR, "palantir/data/product_catalog/material_code_resolved.csv")
OUT_PATH      = os.path.join(BASE_DIR, "palantir/data/product_catalog/variant_id_resolved.csv")

# ── 컬렉션 약어 ──────────────────────────────────────────────
COL_ABBREV = {
    "EZE":      "ez",   # KV 확인
    "ROME":     "rm",   # KV 확인
    "VENICE":   "vn",   # KV 확인
    "VALENCIA": "vl",   # KV 확인
    "LONDON":   "ld",   # KV 확인
    "DIJON":    "dj",   # KV 확인
    "BOSTON":   "bs",   # 사용자 확인
    "MADRID":   "md",   # 사용자 확인
    "MILANO":   "ml",   # 추론 (Milan → ml)
    "MOSCOW":   "mc",   # 추론 (ms 는 소재코드 충돌 방지)
    "SEOUL":    "sl",   # 추론 (Seoul → sl)
    "TORINO":   "tr",   # 추론 (Torino → tr)
}

GENDER_MAP = {"WOMEN": "w", "MEN": "m"}

# ── 색상 코드 매핑 ────────────────────────────────────────────
# KV 확인값
_KV_COLORS = {
    "BLACK", "WHITE", "IVORY", "BEIGE", "BRANDY", "ESPRESSO",
    "ALMOND", "TAUPE", "MUSTARD", "GOLD", "SILVER", "METALLIC BLACK",
    "PINK BEIGE", "PURE WHITE", "SKY BLUE", "RED ORANGE", "DEEP GREEN",
    "WHITE SAND", "CRIMSON", "PATENT BLACK", "PATENT BRANDY", "PATENT WINE",
    "CORAL",
}

COLOR_CODE_MAP = {
    # KV 확인
    "BLACK":          "bk",
    "WHITE":          "wh",
    "IVORY":          "iv",
    "BEIGE":          "be",
    "BRANDY":         "br",
    "ESPRESSO":       "es",
    "ALMOND":         "al",
    "TAUPE":          "tp",
    "MUSTARD":        "mt",
    "GOLD":           "gd",
    "SILVER":         "sv",
    "METALLIC BLACK": "mk",
    "PINK BEIGE":     "pb",
    "PURE WHITE":     "ph",
    "SKY BLUE":       "sb",
    "RED ORANGE":     "ro",
    "DEEP GREEN":     "dg",
    "WHITE SAND":     "ws",
    "CRIMSON":        "cs",
    "PATENT BLACK":   "bk",
    "PATENT BRANDY":  "br",
    "PATENT WINE":    "wn",
    "CORAL":          "cr",
    # 추론
    "WINE":              "wn",
    "BEIGE SAND":        "bs",
    "BRUSH OFF BRANDY":  "br",
    "BRUSH OFF WINE":    "wn",
    "CHARCOAL":          "cc",
    "DARK LEOPARD":      "dl",
    "SNOW LEOPARD":      "sl",
    "STONE":             "st",
    "NAVY BLUE":         "nb",
    "PATENT ESPRESSO":   "es",
}

# 복합 4자 코드 첫 2자 소재 집합 (CRBK, NSBK, MSMK, HCDL 등)
KNOWN_MAT_PREFIX = {"CR", "PL", "NS", "MS", "CE", "GN", "FE", "MK", "SP", "HC"}


def get_color_code(raw_color: str) -> tuple[str, str]:
    """(color_code, source) 반환"""
    raw = raw_color.strip()

    # 패턴 1: 복합 4자 대문자 코드 (CRBK → bk, HCDL → dl, MSGD → gd)
    if re.match(r"^[A-Z]{4}$", raw) and raw[:2] in KNOWN_MAT_PREFIX:
        return raw[2:].lower(), "COMPOUND"

    # 패턴 2: "COLOR (MAT)" → 색상명만 추출
    m = re.match(r"^(.+)\s+\([A-Z]{2,3}\)\s*$", raw)
    color_name = m.group(1).strip().upper() if m else raw.upper()

    code = COLOR_CODE_MAP.get(color_name, "")
    if code:
        source = "KV_DERIVED" if color_name in _KV_COLORS else "INFERRED"
        return code, source

    # 폴백: 앞 2자 소문자
    return raw[:2].lower(), "FALLBACK"


def get_model_no(product_name: str) -> str:
    """'ROME 12 LACE UP FLAT' → '12'"""
    m = re.search(r"\b(\d{2})\b", product_name)
    return m.group(1) if m else "00"


def main():
    # audit: existing_variant_code (KV) 조회용
    audit_map = {}
    for row in csv.DictReader(open(AUDIT_PATH, encoding="utf-8")):
        audit_map[str(row["source_product_id"])] = row

    resolved = list(csv.DictReader(open(RESOLVED_PATH, encoding="utf-8-sig")))

    out_rows = []
    stats = {"KV_CONFIRMED": 0, "CONSTRUCTED_RULE": 0, "CONSTRUCTED_INFERRED": 0, "UNRESOLVED": 0}

    for row in resolved:
        pid    = str(row["source_product_id"])
        audit  = audit_map.get(pid, {})
        kv_code = audit.get("existing_variant_code", "")

        if kv_code:
            # KV 확정 코드 사용 (gender prefix 보정)
            gender = GENDER_MAP.get(row["section"], "w")
            variant_id        = gender + kv_code[1:]
            variant_id_source = "KV_CONFIRMED"
            color_code        = kv_code.split("-")[1][2:] if "-" in kv_code else ""
            col_abbrev        = kv_code[1:3]
            model_no          = kv_code[3:5]
        else:
            # 규칙 기반 생성
            col        = row["collection"]
            col_abbrev = COL_ABBREV.get(col, col[:2].lower())
            model_no   = get_model_no(row["product_name"])
            mat_code   = row["material_code"].lower()
            color_code, color_source = get_color_code(row["raw_color"])

            if mat_code and color_code:
                gender = GENDER_MAP.get(row["section"], "w")
                variant_id = f"{gender}{col_abbrev}{model_no}-{mat_code}{color_code}"
                variant_id_source = (
                    "CONSTRUCTED_INFERRED"
                    if color_source in ("INFERRED", "FALLBACK")
                    else "CONSTRUCTED_RULE"
                )
            else:
                variant_id        = ""
                variant_id_source = "UNRESOLVED"

        stats[variant_id_source] = stats.get(variant_id_source, 0) + 1

        out_rows.append({
            "source_product_id":    pid,
            "product_name":         row["product_name"],
            "collection":           row["collection"],
            "section":              row["section"],
            "raw_color":            row["raw_color"],
            "upper_material":       row["upper_material"],
            "material_code":        row["material_code"],
            "material_code_source": row["material_code_source"],
            "col_abbrev":           col_abbrev,
            "model_no":             model_no,
            "color_code":           color_code,
            "variant_id":           variant_id,
            "variant_id_source":    variant_id_source,
        })

    fieldnames = [
        "source_product_id", "product_name", "collection", "section",
        "raw_color", "upper_material",
        "material_code", "material_code_source",
        "col_abbrev", "model_no", "color_code",
        "variant_id", "variant_id_source",
    ]
    with open(OUT_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    # ── 요약 ──────────────────────────────────────────────────
    print("=" * 55)
    print("Variant ID 생성 완료")
    print("=" * 55)
    print(f"  총 상품                : {len(out_rows)}")
    print(f"  KV_CONFIRMED           : {stats.get('KV_CONFIRMED', 0)}")
    print(f"  CONSTRUCTED_RULE       : {stats.get('CONSTRUCTED_RULE', 0)}")
    print(f"  CONSTRUCTED_INFERRED   : {stats.get('CONSTRUCTED_INFERRED', 0)}")
    print(f"  UNRESOLVED             : {stats.get('UNRESOLVED', 0)}")
    print(f"\n저장: {OUT_PATH}")

    # FALLBACK 경고
    fallbacks = [r for r in out_rows if r["variant_id_source"] in ("CONSTRUCTED_INFERRED",)]
    if fallbacks:
        from collections import Counter
        color_sources = Counter()
        # color_source 재계산
        for r in out_rows:
            if r["variant_id_source"] == "CONSTRUCTED_INFERRED":
                _, src = get_color_code(r["raw_color"])
                color_sources[src] += 1
        print(f"\n추론 포함 상품 ({len(fallbacks)}개) color_source 분포:")
        for src, cnt in color_sources.items():
            print(f"  {src}: {cnt}")

    unresolved = [r for r in out_rows if r["variant_id_source"] == "UNRESOLVED"]
    if unresolved:
        print(f"\n미해결 {len(unresolved)}개:")
        for r in unresolved:
            print(f"  pid={r['source_product_id']} {r['product_name']} | mat={r['material_code']!r} color={r['raw_color']!r}")


if __name__ == "__main__":
    main()
