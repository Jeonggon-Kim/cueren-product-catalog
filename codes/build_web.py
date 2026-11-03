"""
쿠에른 상품 카탈로그 웹 UI 생성기
- data/all_collections.json을 읽어서 단일 HTML 파일 생성
- 콜렉션 → WOMEN/MEN → 모델번호 → 색상별 상품 네비게이션
"""

import json
import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "all_collections.json")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "index.html")


def build_html(data: dict) -> str:
    # JSON 데이터를 JS에 임베드
    js_data = json.dumps(data, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CUEREN - 상품 카탈로그</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif; background: #f5f5f0; color: #1a1a1a; }}

/* 헤더 */
.header {{ background: #fff; border-bottom: 1px solid #e0e0e0; padding: 20px 0; text-align: center; position: sticky; top: 0; z-index: 100; }}
.header h1 {{ font-size: 28px; letter-spacing: 8px; font-weight: 300; }}
.header .subtitle {{ font-size: 11px; color: #888; margin-top: 4px; letter-spacing: 2px; }}

/* 네비게이션 경로 */
.breadcrumb {{ padding: 16px 24px; font-size: 13px; color: #666; background: #fff; border-bottom: 1px solid #eee; }}
.breadcrumb span {{ cursor: pointer; }}
.breadcrumb span:hover {{ color: #1a1a1a; text-decoration: underline; }}
.breadcrumb .sep {{ margin: 0 8px; color: #ccc; cursor: default; }}
.breadcrumb .current {{ color: #1a1a1a; font-weight: 600; cursor: default; }}

/* 뷰 공통 */
.view {{ max-width: 1200px; margin: 0 auto; padding: 32px 24px; }}
.view-title {{ text-align: center; margin-bottom: 8px; }}
.view-title h2 {{ font-size: 24px; letter-spacing: 4px; font-weight: 400; }}
.view-title .count {{ font-size: 12px; color: #999; margin-top: 4px; }}

/* 콜렉션 그리드 */
.collections-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 20px; margin-top: 32px; }}
.collection-card {{ background: #fff; border-radius: 8px; overflow: hidden; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; }}
.collection-card:hover {{ transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.1); }}
.collection-card .thumb {{ width: 100%; aspect-ratio: 1; object-fit: cover; background: #f0f0f0; }}
.collection-card .info {{ padding: 16px; }}
.collection-card .info h3 {{ font-size: 16px; letter-spacing: 3px; font-weight: 500; }}
.collection-card .info .meta {{ font-size: 12px; color: #999; margin-top: 4px; }}

/* WOMEN/MEN 탭 */
.section-tabs {{ display: flex; justify-content: center; gap: 24px; margin: 24px 0; }}
.section-tab {{ padding: 8px 24px; font-size: 14px; letter-spacing: 2px; cursor: pointer; border-bottom: 2px solid transparent; color: #999; transition: all 0.2s; }}
.section-tab:hover {{ color: #1a1a1a; }}
.section-tab.active {{ color: #1a1a1a; border-bottom-color: #1a1a1a; font-weight: 600; }}

/* 모델 그리드 */
.models-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 20px; margin-top: 16px; }}
.model-card {{ background: #fff; border-radius: 8px; overflow: hidden; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; }}
.model-card:hover {{ transform: translateY(-3px); box-shadow: 0 6px 20px rgba(0,0,0,0.08); }}
.model-card .thumb {{ width: 100%; aspect-ratio: 1; object-fit: cover; background: #f0f0f0; }}
.model-card .info {{ padding: 14px; }}
.model-card .info h3 {{ font-size: 14px; letter-spacing: 2px; font-weight: 500; }}
.model-card .info .meta {{ font-size: 12px; color: #999; margin-top: 4px; }}

/* 상품 그리드 (색상별) */
.products-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; margin-top: 16px; }}
.product-card {{ background: #fff; border-radius: 8px; overflow: hidden; transition: transform 0.2s, box-shadow 0.2s; position: relative; }}
.product-card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,0.08); }}
.product-card a {{ text-decoration: none; color: inherit; }}
.product-card .thumb {{ width: 100%; aspect-ratio: 1; object-fit: cover; background: #f0f0f0; }}
.product-card .info {{ padding: 12px; }}
.product-card .info .name {{ font-size: 12px; font-weight: 500; letter-spacing: 1px; }}
.product-card .info .color {{ font-size: 12px; color: #c47a2a; margin-top: 3px; font-weight: 500; }}
.product-card .info .price {{ font-size: 13px; color: #666; margin-top: 4px; }}
.product-card .info .pid {{ font-size: 10px; color: #bbb; margin-top: 2px; }}
.product-card .sold-out-badge {{ position: absolute; top: 8px; right: 8px; background: rgba(0,0,0,0.7); color: #fff; font-size: 10px; padding: 3px 8px; border-radius: 3px; letter-spacing: 1px; }}

/* 상품번호 입력 */
.product-card .code-row {{ display: flex; align-items: center; gap: 4px; margin-top: 6px; }}
.product-card .code-input {{ flex: 1; padding: 4px 8px; font-size: 11px; border: 1px solid #ddd; border-radius: 4px; outline: none; font-family: monospace; letter-spacing: 0.5px; }}
.product-card .code-input:focus {{ border-color: #999; }}
.product-card .code-input.saved {{ border-color: #4caf50; background: #f0faf0; }}
.product-card .code-status {{ font-size: 10px; color: #4caf50; min-width: 16px; }}

/* 뒤로가기 */
.back-btn {{ display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; font-size: 13px; color: #666; cursor: pointer; border: 1px solid #ddd; border-radius: 6px; background: #fff; margin-bottom: 20px; transition: all 0.2s; }}
.back-btn:hover {{ background: #f5f5f5; color: #1a1a1a; }}

/* 검색 */
.search-bar {{ max-width: 400px; margin: 20px auto; position: relative; }}
.search-bar input {{ width: 100%; padding: 10px 16px 10px 40px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; outline: none; background: #fff; }}
.search-bar input:focus {{ border-color: #999; }}
.search-bar .icon {{ position: absolute; left: 14px; top: 50%; transform: translateY(-50%); color: #999; font-size: 14px; }}

/* 검색 결과 */
.search-results {{ margin-top: 16px; }}
.search-results .result-group h3 {{ font-size: 14px; color: #666; margin: 16px 0 8px; padding-bottom: 4px; border-bottom: 1px solid #eee; }}

.hidden {{ display: none !important; }}

/* 반응형 */
@media (max-width: 600px) {{
  .collections-grid, .models-grid {{ grid-template-columns: repeat(2, 1fr); gap: 12px; }}
  .products-grid {{ grid-template-columns: repeat(2, 1fr); gap: 10px; }}
  .view {{ padding: 16px 12px; }}
}}
</style>
</head>
<body>

<div class="header">
  <h1>CUEREN</h1>
  <div class="subtitle">PRODUCT CATALOG</div>
</div>

<div class="breadcrumb" id="breadcrumb"></div>

<div class="view" id="app"></div>

<script>
const DATA = {js_data};

let state = {{ view: 'collections', collection: null, section: null, model: null }};
let productCodes = {{}};

/* ── 상품번호 API ── */
async function fetchCodes() {{
  try {{
    const res = await fetch('/api/codes');
    if (res.ok) productCodes = await res.json();
  }} catch(e) {{ console.warn('상품번호 로드 실패', e); }}
}}

let saveTimers = {{}};
function saveCode(productId, code) {{
  productCodes[String(productId)] = code;
  clearTimeout(saveTimers[productId]);
  saveTimers[productId] = setTimeout(async () => {{
    try {{
      const res = await fetch('/api/codes', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ product_id: productId, code }}),
      }});
      if (res.ok) {{
        const el = document.getElementById('code-status-' + productId);
        if (el) {{ el.textContent = '\\u2713'; setTimeout(() => el.textContent = '', 1500); }}
        const input = document.getElementById('code-input-' + productId);
        if (input) {{ input.classList.add('saved'); setTimeout(() => input.classList.remove('saved'), 1500); }}
      }}
    }} catch(e) {{ console.warn('저장 실패', e); }}
  }}, 500);
}}

/* ── URL 라우팅 ── */
function toSlug(str) {{ return str.toLowerCase().replace(/\\s+/g, '-'); }}
function fromSlug(slug) {{ return slug.toUpperCase().replace(/-/g, ' '); }}

function stateToUrl() {{
  if (!state.collection) return '/';
  let path = '/' + state.collection.toLowerCase();
  if (state.model) path += '/' + toSlug(state.model);
  const params = new URLSearchParams();
  if (state.section && state.section !== getCollectionSections(state.collection)[0]) {{
    params.set('section', state.section);
  }}
  const qs = params.toString();
  return qs ? path + '?' + qs : path;
}}

function urlToState() {{
  const path = window.location.pathname.replace(/\\/+$/, '') || '/';
  const params = new URLSearchParams(window.location.search);
  const parts = path.split('/').filter(Boolean);

  if (parts.length === 0) {{
    return {{ view: 'collections', collection: null, section: null, model: null }};
  }}

  const colKey = parts[0].toUpperCase();
  if (!DATA[colKey]) {{
    return {{ view: 'collections', collection: null, section: null, model: null }};
  }}

  const sections = getCollectionSections(colKey);
  const section = params.get('section') || sections[0];

  if (parts.length >= 2) {{
    const modelSlug = parts.slice(1).join('/');
    const model = fromSlug(modelSlug);
    return {{ view: 'products', collection: colKey, section, model }};
  }}

  return {{ view: 'models', collection: colKey, section, model: null }};
}}

function pushUrl(replace) {{
  const url = stateToUrl();
  if (replace) {{
    history.replaceState(null, '', url);
  }} else {{
    history.pushState(null, '', url);
  }}
}}

window.addEventListener('popstate', () => {{
  state = urlToState();
  renderCurrentView(true);
}});

function renderCurrentView(skipPush) {{
  if (state.view === 'products' && state.collection && state.model) {{
    renderProducts(skipPush);
  }} else if (state.view === 'models' && state.collection) {{
    renderModels(skipPush);
  }} else {{
    renderCollections(skipPush);
  }}
}}

/* ── 데이터 헬퍼 ── */
function getCollectionSections(colName) {{
  const products = DATA[colName].products;
  const sections = [...new Set(products.map(p => p.section))];
  return sections.sort((a, b) => a === 'WOMEN' ? -1 : 1);
}}

function getModels(colName, section) {{
  const products = DATA[colName].products.filter(p => p.section === section);
  const modelMap = {{}};
  for (const p of products) {{
    const key = p.model || p.product_name;
    if (!modelMap[key]) {{
      modelMap[key] = {{
        model: key,
        product_name: p.product_name,
        representative_image: p.image_url,
        count: 0,
        price_range: [],
      }};
    }}
    modelMap[key].count++;
    const priceNum = parseInt(p.price.replace(/[^0-9]/g, ''));
    if (priceNum) modelMap[key].price_range.push(priceNum);
  }}
  return Object.values(modelMap).map(m => {{
    const prices = m.price_range;
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    m.price_display = min === max ? `${{min.toLocaleString()}}원` : `${{min.toLocaleString()}}~${{max.toLocaleString()}}원`;
    return m;
  }}).sort((a, b) => {{
    const na = parseInt(a.model.match(/\\d+/)?.[0] || '0');
    const nb = parseInt(b.model.match(/\\d+/)?.[0] || '0');
    return na - nb;
  }});
}}

function getProducts(colName, section, model) {{
  return DATA[colName].products.filter(p => p.section === section && (p.model || p.product_name) === model);
}}

/* ── 브레드크럼 ── */
function renderBreadcrumb() {{
  const bc = document.getElementById('breadcrumb');
  let parts = [`<span onclick="navigateTo('/')">ALL COLLECTIONS</span>`];
  if (state.collection) {{
    parts.push(`<span class="sep">></span>`);
    if (state.model) {{
      const colUrl = '/' + state.collection.toLowerCase() + (state.section !== getCollectionSections(state.collection)[0] ? '?section=' + state.section : '');
      parts.push(`<span onclick="navigateTo('${{colUrl}}')">${{state.collection}} (${{state.section}})</span>`);
      parts.push(`<span class="sep">></span>`);
      parts.push(`<span class="current">${{state.model}}</span>`);
    }} else {{
      parts.push(`<span class="current">${{state.collection}} (${{state.section || ''}})</span>`);
    }}
  }}
  bc.innerHTML = parts.join('');
}}

/* ── 뷰 렌더링 ── */
function renderCollections(skipPush) {{
  state = {{ view: 'collections', collection: null, section: null, model: null }};
  if (!skipPush) pushUrl();
  renderBreadcrumb();
  const app = document.getElementById('app');

  let html = `
    <div class="view-title">
      <h2>COLLECTIONS</h2>
      <div class="count">12 Collections</div>
    </div>
    <div class="search-bar">
      <span class="icon">&#128269;</span>
      <input type="text" id="searchInput" placeholder="상품명 또는 모델 검색 (예: ROME 07)" oninput="onSearch(this.value)">
    </div>
    <div id="searchResults" class="search-results hidden"></div>
    <div id="collectionsGrid" class="collections-grid">`;

  const order = ['EZE','VENICE','VALENCIA','ROME','LONDON','DIJON','MADRID','MILANO','SEOUL','MOSCOW','TORINO','BOSTON'];
  for (const name of order) {{
    if (!DATA[name]) continue;
    const col = DATA[name];
    const firstImg = col.products[0]?.image_url || '';
    const sections = getCollectionSections(name);
    const secLabel = sections.length > 1 ? sections.join(' / ') : sections[0] || '';
    html += `
      <div class="collection-card" onclick="onCollectionClick('${{name}}')">
        <img class="thumb" src="${{firstImg}}" alt="${{name}}" loading="lazy" onerror="this.style.background='#ddd'">
        <div class="info">
          <h3>${{name}}</h3>
          <div class="meta">${{col.total_products}}개 상품 &middot; ${{secLabel}}</div>
        </div>
      </div>`;
  }}
  html += `</div>`;
  app.innerHTML = html;
}}

function onCollectionClick(colName) {{
  const sections = getCollectionSections(colName);
  state.collection = colName;
  state.section = sections[0];
  state.view = 'models';
  state.model = null;
  pushUrl();
  renderModels(true);
}}

function renderModels(skipPush) {{
  if (!skipPush) pushUrl();
  renderBreadcrumb();
  const app = document.getElementById('app');
  const colName = state.collection;
  const sections = getCollectionSections(colName);
  const models = getModels(colName, state.section);
  const totalInSection = DATA[colName].products.filter(p => p.section === state.section).length;

  let html = `
    <button class="back-btn" onclick="navigateTo('/')">&#8592; 전체 콜렉션</button>
    <div class="view-title">
      <h2>${{colName}} COLLECTION</h2>
      <div class="count">${{totalInSection}}개 상품</div>
    </div>`;

  if (sections.length > 1) {{
    html += `<div class="section-tabs">`;
    for (const sec of sections) {{
      const count = DATA[colName].products.filter(p => p.section === sec).length;
      const active = sec === state.section ? 'active' : '';
      html += `<div class="section-tab ${{active}}" onclick="switchSection('${{sec}}')">${{sec}} (${{count}})</div>`;
    }}
    html += `</div>`;
  }}

  html += `<div class="models-grid">`;
  for (const m of models) {{
    html += `
      <div class="model-card" onclick="onModelClick('${{m.model.replace(/'/g, "\\\\'")}}')">
        <img class="thumb" src="${{m.representative_image}}" alt="${{m.model}}" loading="lazy" onerror="this.style.background='#ddd'">
        <div class="info">
          <h3>${{m.model}}</h3>
          <div class="meta">${{m.count}}개 색상 &middot; ${{m.price_display}}</div>
        </div>
      </div>`;
  }}
  html += `</div>`;
  app.innerHTML = html;
}}

function switchSection(section) {{
  state.section = section;
  state.model = null;
  pushUrl();
  renderModels(true);
}}

function onModelClick(model) {{
  state.model = model;
  state.view = 'products';
  pushUrl();
  renderProducts(true);
}}

function renderProducts(skipPush) {{
  if (!skipPush) pushUrl();
  renderBreadcrumb();
  const app = document.getElementById('app');
  const products = getProducts(state.collection, state.section, state.model);

  const backUrl = '/' + state.collection.toLowerCase() + (state.section !== getCollectionSections(state.collection)[0] ? '?section=' + state.section : '');
  let html = `
    <button class="back-btn" onclick="navigateTo('${{backUrl}}')">&#8592; ${{state.collection}} 모델 목록</button>
    <div class="view-title">
      <h2>${{state.model}}</h2>
      <div class="count">${{products.length}}개 색상 &middot; ${{state.section}}</div>
    </div>
    <div class="products-grid">`;

  for (const p of products) {{
    const existingCode = productCodes[String(p.product_id)] || '';
    html += `
      <div class="product-card">
        <a href="${{p.url}}" target="_blank" rel="noopener">
          ${{p.sold_out ? '<div class="sold-out-badge">SOLD OUT</div>' : ''}}
          <img class="thumb" src="${{p.image_url}}" alt="${{p.product_name}}" loading="lazy" onerror="this.style.background='#ddd'">
          <div class="info">
            <div class="name">${{p.product_name}}</div>
            ${{p.color ? `<div class="color">${{p.color}}</div>` : ''}}
            <div class="price">${{p.price}}</div>
            <div class="pid">ID: ${{p.product_id}}</div>
          </div>
        </a>
        <div class="info">
          <div class="code-row">
            <input class="code-input" id="code-input-${{p.product_id}}" type="text" value="${{existingCode}}" placeholder="상품번호 (예: wez03-cres)" oninput="saveCode(${{p.product_id}}, this.value)">
            <span class="code-status" id="code-status-${{p.product_id}}"></span>
          </div>
        </div>
      </div>`;
  }}
  html += `</div>`;
  app.innerHTML = html;
}}

/* ── 검색 ── */
function onSearch(query) {{
  const grid = document.getElementById('collectionsGrid');
  const results = document.getElementById('searchResults');
  if (!query.trim()) {{
    grid.classList.remove('hidden');
    results.classList.add('hidden');
    return;
  }}
  grid.classList.add('hidden');
  results.classList.remove('hidden');

  const q = query.toUpperCase().trim();
  let html = '';
  let totalFound = 0;

  const order = ['EZE','VENICE','VALENCIA','ROME','LONDON','DIJON','MADRID','MILANO','SEOUL','MOSCOW','TORINO','BOSTON'];
  for (const colName of order) {{
    if (!DATA[colName]) continue;
    const matches = DATA[colName].products.filter(p =>
      p.product_name.toUpperCase().includes(q) ||
      p.model.toUpperCase().includes(q)
    );
    if (matches.length === 0) continue;
    totalFound += matches.length;

    html += `<div class="result-group"><h3>${{colName}} (${{matches.length}}개)</h3><div class="products-grid">`;
    for (const p of matches) {{
      html += `
        <div class="product-card">
          <a href="${{p.url}}" target="_blank" rel="noopener">
            ${{p.sold_out ? '<div class="sold-out-badge">SOLD OUT</div>' : ''}}
            <img class="thumb" src="${{p.image_url}}" alt="${{p.product_name}}" loading="lazy" onerror="this.style.background='#ddd'">
            <div class="info">
              <div class="name">${{p.product_name}} (${{p.section}})</div>
              <div class="price">${{p.price}}</div>
              <div class="pid">ID: ${{p.product_id}}</div>
            </div>
          </a>
        </div>`;
    }}
    html += `</div></div>`;
  }}

  if (totalFound === 0) {{
    html = `<p style="text-align:center;color:#999;margin-top:40px;">검색 결과가 없습니다.</p>`;
  }} else {{
    html = `<p style="text-align:center;color:#999;margin-bottom:16px;">${{totalFound}}개 상품 검색됨</p>` + html;
  }}
  results.innerHTML = html;
}}

/* ── 네비게이션 ── */
function navigateTo(url) {{
  history.pushState(null, '', url);
  state = urlToState();
  renderCurrentView(true);
}}

// 초기 렌더링 — 상품번호 로드 후 URL에서 상태 복원
(async () => {{
  await fetchCodes();
  state = urlToState();
  renderCurrentView(true);
}})();
</script>
</body>
</html>"""


def main():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    html = build_html(data)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"웹 UI 생성 완료: {OUTPUT_PATH}")
    print(f"브라우저에서 열어보세요!")


if __name__ == "__main__":
    main()
