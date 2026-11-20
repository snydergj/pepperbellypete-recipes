#!/usr/bin/env python3
"""Regenerate pepperbellypete-recipes.html from recipes.json (source of truth)."""
import json, html, pathlib, sys

D = pathlib.Path(__file__).parent
sys.path.insert(0, str(D))
from parse_ingredients import annotate_recipes

CAT_ORDER = [
    "Beef Chili",
    "Chicken Chili",
    "Green Chili",
    "Chili Mac & Casserole",
    "Dip",
]

def cat_key(r):
    c = r.get("category") or "Other"
    return (CAT_ORDER.index(c) if c in CAT_ORDER else len(CAT_ORDER), r["title"].lower())

def clean_num(x):
    if x is None:
        return None
    x = float(x)
    if abs(x - round(x)) < 1e-9:
        return int(round(x))
    return round(x, 4)

def ing_text(ing):
    if isinstance(ing, str):
        return ing
    return ing.get("text") or ing.get("item") or ""

def tidy_ingredient(ing):
    return {
        "text": ing.get("text", ""),
        "qty": clean_num(ing.get("qty")),
        "unit": ing.get("unit"),
        "item": ing.get("item"),
        "shop": ing.get("shop") or "other",
        "each_oz": clean_num(ing.get("each_oz")),
        "approx": bool(ing.get("approx")),
        "optional": bool(ing.get("optional")),
    }

# Load, parse, and persist structured ingredients so rebuilds stay in sync.
raw = json.loads((D / "recipes.json").read_text())
annotate_recipes(raw)
for r in raw:
    r["ingredients"] = [tidy_ingredient(i) if not isinstance(i, str) else tidy_ingredient({"text": i}) for i in r["ingredients"]]
(D / "recipes.json").write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n")

recipes = sorted(raw, key=cat_key)
e = html.escape

cats = []
for c in CAT_ORDER:
    n = sum(1 for r in recipes if r.get("category") == c)
    if n:
        cats.append((c, n))
other = sum(1 for r in recipes if r.get("category") not in CAT_ORDER)
if other:
    cats.append(("Other", other))

def search_blob(r):
    texts = [ing_text(i) for i in (r.get("ingredients") or [])]
    parts = [
        r.get("title", ""),
        r.get("channel", ""),
        r.get("category", ""),
        r.get("summary", ""),
        " ".join(texts),
        " ".join(r.get("instructions") or []),
        " ".join(r.get("notes") or []),
    ]
    return e(" ".join(parts).lower())

def card(r, i):
    ing = "".join(f"<li>{e(ing_text(x))}</li>" for x in r.get("ingredients") or [])
    steps = "".join(f"<li>{e(x)}</li>" for x in r.get("instructions") or [])
    notes = "".join(f"<li>{e(x)}</li>" for x in r.get("notes") or [])
    meta_bits = [r.get("category", ""), r.get("servings", ""), r.get("time", "")]
    meta = " · ".join(e(x) for x in meta_bits if x)
    cat = e(r.get("category") or "")
    rid = e(r["id"])
    title = e(r["title"])
    return f'''<article class="recipe-wrap" id="r{i}" data-id="{rid}" data-category="{cat}" data-search="{search_blob(r)}">
<label class="pick" title="Add to shopping list">
  <input type="checkbox" class="pick-box" data-id="{rid}" aria-label="Add {title} to the shopping list">
</label>
<details class="recipe">
<summary>
  <span class="tag">{cat}</span>
  <span class="week-badge">This week's pick</span>
  <h2>{title}</h2>
  <p class="meta">{meta}</p>
</summary>
<p><a href="{e(r.get("url",""))}" target="_blank" rel="noopener">Watch the video</a></p>
{f'<p class="desc">{e(r["summary"])}</p>' if r.get("summary") else ""}
<div class="cols">
  <section><h3>Ingredients</h3><ul>{ing}</ul></section>
  <section><h3>Instructions</h3><ol>{steps}</ol></section>
</div>
{f'<section class="notes"><h3>Notes</h3><ul>{notes}</ul></section>' if notes else ""}
</details>
</article>'''

filters = ['<button type="button" class="on" data-cat="all">All ({n})</button>'.format(n=len(recipes))]
for c, n in cats:
    filters.append(f'<button type="button" data-cat="{e(c)}">{e(c)} ({n})</button>')

