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

# ── READ SHEET ───────────────────────────────────────────────────────────────

def read_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds  = Credentials.from_service_account_file(SA_KEY, scopes=scopes)
    gc     = gspread.authorize(creds)
    ws     = gc.open_by_key(SHEET_ID).worksheet(TAB_NAME)
    return ws.get_all_records()

def parse_fecha(s):
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
            "semana":      r.get("SEMANA", ""),
            "fecha":       fecha,
            "hora":        r.get("HORA (CLT)", ""),
            "tipo":        r.get("TIPO", ""),
            "plataformas": [p.strip() for p in r.get("PLATAFORMAS", "").split("·") if p.strip()],
            "titulo":      r.get("TITULO / DESCRIPCIÓN", ""),
            "estado":      r.get("ESTADO", ""),
            "link":        r.get("LINK", ""),
            "responsable": r.get("RESPONSABLE", ""),
            "ref":         r.get("REF", ""),
            "notas":       r.get("NOTAS", ""),
        })
    items.sort(key=lambda x: (x["fecha"], x["hora"] or "23:59"))
    return items

# ── BRAND TOKENS (IMPULSA Suite) ─────────────────────────────────────────────

# Primary teal from impulsasuite.com custom.css
PRIMARY       = "#058b8a"
PRIMARY_LIGHT = "#e6f7f7"   # very light teal bg tint
PRIMARY_MID   = "#dcf5f0"   # hero bg from original site
PRIMARY_DARK  = "#046b6a"
WHITE         = "#ffffff"
BG            = "#f5fbfb"   # overall page background (mint tint)
CARD_BG       = "#ffffff"
BORDER        = "#d4eeee"
TEXT          = "#4d4d4d"
TEXT2         = "#646464"
TEXT3         = "#999999"
SHADOW        = "0 2px 12px rgba(5,139,138,.08)"
SHADOW_HOVER  = "0 6px 20px rgba(5,139,138,.15)"
RADIUS_CARD   = "16px"
RADIUS_PILL   = "35px"
RADIUS_BADGE  = "20px"

PLATFORM_META = {
    "Instagram":           {"color": "#e1306c", "bg": "#fce8f1", "icon": "📸"},
    "TikTok":              {"color": "#ff0050", "bg": "#ffe5ee", "icon": "🎵"},
    "YouTube":             {"color": "#cc0000", "bg": "#ffe5e5", "icon": "▶"},
    "YouTube Shorts":      {"color": "#cc0000", "bg": "#ffe5e5", "icon": "⚡"},
    "LinkedIn":            {"color": "#0a66c2", "bg": "#e5f0fb", "icon": "💼"},
    "Blog":                {"color": PRIMARY,   "bg": PRIMARY_LIGHT, "icon": "📝"},
    "Blog SistemaImpulsa": {"color": PRIMARY,   "bg": PRIMARY_LIGHT, "icon": "📝"},
    "Blog ImpulsaSuite":   {"color": PRIMARY,   "bg": PRIMARY_LIGHT, "icon": "📝"},
    "Blog CRMPeru":        {"color": PRIMARY,   "bg": PRIMARY_LIGHT, "icon": "📝"},
    "Blog Colombia":       {"color": PRIMARY,   "bg": PRIMARY_LIGHT, "icon": "📝"},
    "Email":               {"color": "#d98909", "bg": "#fef3dc", "icon": "✉"},
    "Facebook":            {"color": "#1877f2", "bg": "#e5effe", "icon": "📘"},
    "Twitter":             {"color": "#1da1f2", "bg": "#e5f5fe", "icon": "🐦"},
}

TIPO_META = {
    "Video Corto":   {"color": "#412f86", "bg": "#ece8f9"},
    "Video Largo":   {"color": "#412f86", "bg": "#ece8f9"},
    "Reel":          {"color": "#e1306c", "bg": "#fce8f1"},
    "Short":         {"color": "#cc0000", "bg": "#ffe5e5"},
    "Artículo":      {"color": PRIMARY,   "bg": PRIMARY_LIGHT},
    "Newsletter":    {"color": "#d98909", "bg": "#fef3dc"},
    "Mail Click":    {"color": "#3578aa", "bg": "#e5eef7"},
    "Carrusel":      {"color": "#e1306c", "bg": "#fce8f1"},
    "Post Imagen":   {"color": PRIMARY,   "bg": PRIMARY_LIGHT},
    "Story":         {"color": "#e1306c", "bg": "#fce8f1"},
    "Evento":        {"color": "#3578aa", "bg": "#e5eef7"},
}

