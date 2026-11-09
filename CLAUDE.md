# CUEREN 홈페이지 크롤링 — 프로젝트 지침

## 데이터 저장 규칙

- `data/` — scraper.py가 생성하는 원본 데이터 전용 (all_collections.json, 콜렉션별 JSON). **절대 건드리지 말 것.**
- `palantir/data/product_catalog/` — 중간 산출물 (audit, resolved CSV 등)
- `palantir/data/final/` — **최종 산출물 전용. "data 폴더"라고 하면 여기를 의미함.**
  - 루트 `data/`는 절대 건드리지 말 것

## 현재 Palantir 데이터 파일

### `palantir/data/product_catalog/`
| 파일 | 설명 |
|---|---|
| `variants_detail.json` | 상세 페이지 스크래핑 결과 — upper_material, description (374개) |
| `material_code_audit.csv` | 전체 소재 코드 감사 결과 (374개) |
| `material_code_missing.csv` | 소재 코드 미확인 상품 목록 (수동 입력용) |
| `material_code_resolved.csv` | 규칙 기반 소재 코드 완성본 (374개) |
| `variant_id_resolved.csv` | Variant ID 완성본 (374개, 중복 없음) |

### `palantir/data/final/`
| 파일 | 설명 |
|---|---|
| `catalog_raw.csv` | **최종 Product Catalog Raw Data** — SKU 단위 (2,244행, 23컬럼) |

## 프로젝트 배경

Palantir Foundry Pipeline Builder에 업로드할 CUEREN 상품 카탈로그 데이터셋 구축 중.
최종 목표: Product / Variant / SKU 3단계 테이블로 분리.
현재 단계: `catalog_raw.csv` 완성 — Palantir에서 3개 테이블로 분리 가능.