index_parts = []
current = None
for i, r in enumerate(recipes):
    c = r.get("category") or "Other"
    if c != current:
        if current is not None:
            index_parts.append("</ul>")
        index_parts.append(f'<h3 class="idx-cat">{e(c)}</h3><ul class="index">')
        current = c
    index_parts.append(f'<li data-for="r{i}"><a href="#r{i}">{e(r["title"])}</a></li>')
if current is not None:
    index_parts.append("</ul>")

body = "".join(card(r, i) for i, r in enumerate(recipes)) or (
    '<p class="empty">No recipes yet. Send a YouTube link to add the first one.</p>'
)

# Compact recipe payload for the shopping list and weekly pick (no instructions).
payload = []
for r in recipes:
    payload.append({
        "id": r["id"],
        "title": r["title"],
        "category": r.get("category") or "",
        "summary": r.get("summary") or "",
        "servings": r.get("servings") or "",
        "url": r.get("url") or "",
        "ingredients": r.get("ingredients") or [],
    })
payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

shop_js = (D / "shop.js").read_text()
if shop_js.startswith("\ufeff"):
    shop_js = shop_js[1:]

html_out = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pepperbellypete Chili Recipes</title>
<style>
:root {{
  --bg: #f7f1e8;
  --paper: #fffdf8;
  --ink: #2a2118;
  --muted: #6d5e50;
  --accent: #9c3b24;
  --accent-soft: #f3e0d4;
  --line: #e4d5c4;
  --shadow: 0 1px 3px rgba(60,30,10,.08);
}}
* {{ box-sizing: border-box; }}
body {{
  font-family: Georgia, "Times New Roman", serif;
  max-width: 920px;
  margin: 0 auto;
  padding: 2rem 1.1rem 7rem;
  background: var(--bg);
  color: var(--ink);
}}
header h1 {{
  color: var(--accent);
  margin: 0 0 .3rem;
  font-size: 2rem;
  letter-spacing: -0.02em;
}}
header .lede {{ color: var(--muted); margin: 0 0 1.2rem; }}
#q {{
  width: 100%;
  padding: .7rem .9rem;
  font-size: 1rem;
  font-family: inherit;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
}}
.filters {{
  display: flex;
  flex-wrap: wrap;
  gap: .4rem;
  margin: .9rem 0 1.2rem;
}}
.filters button, .shop-actions button, .shop-bar button, .weekly-actions button {{
  font: inherit;
  font-size: .88rem;
  padding: .35rem .7rem;
  border: 1px solid var(--line);
  background: #fff;
  color: var(--ink);
  border-radius: 999px;
  cursor: pointer;
}}
.filters button.on, .shop-bar button.primary, .shop-actions button.primary, .weekly-actions button.primary {{
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}}
button:disabled {{ opacity: .45; cursor: not-allowed; }}
nav.toc {{
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: .8rem 1rem 1rem;
  margin: 0 0 1.5rem;
  box-shadow: var(--shadow);
}}
nav.toc > h2 {{ margin: 0 0 .4rem; font-size: 1.05rem; }}
.idx-cat {{
  margin: .8rem 0 .25rem;
  font-size: .78rem;
  text-transform: uppercase;
  letter-spacing: .08em;
  color: var(--accent);
}}
ul.index {{
  list-style: none;
  margin: 0;
  padding: 0;
  columns: 2;
  column-gap: 1.2rem;
}}
ul.index li {{ break-inside: avoid; margin: .15rem 0; }}
ul.index a {{ color: var(--ink); text-decoration: none; }}
ul.index a:hover {{ color: var(--accent); text-decoration: underline; }}
.recipe-wrap {{
  display: flex;
  align-items: flex-start;
  gap: .6rem;
  margin: 0 0 1rem;
}}
.recipe-wrap.is-picked .recipe {{
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent);
}}
.recipe-wrap.is-week-pick .recipe {{
  border-color: var(--accent);
  background: #fff6ef;
  box-shadow: 0 0 0 2px var(--accent-soft);
}}
.week-badge {{
  display: none;
  font-size: .72rem;
  text-transform: uppercase;
  letter-spacing: .06em;
  background: var(--accent);
  color: #fff;
  padding: .12rem .45rem;
  border-radius: 999px;
  margin-left: .35rem;
}}
.recipe-wrap.is-week-pick .week-badge {{ display: inline-block; }}
.pick {{
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.4rem;
  min-height: 2.4rem;
  margin-top: 1rem;
  cursor: pointer;
}}
.pick-box {{
  width: 1.2rem;
  height: 1.2rem;
  accent-color: var(--accent);
  cursor: pointer;
}}
.recipe {{
  flex: 1 1 auto;
  background: var(--paper);
  border-radius: 10px;
  padding: 0;
  margin: 0;
  box-shadow: var(--shadow);
  border: 1px solid var(--line);
  min-width: 0;
}}
.recipe > summary {{
  list-style: none;
  cursor: pointer;
  padding: 1rem 1.3rem;
}}
.recipe > summary::-webkit-details-marker {{ display: none; }}
.recipe > summary::after {{
  content: "▸";
  float: right;
  color: var(--muted);
  font-size: 1.1rem;
  margin-top: .4rem;
}}
.recipe[open] > summary::after {{ content: "▾"; }}
.recipe h2 {{ margin: .15rem 0 .15rem; font-size: 1.35rem; }}
.tag {{
  display: inline-block;
  font-size: .72rem;
  text-transform: uppercase;
  letter-spacing: .06em;
  background: var(--accent-soft);
  color: var(--accent);
  padding: .12rem .45rem;
  border-radius: 999px;
}}
.meta {{ color: var(--muted); font-size: .9rem; margin: 0; }}
.recipe > p, .recipe > .desc, .recipe > .cols, .recipe > .notes {{
  padding: 0 1.3rem;
}}
.recipe > .notes, .recipe > .cols {{ padding-bottom: 1.1rem; }}
.desc {{ margin: .3rem 0 1rem; }}
.cols {{ display: grid; grid-template-columns: 1fr 1.4fr; gap: 1.4rem; }}
h3 {{ margin: .2rem 0 .5rem; font-size: 1.05rem; color: var(--accent); }}
li {{ margin: .28rem 0; }}
a {{ color: var(--accent); }}
#empty {{ display: none; color: var(--muted); font-style: italic; }}
.weekly {{
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 1rem 1.2rem;
  margin: 0 0 1.2rem;
  box-shadow: var(--shadow);
}}
.weekly h2 {{ margin: 0 0 .35rem; font-size: 1.15rem; color: var(--accent); }}
.weekly .week-hint, .recommend-hint {{ color: var(--muted); font-size: .95rem; margin: 0; }}
.weekly .pick-title {{ font-size: 1.2rem; margin: 0 0 .25rem; }}
.weekly .pick-sum {{ margin: 0 0 .7rem; }}
.weekly-actions {{ display: flex; flex-wrap: wrap; align-items: center; gap: .4rem; margin: 0 0 .8rem; }}
.similar {{ list-style: none; margin: 0; padding: 0; }}
.similar li {{
  margin: 0 0 .75rem;
  padding-bottom: .75rem;
  border-bottom: 1px solid var(--line);
}}
.similar li:last-child {{ border-bottom: none; margin-bottom: 0; padding-bottom: 0; }}
.similar .sim-title {{ font-weight: bold; }}
.similar .why, .similar .needs {{ color: var(--muted); font-size: .9rem; display: block; margin: .15rem 0 0; }}
.similar .sim-actions {{ margin-top: .35rem; }}
#week-similar-wrap[hidden], #week-chosen[hidden], #week-empty[hidden] {{ display: none !important; }}
.shop-bar {{
  position: fixed;
  left: 0; right: 0; bottom: 0;
  z-index: 30;
  background: var(--paper);
  border-top: 1px solid var(--line);
  box-shadow: 0 -2px 10px rgba(60,30,10,.08);
}}
.shop-bar-inner {{
  max-width: 920px;
  margin: 0 auto;
  padding: .7rem 1.1rem calc(.7rem + env(safe-area-inset-bottom, 0));
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: .5rem .8rem;
}}
.shop-bar #shop-count {{ flex: 1 1 auto; }}
.shop-modal {{
  position: fixed;
  inset: 0;
  z-index: 40;
  background: rgba(42, 33, 24, .45);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding: 1rem 1rem 0;
}}
.shop-modal[hidden] {{ display: none !important; }}
.shop-panel {{
  background: var(--paper);
  color: var(--ink);
  width: min(640px, 100%);
  max-height: min(92vh, 860px);
  overflow: auto;
  border-radius: 12px 12px 0 0;
  box-shadow: 0 -4px 24px rgba(0,0,0,.18);
  padding: 1rem 1.2rem 1.3rem;
}}
.shop-panel-head {{
  display: flex;
  align-items: center;
  gap: .6rem;
  margin-bottom: .3rem;
}}
.shop-panel-head h2 {{ margin: 0; flex: 1; color: var(--accent); font-size: 1.3rem; }}
#shop-close {{
  font: inherit;
  font-size: 1.4rem;
  line-height: 1;
  border: none;
  background: none;
  color: var(--muted);
  cursor: pointer;
  padding: .2rem .4rem;
}}
.shop-for {{ color: var(--muted); font-size: .9rem; margin: 0 0 .8rem; }}
.shop-group {{ margin: 0 0 1rem; }}
.shop-group h3 {{ margin: 0 0 .4rem; }}
.shop-item {{
  list-style: none;
  display: flex;
  gap: .55rem;
  align-items: flex-start;
  margin: .35rem 0;
}}
.shop-item input {{ margin-top: .25rem; accent-color: var(--accent); width: 1.1rem; height: 1.1rem; flex: 0 0 auto; }}
.shop-item.done .shop-line {{ text-decoration: line-through; color: var(--muted); }}
.shop-sources {{ display: block; color: var(--muted); font-size: .8rem; margin-top: .1rem; }}
.shop-list {{ margin: 0; padding: 0; }}
.shop-actions {{ display: flex; flex-wrap: wrap; gap: .4rem; margin-top: .6rem; }}
@media (max-width: 700px) {{
  .cols {{ grid-template-columns: 1fr; }}
  ul.index {{ columns: 1; }}
  .shop-bar-inner {{ padding-left: 1rem; padding-right: 1rem; }}
}}
@media (min-width: 701px) {{
  .shop-modal {{ align-items: center; padding: 1.5rem; }}
  .shop-panel {{ border-radius: 12px; }}
}}
@media print {{
  body {{ background: #fff; padding: 0; max-width: none; }}
  #q, .filters, nav.toc, .recipe-wrap, .shop-bar, .weekly, header .lede, #empty {{
    display: none !important;
  }}
  .shop-modal {{
    position: static;
    background: none;
    display: block !important;
    padding: 0;
  }}
  .shop-panel {{
    box-shadow: none;
    border: none;
    max-height: none;
    width: 100%;
    border-radius: 0;
    padding: 0;
  }}
  #shop-close, .shop-actions {{ display: none !important; }}
}}
</style>
</head>
<body>
<header>
  <h1>Pepperbellypete Chili Recipes</h1>
  <p class="lede">{len(recipes)} chili recipes from Pete's YouTube shorts. Duplicate posts of the same pot are merged; variations are kept separate. Check a few recipes to build a combined shopping list.</p>