ESTADO_META = {
    "Publicado":     {"color": "#1a7a4a", "bg": "#e6f5ed", "dot": "#1a7a4a"},
    "Programado":    {"color": "#412f86", "bg": "#ece8f9", "dot": "#412f86"},
    "En Producción": {"color": "#b06a00", "bg": "#fef3dc", "dot": "#d98909"},
    "Borrador":      {"color": "#646464", "bg": "#f3f3f3", "dot": "#999"},
    "Idea":          {"color": "#3578aa", "bg": "#e5eef7", "dot": "#3578aa"},
    "Cancelado":     {"color": "#c0392b", "bg": "#fde8e6", "dot": "#c0392b"},
}

DIAS_ES  = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
MESES_ES = ["", "ene", "feb", "mar", "abr", "may", "jun",
            "jul", "ago", "sep", "oct", "nov", "dic"]

# ── BADGE BUILDERS ───────────────────────────────────────────────────────────

def platform_badge(name):
    m = PLATFORM_META.get(name, {"color": TEXT2, "bg": "#f3f3f3", "icon": "🌐"})
    return (f'<span class="badge plat-badge" style="color:{m["color"]};background:{m["bg"]}">'
            f'{m["icon"]} {name}</span>')

def tipo_badge(name):
    if not name:
        return ""
    m = TIPO_META.get(name, {"color": TEXT2, "bg": "#f3f3f3"})
    return (f'<span class="badge tipo-badge" style="color:{m["color"]};background:{m["bg"]}">'
            f'{name}</span>')

def estado_badge(name):
    if not name:
        return ""
    m = ESTADO_META.get(name, {"color": TEXT2, "bg": "#f3f3f3", "dot": TEXT2})
    return (f'<span class="estado-badge" style="color:{m["color"]};background:{m["bg"]}">'
            f'<span class="dot" style="background:{m["dot"]}"></span>{name}</span>')

# ── CARD ─────────────────────────────────────────────────────────────────────

def build_card(item):
    plat_html  = "".join(platform_badge(p) for p in item["plataformas"])
    link_open  = f'<a href="{item["link"]}" target="_blank" rel="noopener" class="card-link">' if item["link"] else '<span class="card-link">'
    link_close = "</a>" if item["link"] else "</span>"
    hora_html  = f'<span class="meta-item">🕐 {item["hora"]} CLT</span>' if item["hora"] else ""
    resp_html  = f'<span class="meta-item resp">{item["responsable"]}</span>' if item["responsable"] else ""
    notas_html = f'<p class="card-notas">{item["notas"]}</p>' if item["notas"] else ""
    arrow      = ' <span class="arrow">↗</span>' if item["link"] else ""
    return f"""
    <div class="card" data-tipo="{item["tipo"]}" data-estado="{item["estado"]}"
         data-plataformas="{", ".join(item["plataformas"])}">
      <div class="card-top">
        {tipo_badge(item["tipo"])}
        {estado_badge(item["estado"])}
      </div>
      <div class="card-title">{link_open}{item["titulo"] or "(sin título)"}{arrow}{link_close}</div>
      <div class="card-meta">{hora_html}{resp_html}</div>
      <div class="card-plats">{plat_html}</div>
      {notas_html}
    </div>"""

# ── WEEK GRID ────────────────────────────────────────────────────────────────

