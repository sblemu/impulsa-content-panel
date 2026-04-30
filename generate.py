#!/usr/bin/env python3
"""
IMPULSA Content Panel — Generator
Lee Calendario Editorial desde Google Sheets y genera index.html estático.
Uso: python3 generate.py
"""

import json, re
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
import gspread

SHEET_ID  = "1tp1MRjJU6g6vF5VD78k-xbV6tcSM5XVZb_FQe9HIdIs"
SA_KEY    = "/Users/sebastian/.config/claude-keys/google-sheets-sa.json"
TAB_NAME  = "Calendario Editorial"
OUT_FILE  = "index.html"

# ── READ SHEET ──────────────────────────────────────────────────────────────

def read_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds  = Credentials.from_service_account_file(SA_KEY, scopes=scopes)
    gc     = gspread.authorize(creds)
    ws     = gc.open_by_key(SHEET_ID).worksheet(TAB_NAME)
    rows   = ws.get_all_records()
    return rows

def parse_fecha(s):
    """DD/MM/YYYY → YYYY-MM-DD"""
    if not s:
        return ""
    try:
        return datetime.strptime(s.strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
    except:
        return s

def normalize(rows):
    items = []
    for r in rows:
        fecha = parse_fecha(r.get("FECHA", ""))
        if not fecha:
            continue
        items.append({
            "semana":       r.get("SEMANA", ""),
            "fecha":        fecha,
            "hora":         r.get("HORA (CLT)", ""),
            "tipo":         r.get("TIPO", ""),
            "plataformas":  [p.strip() for p in r.get("PLATAFORMAS", "").split("·") if p.strip()],
            "titulo":       r.get("TITULO / DESCRIPCIÓN", ""),
            "estado":       r.get("ESTADO", ""),
            "link":         r.get("LINK", ""),
            "responsable":  r.get("RESPONSABLE", ""),
            "ref":          r.get("REF", ""),
            "notas":        r.get("NOTAS", ""),
        })
    items.sort(key=lambda x: (x["fecha"], x["hora"] or "23:59"))
    return items

# ── HTML TEMPLATE ────────────────────────────────────────────────────────────

PLATFORM_META = {
    "Instagram":        {"color": "#e1306c", "bg": "#2a0f19", "icon": "📸"},
    "TikTok":           {"color": "#ff0050", "bg": "#1a0008", "icon": "🎵"},
    "YouTube":          {"color": "#ff0000", "bg": "#1a0000", "icon": "▶️"},
    "YouTube Shorts":   {"color": "#ff4444", "bg": "#1a0000", "icon": "⚡"},
    "LinkedIn":         {"color": "#0a66c2", "bg": "#001a33", "icon": "💼"},
    "Blog":             {"color": "#10b981", "bg": "#001a12", "icon": "📝"},
    "Blog SistemaImpulsa": {"color": "#10b981", "bg": "#001a12", "icon": "📝"},
    "Blog ImpulsaSuite":   {"color": "#10b981", "bg": "#001a12", "icon": "📝"},
    "Blog CRMPeru":     {"color": "#10b981", "bg": "#001a12", "icon": "📝"},
    "Blog Colombia":    {"color": "#10b981", "bg": "#001a12", "icon": "📝"},
    "Email":            {"color": "#f59e0b", "bg": "#1a1200", "icon": "✉️"},
    "Twitter":          {"color": "#1da1f2", "bg": "#001a26", "icon": "🐦"},
    "Facebook":         {"color": "#1877f2", "bg": "#001226", "icon": "📘"},
}

TIPO_META = {
    "Video Corto":      {"color": "#6366f1", "bg": "#12123a"},
    "Video Largo":      {"color": "#8b5cf6", "bg": "#160a2e"},
    "Artículo":         {"color": "#10b981", "bg": "#001a12"},
    "Newsletter":       {"color": "#f59e0b", "bg": "#1a1200"},
    "Mail Click":       {"color": "#ef4444", "bg": "#1a0000"},
    "Carrusel":         {"color": "#ec4899", "bg": "#1a0014"},
    "Post Imagen":      {"color": "#14b8a6", "bg": "#001a18"},
    "Story":            {"color": "#a855f7", "bg": "#14002e"},
    "Evento":           {"color": "#06b6d4", "bg": "#001a20"},
    "Reel":             {"color": "#e1306c", "bg": "#2a0f19"},
    "Short":            {"color": "#ff4444", "bg": "#1a0000"},
}

ESTADO_META = {
    "Publicado":        {"color": "#10b981", "bg": "#052e16"},
    "Programado":       {"color": "#6366f1", "bg": "#1e1b4b"},
    "En Producción":    {"color": "#f59e0b", "bg": "#1c1200"},
    "Borrador":         {"color": "#9ca3af", "bg": "#1f2937"},
    "Idea":             {"color": "#a855f7", "bg": "#1a0035"},
    "Cancelado":        {"color": "#ef4444", "bg": "#1a0000"},
}

DIAS_ES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
MESES_ES = ["", "ene", "feb", "mar", "abr", "may", "jun",
            "jul", "ago", "sep", "oct", "nov", "dic"]

def platform_badge(name):
    m = PLATFORM_META.get(name, {"color": "#888", "bg": "#222", "icon": "🌐"})
    return (f'<span class="badge" style="color:{m["color"]};background:{m["bg"]};'
            f'border:1px solid {m["color"]}22">{m["icon"]} {name}</span>')

def tipo_badge(name):
    if not name:
        return ""
    m = TIPO_META.get(name, {"color": "#888", "bg": "#222"})
    return (f'<span class="badge tipo-badge" style="color:{m["color"]};background:{m["bg"]};'
            f'border:1px solid {m["color"]}44">{name}</span>')

def estado_badge(name):
    if not name:
        return ""
    m = ESTADO_META.get(name, {"color": "#888", "bg": "#222"})
    return (f'<span class="estado-badge" style="color:{m["color"]};background:{m["bg"]};'
            f'border:1px solid {m["color"]}66">{name}</span>')

def build_card(item):
    plat_html = " ".join(platform_badge(p) for p in item["plataformas"])
    link_open  = f'<a href="{item["link"]}" target="_blank" rel="noopener">' if item["link"] else "<span>"
    link_close = "</a>" if item["link"] else "</span>"
    hora_html  = f'<span class="hora">🕐 {item["hora"]} CLT</span>' if item["hora"] else ""
    notas_html = f'<div class="notas">{item["notas"]}</div>' if item["notas"] else ""
    resp_html  = (f'<span class="responsable">{item["responsable"]}</span>'
                  if item["responsable"] else "")
    return f"""
    <div class="card" data-tipo="{item["tipo"]}" data-estado="{item["estado"]}"
         data-plataformas="{", ".join(item["plataformas"])}">
      <div class="card-top">
        {tipo_badge(item["tipo"])}
        {estado_badge(item["estado"])}
      </div>
      <div class="card-title">{link_open}{item["titulo"] or "(sin título)"}{link_close}</div>
      <div class="card-meta">
        {hora_html}
        {resp_html}
      </div>
      <div class="card-platforms">{plat_html}</div>
      {notas_html}
    </div>"""

def build_week_grid(items, week_start):
    days = [week_start + timedelta(days=i) for i in range(7)]
    cols = []
    total = 0
    for d in days:
        ds = d.strftime("%Y-%m-%d")
        day_items = [x for x in items if x["fecha"] == ds]
        total += len(day_items)
        label = f"{DIAS_ES[d.weekday()]} {d.day}"
        cards_html = "".join(build_card(it) for it in day_items)
        empty = '<div class="empty-day">—</div>' if not day_items else ""
        cols.append(f"""
      <div class="day-col {"today" if ds == datetime.now().strftime("%Y-%m-%d") else ""}">
        <div class="day-header">
          <span class="day-name">{label}</span>
          {"<span class='day-count'>"+str(len(day_items))+"</span>" if day_items else ""}
        </div>
        <div class="day-cards">{cards_html}{empty}</div>
      </div>""")
    return "".join(cols), total

def get_weeks(items):
    weeks = set()
    for it in items:
        try:
            d = datetime.strptime(it["fecha"], "%Y-%m-%d")
            mon = d - timedelta(days=d.weekday())
            weeks.add(mon.strftime("%Y-%m-%d"))
        except:
            pass
    today_mon = datetime.now()
    today_mon -= timedelta(days=today_mon.weekday())
    weeks.add(today_mon.strftime("%Y-%m-%d"))
    return sorted(weeks)

def week_label(mon_str):
    mon = datetime.strptime(mon_str, "%Y-%m-%d")
    sun = mon + timedelta(days=6)
    iso = mon.isocalendar()[1]
    return f"W{iso} · {mon.day} {MESES_ES[mon.month]} — {sun.day} {MESES_ES[sun.month]} {sun.year}"

def tipo_stats(items):
    counts = {}
    for it in items:
        t = it["tipo"] or "Sin tipo"
        counts[t] = counts.get(t, 0) + 1
    return counts

def build_html(items):
    weeks = get_weeks(items)
    today_mon = datetime.now()
    today_mon -= timedelta(days=today_mon.weekday())
    today_mon_s = today_mon.strftime("%Y-%m-%d")

    # Build week tabs + grids
    tabs_html  = []
    grids_html = []
    for i, w in enumerate(weeks):
        wmon = datetime.strptime(w, "%Y-%m-%d")
        wlbl = week_label(w)
        is_current = (w == today_mon_s)
        grid_html, total = build_week_grid(items, wmon)
        tabs_html.append(
            f'<button class="tab {"active" if is_current else ""}" onclick="showWeek({i})" id="tab-{i}">'
            f'{wlbl}<span class="tbadge">{total}</span></button>'
        )
        grids_html.append(
            f'<div class="week-grid {"active" if is_current else ""}" id="grid-{i}">'
            f'<div class="day-row">{grid_html}</div></div>'
        )

    tabs_html_str  = "\n".join(tabs_html)
    grids_html_str = "\n".join(grids_html)

    # Stats for this week
    today_items = [it for it in items
                   if abs((datetime.strptime(it["fecha"], "%Y-%m-%d") - today_mon).days) < 7]
    total_week  = len(today_items)
    published   = sum(1 for it in today_items if it["estado"] == "Publicado")
    scheduled   = sum(1 for it in today_items if it["estado"] == "Programado")
    production  = sum(1 for it in today_items if it["estado"] == "En Producción")
    total_all   = len(items)
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>IMPULSA · Content Panel</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{{
  --bg:#0a0a0e; --surface:#111118; --s2:#16161f; --border:#1e1e2c; --b2:#252535;
  --text:#e2e2eb; --t2:#888899; --t3:#44445a;
  --indigo:#6366f1; --green:#10b981; --amber:#f59e0b; --red:#ef4444;
  --blue:#3b82f6;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Inter',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;font-size:13px}}
a{{color:inherit;text-decoration:none}}

/* HEADER */
.header{{display:flex;align-items:center;justify-content:space-between;padding:14px 28px;border-bottom:1px solid var(--border);background:var(--bg);position:sticky;top:0;z-index:100}}
.header-left{{display:flex;align-items:center;gap:14px}}
.logo{{font-size:18px;font-weight:700;letter-spacing:-0.5px;color:#fff}}
.logo span{{color:var(--indigo)}}
.header-sub{{font-size:11px;color:var(--t3);font-family:monospace}}
.generated{{font-size:10px;color:var(--t3)}}

/* STATS BAR */
.stats-bar{{display:flex;gap:8px;padding:14px 28px;border-bottom:1px solid var(--border);background:var(--surface);flex-wrap:wrap}}
.stat-pill{{display:flex;align-items:center;gap:6px;background:var(--s2);border:1px solid var(--border);border-radius:20px;padding:5px 14px}}
.stat-num{{font-size:15px;font-weight:700}}
.stat-lbl{{font-size:11px;color:var(--t2)}}
.c-green{{color:var(--green)}} .c-indigo{{color:var(--indigo)}}
.c-amber{{color:var(--amber)}} .c-slate{{color:#6b7280}}

/* TABS */
.tabs-row{{display:flex;align-items:center;gap:2px;padding:14px 28px 0;border-bottom:1px solid var(--border);overflow-x:auto;background:var(--bg)}}
.tab{{padding:8px 16px;font-size:12px;font-weight:500;cursor:pointer;border-radius:8px 8px 0 0;color:var(--t2);background:transparent;border:none;transition:all .15s;white-space:nowrap;font-family:'Inter',sans-serif}}
.tab:hover{{color:var(--text)}}
.tab.active{{color:#f0f0f8;background:var(--surface);border:1px solid var(--border);border-bottom:1px solid var(--surface)}}
.tbadge{{display:inline-flex;align-items:center;justify-content:center;min-width:18px;height:18px;border-radius:9px;font-size:10px;font-weight:600;margin-left:5px;background:var(--b2);color:var(--t2);padding:0 4px}}
.tab.active .tbadge{{color:var(--text)}}

/* WEEK GRID */
.week-grid{{display:none;padding:20px 28px}}
.week-grid.active{{display:block}}
.day-row{{display:grid;grid-template-columns:repeat(7,1fr);gap:10px;min-height:400px}}

/* DAY COLUMN */
.day-col{{background:var(--surface);border:1px solid var(--border);border-radius:10px;overflow:hidden;display:flex;flex-direction:column}}
.day-col.today{{border-color:var(--indigo)44;box-shadow:0 0 0 1px var(--indigo)22}}
.day-header{{display:flex;align-items:center;justify-content:space-between;padding:8px 10px;border-bottom:1px solid var(--border);background:var(--s2)}}
.day-name{{font-size:11px;font-weight:600;color:var(--t2);text-transform:uppercase;letter-spacing:.5px}}
.today .day-name{{color:var(--indigo)}}
.day-count{{font-size:11px;font-weight:700;color:var(--text);background:var(--b2);border-radius:10px;padding:1px 7px}}
.day-cards{{display:flex;flex-direction:column;gap:8px;padding:8px;flex:1}}
.empty-day{{color:var(--t3);font-size:12px;text-align:center;padding:20px 0}}

/* CARD */
.card{{background:var(--s2);border:1px solid var(--border);border-radius:8px;padding:10px;transition:border-color .15s,transform .1s;cursor:default}}
.card:hover{{border-color:var(--b2);transform:translateY(-1px)}}
.card-top{{display:flex;align-items:center;gap:5px;flex-wrap:wrap;margin-bottom:7px}}
.card-title{{font-size:12px;font-weight:500;color:var(--text);line-height:1.4;margin-bottom:6px}}
.card-title a:hover{{color:var(--indigo)}}
.card-meta{{display:flex;align-items:center;gap:8px;margin-bottom:6px;flex-wrap:wrap}}
.hora{{font-size:10px;color:var(--t2)}}
.responsable{{font-size:10px;color:var(--t3);background:var(--b2);border-radius:4px;padding:1px 6px}}
.card-platforms{{display:flex;flex-wrap:wrap;gap:4px;margin-top:4px}}
.notas{{font-size:10px;color:var(--t3);margin-top:6px;font-style:italic;line-height:1.4}}

/* BADGES */
.badge{{display:inline-flex;align-items:center;gap:3px;font-size:10px;font-weight:500;border-radius:4px;padding:2px 7px;white-space:nowrap}}
.tipo-badge{{font-weight:600}}
.estado-badge{{font-size:10px;font-weight:600;border-radius:4px;padding:2px 8px;border:1px solid transparent}}

/* FILTERS */
.filters-row{{display:flex;align-items:center;gap:8px;padding:12px 28px;border-bottom:1px solid var(--border);background:var(--bg);flex-wrap:wrap}}
.filter-label{{font-size:11px;color:var(--t3);font-weight:600;text-transform:uppercase;letter-spacing:.5px}}
.filter-btn{{font-size:11px;font-weight:500;padding:4px 12px;border-radius:12px;background:var(--s2);border:1px solid var(--border);color:var(--t2);cursor:pointer;transition:all .15s;font-family:'Inter',sans-serif}}
.filter-btn:hover{{color:var(--text);border-color:var(--b2)}}
.filter-btn.active{{background:var(--indigo)22;border-color:var(--indigo)66;color:var(--indigo)}}

@media(max-width:900px){{
  .day-row{{grid-template-columns:repeat(3,1fr)}}
}}
@media(max-width:600px){{
  .day-row{{grid-template-columns:1fr}}
  .header{{padding:12px 16px}}
  .week-grid,.filters-row,.stats-bar,.tabs-row{{padding-left:16px;padding-right:16px}}
}}
</style>
</head>
<body>

<div class="header">
  <div class="header-left">
    <div>
      <div class="logo">IMPULSA<span>.</span></div>
      <div class="header-sub">Content Panel</div>
    </div>
  </div>
  <div class="generated">Actualizado: {generated_at}</div>
</div>

<div class="stats-bar">
  <div class="stat-pill">
    <span class="stat-num c-indigo">{total_week}</span>
    <span class="stat-lbl">Esta semana</span>
  </div>
  <div class="stat-pill">
    <span class="stat-num c-green">{published}</span>
    <span class="stat-lbl">Publicados</span>
  </div>
  <div class="stat-pill">
    <span class="stat-num" style="color:var(--indigo)">{scheduled}</span>
    <span class="stat-lbl">Programados</span>
  </div>
  <div class="stat-pill">
    <span class="stat-num c-amber">{production}</span>
    <span class="stat-lbl">En producción</span>
  </div>
  <div class="stat-pill">
    <span class="stat-num c-slate">{total_all}</span>
    <span class="stat-lbl">Total en grilla</span>
  </div>
</div>

<div class="filters-row">
  <span class="filter-label">Plataforma:</span>
  <button class="filter-btn active" onclick="filterBy('plataforma','all',this)">Todas</button>
  <button class="filter-btn" onclick="filterBy('plataforma','Instagram',this)">📸 Instagram</button>
  <button class="filter-btn" onclick="filterBy('plataforma','TikTok',this)">🎵 TikTok</button>
  <button class="filter-btn" onclick="filterBy('plataforma','YouTube',this)">▶️ YouTube</button>
  <button class="filter-btn" onclick="filterBy('plataforma','LinkedIn',this)">💼 LinkedIn</button>
  <button class="filter-btn" onclick="filterBy('plataforma','Blog',this)">📝 Blog</button>
  <button class="filter-btn" onclick="filterBy('plataforma','Email',this)">✉️ Email</button>
  &nbsp;
  <span class="filter-label">Estado:</span>
  <button class="filter-btn active" onclick="filterBy('estado','all',this)" id="estado-all">Todos</button>
  <button class="filter-btn" onclick="filterBy('estado','Publicado',this)">Publicado</button>
  <button class="filter-btn" onclick="filterBy('estado','Programado',this)">Programado</button>
  <button class="filter-btn" onclick="filterBy('estado','En Producción',this)">En Producción</button>
</div>

<div class="tabs-row">
{tabs_html_str}
</div>

{grids_html_str}

<script>
let activeWeek = {weeks.index(today_mon_s) if today_mon_s in weeks else 0};
let filters = {{plataforma: 'all', estado: 'all'}};

function showWeek(i) {{
  document.querySelectorAll('.week-grid').forEach(g => g.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById('grid-' + i).classList.add('active');
  document.getElementById('tab-' + i).classList.add('active');
  activeWeek = i;
}}

function filterBy(type, value, btn) {{
  filters[type] = value;
  // update button states for this filter group
  const parent = btn.parentElement;
  parent.querySelectorAll('.filter-btn').forEach(b => {{
    if (b.getAttribute('onclick') && b.getAttribute('onclick').includes("'" + type + "'")) {{
      b.classList.remove('active');
    }}
  }});
  btn.classList.add('active');
  applyFilters();
}}

function applyFilters() {{
  document.querySelectorAll('.card').forEach(card => {{
    const tipo      = card.dataset.tipo || '';
    const estado    = card.dataset.estado || '';
    const plats     = card.dataset.plataformas || '';

    let show = true;
    if (filters.plataforma !== 'all') {{
      // match partial (e.g. "YouTube" matches "YouTube Shorts")
      show = show && plats.toLowerCase().includes(filters.plataforma.toLowerCase());
    }}
    if (filters.estado !== 'all') {{
      show = show && estado === filters.estado;
    }}
    card.style.display = show ? '' : 'none';
  }});
}}
</script>
</body>
</html>"""

# ── MAIN ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")

    print("📥 Leyendo Calendario Editorial...")
    rows  = read_sheet()
    items = normalize(rows)
    print(f"   {len(items)} piezas de contenido cargadas")

    print("🏗️  Generando HTML...")
    html = build_html(items)

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ {OUT_FILE} generado ({len(html)//1024}KB)")
    print(f"   Abre en: file://{__file__.replace('generate.py', OUT_FILE)}")