</header>
<aside class="weekly" id="weekly-pick">
  <h2>This week's pick</h2>
  <div id="week-empty">
    <p class="week-hint">Check one recipe to make it this week's pick</p>
  </div>
  <div id="week-chosen" hidden>
    <p class="pick-title" id="week-title"></p>
    <p class="pick-sum" id="week-sum"></p>
    <div class="weekly-actions">
      <a id="week-jump" href="#">Open recipe</a>
      <button type="button" class="primary" id="week-recommend" disabled title="Select just one recipe">Recommend Similar Recipes</button>
      <span class="recommend-hint" id="week-recommend-hint">Select just one recipe</span>
    </div>
    <div id="week-similar-wrap" hidden>
      <h3>Similar recipes</h3>
      <ul class="similar" id="week-similar"></ul>
    </div>
  </div>
</aside>
<input id="q" type="search" placeholder="Search recipes or ingredients..." autocomplete="off">
<div class="filters" id="filters">{''.join(filters)}</div>
<nav class="toc">
  <h2>Recipe index</h2>
  {''.join(index_parts)}
</nav>
<p id="empty">No recipes match that search.</p>
{body}
<div class="shop-bar" id="shop-bar">
  <div class="shop-bar-inner">
    <span id="shop-count">0 recipes selected</span>
    <button type="button" class="primary" id="shop-gen" disabled>Generate shopping list</button>
    <button type="button" id="bar-recommend" disabled title="Select just one recipe">Recommend Similar Recipes</button>
    <button type="button" id="shop-clear" hidden>Clear selection</button>
  </div>