def build_week_grid(items, week_start):
    today_s = datetime.now().strftime("%Y-%m-%d")
    days    = [week_start + timedelta(days=i) for i in range(7)]
    cols    = []
    total   = 0
    for d in days:
        ds         = d.strftime("%Y-%m-%d")
        day_items  = [x for x in items if x["fecha"] == ds]
        total     += len(day_items)
        is_today   = ds == today_s
        is_past    = ds < today_s
        day_num    = f"{DIAS_ES[d.weekday()]} {d.day}"
        cards_html = "".join(build_card(it) for it in day_items)
        empty_html = '<div class="empty-day">Sin contenido</div>' if not day_items else ""
        count_html = f'<span class="day-count">{len(day_items)}</span>' if day_items else ""
        cols.append(f"""
      <div class="day-col{"" if not is_today else " is-today"}{"" if not is_past else " is-past"}">
        <div class="day-header">
          <span class="day-name">{day_num}</span>
          {count_html}
        </div>
        <div class="day-body">{cards_html}{empty_html}</div>
      </div>""")
    return "".join(cols), total

# ── WEEKS INDEX ──────────────────────────────────────────────────────────────

def get_weeks(items):
    weeks = set()
    for it in items:
        try:
            d   = datetime.strptime(it["fecha"], "%Y-%m-%d")
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

# ── HTML BUILDER ─────────────────────────────────────────────────────────────

def build_html(items):
    weeks        = get_weeks(items)
    today_mon    = datetime.now() - timedelta(days=datetime.now().weekday())
    today_mon_s  = today_mon.strftime("%Y-%m-%d")
    current_idx  = weeks.index(today_mon_s) if today_mon_s in weeks else 0

    tabs_html  = []
    grids_html = []
    for i, w in enumerate(weeks):
        wmon  = datetime.strptime(w, "%Y-%m-%d")
        wlbl  = week_label(w)
        active = "active" if i == current_idx else ""
        grid_html, total = build_week_grid(items, wmon)
        badge = f'<span class="tab-count">{total}</span>' if total else ""
        tabs_html.append(
            f'<button class="tab {active}" onclick="showWeek({i})" id="tab-{i}">'
            f'{wlbl}{badge}</button>'
        )
        grids_html.append(
            f'<div class="week-grid {active}" id="grid-{i}">'
            f'<div class="day-row">{grid_html}</div></div>'
        )

    tabs_str  = "\n".join(tabs_html)
    grids_str = "\n".join(grids_html)

    # Stats
    this_week_items = [it for it in items
                       if abs((datetime.strptime(it["fecha"], "%Y-%m-%d") - today_mon).days) < 7]
    published  = sum(1 for it in this_week_items if it["estado"] == "Publicado")
    scheduled  = sum(1 for it in this_week_items if it["estado"] == "Programado")
    production = sum(1 for it in this_week_items if it["estado"] == "En Producción")
    total_week = len(this_week_items)
    total_all  = len(items)
    generated  = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Filter buttons for plataforma
    all_plats = sorted({p for it in items for p in it["plataformas"]})
    plat_btns = '\n'.join(
        f'<button class="filter-btn" onclick="filterBy(\'plataforma\',\'{p}\',this)">'
        f'{PLATFORM_META.get(p, {}).get("icon","🌐")} {p}</button>'
        for p in all_plats
    )

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>IMPULSA · Content Panel</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@600;700&family=Roboto:wght@400;500&display=swap" rel="stylesheet">
<style>
/* ── RESET & BASE ── */
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: 'Roboto', sans-serif;
  background: {BG};
  color: {TEXT};
  min-height: 100vh;
  font-size: 13px;
}}
a {{ text-decoration: none; color: inherit; }}

/* ── HEADER ── */
.header {{
  background: {WHITE};
  border-bottom: 1px solid {BORDER};
  padding: 0 36px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 2px 8px rgba(5,139,138,.06);
}}
.logo-area {{ display: flex; align-items: center; gap: 12px; }}
.logo-bar {{
  width: 4px; height: 32px;
  background: {PRIMARY};
  border-radius: 4px;
}}
.logo-text {{
  font-family: 'Poppins', sans-serif;
  font-size: 15px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: {TEXT};
}}
.logo-text span {{ color: {PRIMARY}; }}
.logo-sub {{
  font-family: 'Roboto', sans-serif;
  font-size: 11px;
  color: {TEXT3};
  font-weight: 500;
  letter-spacing: .5px;
}}
.header-right {{ display: flex; align-items: center; gap: 16px; }}
.updated-badge {{
  font-size: 11px;
  color: {TEXT3};
  background: {PRIMARY_LIGHT};
  border: 1px solid {BORDER};
  border-radius: 20px;
  padding: 4px 12px;
}}
.sheet-link {{
  font-size: 11px;
  font-weight: 500;
  color: {PRIMARY};
  background: {PRIMARY_LIGHT};
  border: 1px solid {PRIMARY};
  border-radius: {RADIUS_PILL};
  padding: 6px 16px;
  transition: all .15s;
}}
.sheet-link:hover {{ background: {PRIMARY}; color: {WHITE}; }}