</div>
<div id="shop-modal" class="shop-modal" hidden role="dialog" aria-modal="true" aria-labelledby="shop-modal-title">
  <div class="shop-panel">
    <div class="shop-panel-head">
      <h2 id="shop-modal-title">Shopping list</h2>
      <button type="button" id="shop-close" aria-label="Close">&times;</button>
    </div>
    <p class="shop-for" id="shop-for"></p>
    <div id="shop-body"></div>
    <div class="shop-actions">
      <button type="button" class="primary" id="shop-copy">Copy to clipboard</button>
      <button type="button" id="shop-print">Print</button>
      <button type="button" id="shop-clear-2">Clear selection</button>
    </div>
  </div>
</div>
<script>
window.RECIPES = {payload_json};
__SHOP_JS__
__UI_JS__
</script>
</body>
</html>
'''

ui_js = r'''
(function () {
  const q = document.getElementById('q');
  const empty = document.getElementById('empty');
  const wraps = [...document.querySelectorAll('.recipe-wrap')];
  const buttons = [...document.querySelectorAll('.filters button')];
  const STORAGE_SEL = 'pbp-chili-selected';
  const STORAGE_CHECKED = 'pbp-chili-checked';
  const STORAGE_WEEK = 'pbp-chili-week-pick';
  let cat = 'all';
  const byId = {};
  (window.RECIPES || []).forEach(r => { byId[r.id] = r; });

  function show() {
    const term = q.value.toLowerCase().trim();
    let n = 0;
    for (const a of wraps) {
      const okCat = cat === 'all' || a.dataset.category === cat;
      const okQ = !term || (a.dataset.search || '').includes(term);
      const on = okCat && okQ;
      a.style.display = on ? '' : 'none';
      const idx = document.querySelector('li[data-for="' + a.id + '"]');
      if (idx) idx.style.display = on ? '' : 'none';
      if (on) n++;
    }
    for (const h of document.querySelectorAll('.idx-cat')) {
      const ul = h.nextElementSibling;
      const any = ul && [...ul.children].some(li => li.style.display !== 'none');
      h.style.display = any ? '' : 'none';
      if (ul) ul.style.display = any ? '' : 'none';
    }
    empty.style.display = n ? 'none' : 'block';
  }
  q.addEventListener('input', show);
  buttons.forEach(b => b.addEventListener('click', () => {
    buttons.forEach(x => x.classList.remove('on'));
    b.classList.add('on');
    cat = b.dataset.cat;
    show();
  }));

  function loadSel() {
    try { return JSON.parse(localStorage.getItem(STORAGE_SEL) || '[]'); }
    catch (err) { return []; }
  }
  function saveSel(ids) {
    try { localStorage.setItem(STORAGE_SEL, JSON.stringify(ids)); } catch (err) {}
  }
  function selectedIds() {
    return [...document.querySelectorAll('.pick-box:checked')].map(b => b.dataset.id);
  }
  function applySel(ids) {
    const set = new Set(ids);
    document.querySelectorAll('.pick-box').forEach(box => {
      box.checked = set.has(box.dataset.id);
      const wrap = box.closest('.recipe-wrap');
      if (wrap) wrap.classList.toggle('is-picked', box.checked);
    });
    const n = ids.length;
    document.getElementById('shop-count').textContent =
      n === 0 ? '0 recipes selected' : (n === 1 ? '1 recipe selected' : n + ' recipes selected');
    document.getElementById('shop-gen').disabled = n === 0;
    document.getElementById('shop-clear').hidden = n === 0;
    updateWeekFromSelection(ids);
  }
  function syncFromBoxes() {
    const ids = selectedIds();
    saveSel(ids);
    applySel(ids);
  }

  function loadWeekId() {
    try { return localStorage.getItem(STORAGE_WEEK) || ''; }
    catch (err) { return ''; }
  }
  function saveWeekId(id) {
    try {
      if (id) localStorage.setItem(STORAGE_WEEK, id);
      else localStorage.removeItem(STORAGE_WEEK);
    } catch (err) {}
  }
  function jumpToRecipe(id, openCard) {
    const wrap = document.querySelector('.recipe-wrap[data-id="' + id + '"]');
    if (!wrap) return;
    if (openCard) {
      const det = wrap.querySelector('details.recipe');
      if (det) det.open = true;
    }
    wrap.scrollIntoView({ behavior: 'smooth', block: 'start' });
    if (wrap.id) try { history.replaceState(null, '', '#' + wrap.id); } catch (err) {}
  }
  function setRecommendEnabled(on) {
    ['week-recommend', 'bar-recommend'].forEach(id => {
      const b = document.getElementById(id);
      if (!b) return;
      b.disabled = !on;
      b.title = on ? 'Find recipes that use leftover ingredients' : 'Select just one recipe';
    });
    const hint = document.getElementById('week-recommend-hint');
    if (hint) hint.hidden = !!on;
  }
  function renderWeekPanel() {
    const weekId = loadWeekId();
    const pick = weekId ? byId[weekId] : null;
    const empty = document.getElementById('week-empty');
    const chosen = document.getElementById('week-chosen');
    document.querySelectorAll('.recipe-wrap').forEach(w => {
      w.classList.toggle('is-week-pick', !!(pick && w.dataset.id === pick.id));
    });
    if (!pick) {
      empty.hidden = false;
      chosen.hidden = true;
      return;
    }
    empty.hidden = true;
    chosen.hidden = false;
    document.getElementById('week-title').textContent = pick.title;
    document.getElementById('week-sum').textContent = pick.summary || '';
    const wrap = document.querySelector('.recipe-wrap[data-id="' + pick.id + '"]');
    const jump = document.getElementById('week-jump');
    jump.href = wrap ? ('#' + wrap.id) : '#';
    jump.onclick = ev => { ev.preventDefault(); jumpToRecipe(pick.id, true); };
  }
  function updateWeekFromSelection(ids) {
    if (ids.length === 1) saveWeekId(ids[0]);
    renderWeekPanel();
    setRecommendEnabled(ids.length === 1);
  }
  function showSimilarRecommendations() {
    const ids = selectedIds();
    if (ids.length !== 1) return;
    const pick = byId[ids[0]];
    if (!pick || !window.Shop) return;
    saveWeekId(pick.id);
    renderWeekPanel();
    const results = Shop.recommendSimilar(pick, RECIPES, 5);
    const wrap = document.getElementById('week-similar-wrap');
    const ul = document.getElementById('week-similar');
    wrap.hidden = false;
    ul.innerHTML = '';
    if (!results.length) {
      ul.innerHTML = '<li class="why">No close matches that would use up leftovers.</li>';
    } else {
      results.forEach(s => {
        const li = document.createElement('li');
        const title = document.createElement('a');
        title.className = 'sim-title';
        title.href = '#';
        title.textContent = s.title;
        title.addEventListener('click', ev => {
          ev.preventDefault();
          jumpToRecipe(s.id, true);
        });
        const why = document.createElement('span');
        why.className = 'why';
        why.textContent = s.reason;
        const needs = document.createElement('span');
        needs.className = 'needs';
        needs.textContent = s.needs.charAt(0).toUpperCase() + s.needs.slice(1) + '.';
        const actions = document.createElement('div');
        actions.className = 'sim-actions';
        const add = document.createElement('button');
        add.type = 'button';
        add.textContent = 'Add to list';
        add.addEventListener('click', ev => {
          ev.preventDefault();
          ev.stopPropagation();
          const next = new Set(loadSel());
          next.add(s.id);
          saveSel([...next]);
          applySel([...next]);
        });
        actions.appendChild(add);
        li.appendChild(title);
        li.appendChild(why);
        li.appendChild(needs);
        li.appendChild(actions);
        ul.appendChild(li);
      });
    }
    document.getElementById('weekly-pick').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  document.querySelectorAll('.pick-box').forEach(box => {
    box.addEventListener('click', ev => ev.stopPropagation());
    box.addEventListener('change', syncFromBoxes);
  });
  document.querySelectorAll('.pick').forEach(lab => {
    lab.addEventListener('click', ev => ev.stopPropagation());
  });

  applySel(loadSel());

  function clearSel() {
    saveSel([]);
    applySel([]);
    closeModal();
  }
  document.getElementById('shop-clear').addEventListener('click', clearSel);
  document.getElementById('shop-clear-2').addEventListener('click', clearSel);

  const modal = document.getElementById('shop-modal');
  function closeModal() { modal.hidden = true; }
  function openModal() { modal.hidden = false; }
  document.getElementById('shop-close').addEventListener('click', closeModal);
  modal.addEventListener('click', ev => { if (ev.target === modal) closeModal(); });
  document.addEventListener('keydown', ev => { if (ev.key === 'Escape' && !modal.hidden) closeModal(); });

  let lastRows = [];
  let lastSelected = [];

  function renderList() {
    const ids = selectedIds();
    lastSelected = ids.map(id => byId[id]).filter(Boolean);
    lastRows = Shop.mergeIngredients(lastSelected);
    const groups = Shop.groupedList(lastRows);
    document.getElementById('shop-for').textContent =
      'Combined from ' + lastSelected.map(r => r.title).join(', ') + '.';
    let checked = [];
    try { checked = JSON.parse(localStorage.getItem(STORAGE_CHECKED) || '[]'); } catch (err) {}
    const checkSet = new Set(checked);
    const body = document.getElementById('shop-body');
    body.innerHTML = groups.map(g => {
      const items = g.items.map(row => {
        const on = checkSet.has(row.item) ? ' checked' : '';
        const done = checkSet.has(row.item) ? ' done' : '';
        return '<li class="shop-item' + done + '">' +
          '<input type="checkbox" data-item="' + row.item.replace(/"/g, '&quot;') + '"' + on + '>' +
          '<span><span class="shop-line"></span><span class="shop-sources"></span></span></li>';
      }).join('');
      return '<section class="shop-group"><h3>' + g.label + '</h3><ul class="shop-list">' + items + '</ul></section>';
    }).join('');
    const lis = body.querySelectorAll('.shop-item');
    let k = 0;
    groups.forEach(g => g.items.forEach(row => {
      const li = lis[k++];
      li.querySelector('.shop-line').textContent = row.line;
      li.querySelector('.shop-sources').textContent = 'from ' + row.sources.join(', ');
    }));
    body.querySelectorAll('.shop-item input').forEach(inp => {
      inp.addEventListener('change', () => {
        const item = inp.getAttribute('data-item');
        let cur = [];
        try { cur = JSON.parse(localStorage.getItem(STORAGE_CHECKED) || '[]'); } catch (err) {}
        const set = new Set(cur);
        if (inp.checked) set.add(item); else set.delete(item);
        try { localStorage.setItem(STORAGE_CHECKED, JSON.stringify([...set])); } catch (err) {}
        inp.closest('.shop-item').classList.toggle('done', inp.checked);
      });
    });
  }

  document.getElementById('shop-gen').addEventListener('click', () => {
    if (!selectedIds().length) return;
    renderList();
    openModal();
  });
  document.getElementById('shop-print').addEventListener('click', () => window.print());
  document.getElementById('shop-copy').addEventListener('click', async () => {
    const text = Shop.listAsText(lastSelected, lastRows);
    const btn = document.getElementById('shop-copy');
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        ta.remove();
      }
      btn.textContent = 'Copied';
      setTimeout(() => { btn.textContent = 'Copy to clipboard'; }, 1500);
    } catch (err) {
      btn.textContent = 'Copy failed';
      setTimeout(() => { btn.textContent = 'Copy to clipboard'; }, 1500);
    }
  });

  document.getElementById('week-recommend').addEventListener('click', showSimilarRecommendations);
  document.getElementById('bar-recommend').addEventListener('click', showSimilarRecommendations);
})();
'''

html_out = html_out.replace("__SHOP_JS__", shop_js).replace("__UI_JS__", ui_js)
(D / "pepperbellypete-recipes.html").write_text(html_out)
# Also write index.html so a rebuild in the export folder is ready to serve.
(D / "index.html").write_text(html_out)
print(f"Built page with {len(recipes)} recipes")