/* ── STATS BAR ── */
.stats-bar {{
  background: {WHITE};
  border-bottom: 1px solid {BORDER};
  padding: 14px 36px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}}
.stat-card {{
  display: flex;
  align-items: center;
  gap: 10px;
  background: {BG};
  border: 1px solid {BORDER};
  border-radius: {RADIUS_CARD};
  padding: 10px 20px;
  min-width: 130px;
}}
.stat-icon {{
  width: 36px; height: 36px;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}}
.stat-info {{ display: flex; flex-direction: column; }}
.stat-num {{
  font-family: 'Poppins', sans-serif;
  font-size: 20px;
  font-weight: 700;
  line-height: 1;
  color: {TEXT};
}}
.stat-lbl {{
  font-size: 11px;
  color: {TEXT3};
  margin-top: 2px;
  font-weight: 500;
}}

/* ── TABS ── */
.tabs-wrap {{
  background: {WHITE};
  border-bottom: 3px solid {BORDER};
  padding: 0 36px;
  display: flex;
  gap: 4px;
  overflow-x: auto;
}}
.tab {{
  font-family: 'Roboto', sans-serif;
  font-size: 12px;
  font-weight: 500;
  color: {TEXT2};
  background: transparent;
  border: none;
  padding: 14px 18px 11px;
  cursor: pointer;
  white-space: nowrap;
  border-bottom: 3px solid transparent;
  margin-bottom: -3px;
  transition: all .15s;
  display: flex;
  align-items: center;
  gap: 6px;
}}
.tab:hover {{ color: {PRIMARY}; }}
.tab.active {{
  color: {PRIMARY};
  font-weight: 700;
  border-bottom-color: {PRIMARY};
}}
.tab-count {{
  background: {PRIMARY_LIGHT};
  color: {PRIMARY};
  border-radius: 10px;
  font-size: 10px;
  font-weight: 700;
  padding: 1px 7px;
  min-width: 20px;
  text-align: center;
}}
.tab.active .tab-count {{ background: {PRIMARY}; color: {WHITE}; }}

/* ── FILTERS ── */
.filters-wrap {{
  background: {WHITE};
  border-bottom: 1px solid {BORDER};
  padding: 10px 36px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}}
.filter-label {{
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .8px;
  color: {TEXT3};
  margin-right: 4px;
}}
.filter-btn {{
  font-family: 'Roboto', sans-serif;
  font-size: 11px;
  font-weight: 500;
  padding: 5px 14px;
  border-radius: {RADIUS_PILL};
  background: {BG};
  border: 1px solid {BORDER};
  color: {TEXT2};
  cursor: pointer;
  transition: all .15s;
}}
.filter-btn:hover {{ border-color: {PRIMARY}; color: {PRIMARY}; }}
.filter-btn.active {{
  background: {PRIMARY};
  border-color: {PRIMARY};
  color: {WHITE};
  font-weight: 700;
}}
.filter-divider {{
  width: 1px; height: 20px;
  background: {BORDER};
  margin: 0 4px;
}}

/* ── WEEK GRID ── */
.week-grid {{ display: none; padding: 24px 36px; }}
.week-grid.active {{ display: block; }}
.day-row {{
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 12px;
  min-height: 420px;
}}

/* ── DAY COLUMN ── */
.day-col {{
  background: {WHITE};
  border: 1px solid {BORDER};
  border-radius: {RADIUS_CARD};
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: {SHADOW};
  transition: box-shadow .2s;
}}
.day-col:hover {{ box-shadow: {SHADOW_HOVER}; }}
.day-col.is-today {{
  border-color: {PRIMARY};
  box-shadow: 0 0 0 2px {PRIMARY_LIGHT}, {SHADOW};
}}
.day-col.is-past {{ opacity: .85; }}

.day-header {{
  padding: 10px 12px 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: {PRIMARY_LIGHT};
  border-bottom: 1px solid {BORDER};
}}
.is-today .day-header {{
  background: {PRIMARY};
}}
.day-name {{
  font-family: 'Poppins', sans-serif;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .6px;
  color: {TEXT2};
}}
.is-today .day-name {{ color: {WHITE}; }}
.day-count {{
  background: {PRIMARY};
  color: {WHITE};
  border-radius: 10px;
  font-size: 10px;
  font-weight: 700;
  padding: 1px 7px;
}}
.is-today .day-count {{
  background: {WHITE};
  color: {PRIMARY};
}}

.day-body {{
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px;
  flex: 1;
}}
.empty-day {{
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: {TEXT3};
  font-size: 12px;
  padding: 24px 0;
  border: 1.5px dashed {BORDER};
  border-radius: 10px;
  margin: 4px 0;
}}

/* ── CARD ── */
.card {{
  background: {BG};
  border: 1px solid {BORDER};
  border-radius: 12px;
  padding: 10px 11px;
  transition: box-shadow .15s, transform .1s;
  cursor: default;
}}
.card:hover {{
  box-shadow: {SHADOW_HOVER};
  transform: translateY(-1px);
  background: {WHITE};
  border-color: {PRIMARY}44;
}}
.card-top {{
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 7px;
}}
.card-title {{
  font-size: 12px;
  font-weight: 500;
  color: {TEXT};
  line-height: 1.45;
  margin-bottom: 7px;
}}
.card-link {{ color: {TEXT}; }}
.card-link:hover {{ color: {PRIMARY}; }}
.arrow {{
  font-size: 11px;
  color: {PRIMARY};
  margin-left: 2px;
}}
.card-meta {{
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-bottom: 7px;
}}
.meta-item {{
  font-size: 10px;
  color: {TEXT3};
  background: {WHITE};
  border: 1px solid {BORDER};
  border-radius: 20px;
  padding: 1px 8px;
}}
.resp {{ color: {TEXT2}; font-weight: 500; }}
.card-plats {{ display: flex; flex-wrap: wrap; gap: 4px; }}
.card-notas {{
  margin-top: 7px;
  font-size: 10px;
  color: {TEXT3};
  font-style: italic;
  line-height: 1.4;
  padding-top: 6px;
  border-top: 1px solid {BORDER};
}}

/* ── BADGES ── */
.badge {{
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 10px;
  font-weight: 600;
  border-radius: {RADIUS_BADGE};
  padding: 3px 9px;
  white-space: nowrap;
  font-family: 'Roboto', sans-serif;
}}
.estado-badge {{
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 10px;
  font-weight: 700;
  border-radius: {RADIUS_BADGE};
  padding: 3px 9px;
  font-family: 'Roboto', sans-serif;
}}
.dot {{
  width: 6px; height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}}

/* ── FOOTER ── */
.footer {{
  background: {PRIMARY};
  color: {WHITE};
  text-align: center;
  padding: 18px 36px;
  font-size: 11px;
  opacity: .9;
}}
.footer a {{ color: #a9d7d7; }}
.footer a:hover {{ color: {WHITE}; }}

/* ── RESPONSIVE ── */
@media(max-width:1100px) {{
  .day-row {{ grid-template-columns: repeat(4, 1fr); }}
}}
@media(max-width:700px) {{
  .day-row {{ grid-template-columns: repeat(2, 1fr); }}
  .header, .stats-bar, .tabs-wrap, .filters-wrap, .week-grid {{ padding-left: 16px; padding-right: 16px; }}
}}
@media(max-width:400px) {{
  .day-row {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>

<!-- HEADER -->
<header class="header">
  <div class="logo-area">
    <div class="logo-bar"></div>
    <div>
      <div class="logo-text">IMPULSA<span> Suite</span></div>
      <div class="logo-sub">Content Panel</div>
    </div>
  </div>
  <div class="header-right">
    <span class="updated-badge">Actualizado: {generated}</span>
    <a href="https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#gid=1371647617"
       target="_blank" class="sheet-link">📋 Abrir Sheet</a>
  </div>
</header>

<!-- STATS BAR -->
<div class="stats-bar">
  <div class="stat-card">
    <div class="stat-icon" style="background:{PRIMARY_LIGHT};color:{PRIMARY}">📅</div>
    <div class="stat-info">
      <span class="stat-num">{total_week}</span>
      <span class="stat-lbl">Esta semana</span>
    </div>
  </div>
  <div class="stat-card">
    <div class="stat-icon" style="background:#e6f5ed;color:#1a7a4a">✓</div>
    <div class="stat-info">
      <span class="stat-num" style="color:#1a7a4a">{published}</span>
      <span class="stat-lbl">Publicados</span>
    </div>
  </div>
  <div class="stat-card">
    <div class="stat-icon" style="background:#ece8f9;color:#412f86">⏱</div>
    <div class="stat-info">
      <span class="stat-num" style="color:#412f86">{scheduled}</span>
      <span class="stat-lbl">Programados</span>
    </div>
  </div>
  <div class="stat-card">
    <div class="stat-icon" style="background:#fef3dc;color:#b06a00">⚙</div>
    <div class="stat-info">
      <span class="stat-num" style="color:#b06a00">{production}</span>
      <span class="stat-lbl">En producción</span>
    </div>
  </div>
  <div class="stat-card">
    <div class="stat-icon" style="background:#f3f3f3;color:{TEXT2}">≡</div>
    <div class="stat-info">
      <span class="stat-num">{total_all}</span>
      <span class="stat-lbl">Total en grilla</span>
    </div>
  </div>
</div>

<!-- TABS -->
<div class="tabs-wrap">
{tabs_str}
</div>

<!-- FILTERS -->
<div class="filters-wrap">
  <span class="filter-label">Plataforma:</span>
  <button class="filter-btn active" id="plat-all" onclick="filterBy('plataforma','all',this)">Todas</button>
  {plat_btns}
  <div class="filter-divider"></div>
  <span class="filter-label">Estado:</span>
  <button class="filter-btn active" id="estado-all" onclick="filterBy('estado','all',this)">Todos</button>
  <button class="filter-btn" onclick="filterBy('estado','Publicado',this)">✓ Publicado</button>
  <button class="filter-btn" onclick="filterBy('estado','Programado',this)">⏱ Programado</button>
  <button class="filter-btn" onclick="filterBy('estado','En Producción',this)">⚙ En Producción</button>
  <button class="filter-btn" onclick="filterBy('estado','Borrador',this)">◻ Borrador</button>
  <button class="filter-btn" onclick="filterBy('estado','Idea',this)">💡 Idea</button>
</div>

<!-- WEEK GRIDS -->
{grids_str}

<!-- FOOTER -->
<footer class="footer">
  IMPULSA Suite · Content Panel ·
  <a href="https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#gid=1371647617" target="_blank">
    Editar en Google Sheets
  </a>
</footer>

<script>
let filters = {{plataforma: 'all', estado: 'all'}};

function showWeek(i) {{
  document.querySelectorAll('.week-grid').forEach(g => g.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById('grid-' + i).classList.add('active');
  document.getElementById('tab-' + i).classList.add('active');
}}

function filterBy(type, value, btn) {{
  filters[type] = value;
  document.querySelectorAll('.filter-btn').forEach(b => {{
    const oc = b.getAttribute('onclick') || '';
    if (oc.includes("'" + type + "'")) b.classList.remove('active');
  }});
  btn.classList.add('active');
  applyFilters();
}}

function applyFilters() {{
  document.querySelectorAll('.card').forEach(card => {{
    const estado = card.dataset.estado || '';
    const plats  = (card.dataset.plataformas || '').toLowerCase();
    let show = true;
    if (filters.plataforma !== 'all')
      show = show && plats.includes(filters.plataforma.toLowerCase());
    if (filters.estado !== 'all')
      show = show && estado === filters.estado;
    card.style.display = show ? '' : 'none';
  }});
}}
</script>
</body>
</html>"""

# ── MAIN ─────────────────────────────────────────────────────────────────────

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
