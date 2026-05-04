#!/usr/bin/env python3
"""IMPULSA Marketing Content Hub — Generator v7"""

import json, re, calendar as cal_mod
from datetime import datetime, timedelta
from collections import defaultdict
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import gspread

SHEET_ID = "1tp1MRjJU6g6vF5VD78k-xbV6tcSM5XVZb_FQe9HIdIs"
SA_KEY   = "/Users/sebastian/.config/claude-keys/google-sheets-sa.json"
TAB_NAME = "Calendario Editorial"
OUT_FILE = "index.html"

# ── READ & NORMALIZE ──────────────────────────────────────────────────────────

def read_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds  = Credentials.from_service_account_file(SA_KEY, scopes=scopes)
    gc     = gspread.authorize(creds)
    return gc.open_by_key(SHEET_ID).worksheet(TAB_NAME).get_all_records()

def parse_fecha(s):
    try:
        return datetime.strptime(s.strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
    except:
        return ""

# ── CROSS-REFERENCE LOADING ───────────────────────────────────────────────────

def _norm(s):
    return re.sub(r"[^a-záéíóúüñ0-9 ]", "", s.lower().strip())

def _words(s):
    return {w for w in _norm(s).split() if len(w) > 4}

def _sheet_headers(service, sheet_id, tab_range):
    """Return a dict of HEADER_NAME → col_index for the first row of a tab."""
    res = service.spreadsheets().get(
        spreadsheetId=sheet_id, ranges=[tab_range], includeGridData=True
    ).execute()
    row0 = res["sheets"][0]["data"][0].get("rowData", [{}])[0].get("values", [])
    headers = {}
    for i, c in enumerate(row0):
        h = c.get("formattedValue", "").strip()
        if h:
            headers[h.upper()] = i
    return headers, res

def load_references(service, sheet_id):
    """Load cross-reference URLs from Newsletters and Articulos tabs.
    Returns {newsletters:{}, articulos:{}} — type-separated.
    """
    refs = {"newsletters": {}, "articulos": {}}

    # ── Newsletters tab ──────────────────────────────────────────────────
    try:
        headers, res2 = _sheet_headers(service, sheet_id, "Newsletters!A:J")
        tema_col = headers.get("TEMA", 4)
        for row in res2["sheets"][0]["data"][0].get("rowData", [])[1:]:
            cells = row.get("values", [])
            def cv(idx): return cells[idx].get("formattedValue", "") if idx < len(cells) else ""
            def lv(idx): return cells[idx].get("hyperlink", "")      if idx < len(cells) else ""
            tema = cv(tema_col)
            if not tema: continue
            folder_url = lv(0)  # N° column hyperlink
            if tema and folder_url:
                refs["newsletters"][_norm(tema)] = {"folder_url": folder_url}
    except Exception as e:
        print(f"   [warn] Newsletters tab: {e}")

    # ── Articulos tab ────────────────────────────────────────────────────
    try:
        headers, res3 = _sheet_headers(service, sheet_id, "Articulos!A:K")
        tema_col = headers.get("TEMA", 5)
        for row in res3["sheets"][0]["data"][0].get("rowData", [])[1:]:
            cells = row.get("values", [])
            def cv(idx): return cells[idx].get("formattedValue", "") if idx < len(cells) else ""
            def lv(idx): return cells[idx].get("hyperlink", "")      if idx < len(cells) else ""
            tema = cv(tema_col)
            if not tema: continue
            folder_url = lv(0)
            if tema and folder_url:
                refs["articulos"][_norm(tema)] = {"folder_url": folder_url}
    except Exception as e:
        print(f"   [warn] Articulos tab: {e}")

    print(f"   ↳ Referencias: {len(refs['newsletters'])} newsletters · {len(refs['articulos'])} artículos")
    return refs

def find_ref(titulo, sub_refs):
    """Fuzzy-match a calendar title against a type-specific sub-dict."""
    if not sub_refs or not titulo:
        return None
    key = _norm(titulo)
    if key in sub_refs:
        return sub_refs[key]
    words_a = _words(titulo)
    best, best_n = None, 0
    for rkey, rval in sub_refs.items():
        overlap = len(words_a & _words(rkey))
        if overlap >= 3 and overlap > best_n:
            best_n, best = overlap, rval
    return best

def get_card_url(item, ref_data):
    """Return the URL to open when the card is clicked."""
    cat  = item.get("categoria", "")
    link = item.get("link", "")
    if link and link.startswith("http"):
        return link
    if cat == "email":
        matched = find_ref(item.get("titulo", ""), ref_data.get("newsletters", {}))
        if matched and matched.get("folder_url"):
            return matched["folder_url"]
    elif cat == "articulo":
        matched = find_ref(item.get("titulo", ""), ref_data.get("articulos", {}))
        if matched and matched.get("folder_url"):
            return matched["folder_url"]
    return ""

# Maps granular internal states → macro state (for top-level filtering)
ESTADO_INTERNO_MAP = {
    "Por redactar":  "En Producción",
    "Por grabar":    "En Producción",
    "Por editar":    "En Producción",
    "Por diseñar":   "En Producción",
    "Por publicar":  "Programado",
    "Por presentar": "Programado",
    "Realizado":     "Publicado",
    "Publicado":     "Publicado",
    "Programado":    "Programado",
    "En Producción": "En Producción",
    "Borrador":      "En Producción",
    "Idea":          "Idea",
    "Cancelado":     "Cancelado",
}

def normalize(rows, ref_data=None):
    if ref_data is None:
        ref_data = {}
    items = []
    for r in rows:
        fecha = parse_fecha(r.get("FECHA", ""))
        if not fecha:
            continue
        estado = r.get("ESTADO", "")
        item = {
            "fecha":        fecha,
            "hora":         r.get("HORA (CLT)", ""),
            "tipo":         r.get("TIPO", ""),
            "categoria":    TIPO_TO_CAT.get(r.get("TIPO", ""), "otro"),
            "plataformas":  [p.strip() for p in r.get("PLATAFORMAS", "").split("·") if p.strip()],
            "titulo":       r.get("TITULO / DESCRIPCIÓN", ""),
            "estado":       estado,
            "macro_estado": ESTADO_INTERNO_MAP.get(estado, estado),
            "link":         r.get("LINK", ""),
            "responsable":  r.get("RESPONSABLE", ""),
            "ref":          r.get("REF", ""),
            "notas":        r.get("NOTAS", ""),
            "hashtags":     r.get("HASHTAGS", ""),
            "descripcion":  r.get("DESCRIPCION", ""),
            "url_embed":    r.get("URL_EMBED", ""),
        }
        item["card_url"] = get_card_url(item, ref_data)
        items.append(item)
    items.sort(key=lambda x: (x["fecha"], x["hora"] or "23:59"))
    for i, item in enumerate(items):
        item["cid"] = f"c{i}"
    return items

# ── BRAND TOKENS ──────────────────────────────────────────────────────────────

PRIMARY   = "#058b8a"
PRIMARY_L = "#e6f7f7"
PRIMARY_M = "#dcf5f0"
BG        = "#f4fafa"
WHITE     = "#ffffff"
BORDER    = "#d4eeee"
BORDER2   = "#eaf5f5"
TEXT      = "#4d4d4d"
TEXT2     = "#646464"
TEXT3     = "#999999"
SH        = "0 2px 12px rgba(5,139,138,.08)"
SH_H      = "0 6px 22px rgba(5,139,138,.16)"

TIPO_TO_CAT = {
    "Video Corto": "video", "Video Largo": "video",
    "Reel": "video",        "Short": "video",
    "Artículo": "articulo",
    "Newsletter": "email",  "Mail Click": "email",
    "Carrusel": "publicacion", "Post Imagen": "publicacion", "Story": "publicacion",
    "Evento": "evento",
}

TIPO_META = {
    "Video Corto":   {"c": "#412f86", "bg": "#ece8f9"},
    "Video Largo":   {"c": "#412f86", "bg": "#ece8f9"},
    "Reel":          {"c": "#e1306c", "bg": "#fce8f1"},
    "Short":         {"c": "#cc0000", "bg": "#ffe5e5"},
    "Artículo":      {"c": PRIMARY,   "bg": PRIMARY_L},
    "Newsletter":    {"c": "#d98909", "bg": "#fef3dc"},
    "Mail Click":    {"c": "#3578aa", "bg": "#e5eef7"},
    "Carrusel":      {"c": "#e1306c", "bg": "#fce8f1"},
    "Post Imagen":   {"c": PRIMARY,   "bg": PRIMARY_L},
    "Story":         {"c": "#e1306c", "bg": "#fce8f1"},
    "Evento":        {"c": "#3578aa", "bg": "#e5eef7"},
}

PLAT_META = {
    "Instagram":           {"c": "#E1306C", "bg": "linear-gradient(135deg,#f09433 0%,#e6683c 25%,#dc2743 50%,#cc2366 75%,#bc1888 100%)", "icon": "ig"},
    "TikTok":              {"c": "#000000", "bg": "#000000",  "icon": "tt"},
    "YouTube":             {"c": "#FF0000", "bg": "#FF0000",  "icon": "yt"},
    "YouTube Shorts":      {"c": "#FF0000", "bg": "#FF0000",  "icon": "yt"},
    "LinkedIn":            {"c": "#0A66C2", "bg": "#0A66C2",  "icon": "li"},
    "Facebook":            {"c": "#1877F2", "bg": "#1877F2",  "icon": "fb"},
    "Twitter":             {"c": "#000000", "bg": "#14171A",  "icon": "tw"},
    "Blog":                {"c": PRIMARY,   "bg": PRIMARY,    "icon": "blog"},
    "Blog SistemaImpulsa": {"c": PRIMARY,   "bg": PRIMARY,    "icon": "blog"},
    "Blog ImpulsaSuite":   {"c": PRIMARY,   "bg": PRIMARY,    "icon": "blog"},
    "Blog CRMPeru":        {"c": PRIMARY,   "bg": PRIMARY,    "icon": "blog"},
    "Blog Colombia":       {"c": PRIMARY,   "bg": PRIMARY,    "icon": "blog"},
    "Email":               {"c": "#D98909", "bg": "#D98909",  "icon": "email"},
}

ESTADO_META = {
    # Macro states
    "Publicado":     {"c": "#1a7a4a", "bg": "#e6f5ed", "d": "#1a7a4a"},
    "Programado":    {"c": "#412f86", "bg": "#ece8f9", "d": "#412f86"},
    "En Producción": {"c": "#b06a00", "bg": "#fef3dc", "d": "#d98909"},
    "Borrador":      {"c": "#646464", "bg": "#f3f3f3", "d": "#999"},
    "Idea":          {"c": "#3578aa", "bg": "#e5eef7", "d": "#3578aa"},
    "Cancelado":     {"c": "#c0392b", "bg": "#fde8e6", "d": "#c0392b"},
    # Internal granular states
    "Por redactar":  {"c": "#b06a00", "bg": "#fef3dc", "d": "#d98909"},
    "Por grabar":    {"c": "#7b3fa0", "bg": "#f0e6f7", "d": "#9b59b6"},
    "Por editar":    {"c": "#b06a00", "bg": "#fff3e0", "d": "#e67e22"},
    "Por diseñar":   {"c": "#c0392b", "bg": "#fde8e6", "d": "#e74c3c"},
    "Por publicar":  {"c": "#412f86", "bg": "#ece8f9", "d": "#412f86"},
    "Por presentar": {"c": "#412f86", "bg": "#ece8f9", "d": "#412f86"},
    "Realizado":     {"c": "#1a7a4a", "bg": "#e6f5ed", "d": "#1a7a4a"},
}

DIAS_ES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
DIAS_F  = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
MESES_F = ["","Enero","Febrero","Marzo","Abril","Mayo","Junio",
           "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
MESES_S = ["","ene","feb","mar","abr","may","jun",
           "jul","ago","sep","oct","nov","dic"]

# ── SVG SPRITE ────────────────────────────────────────────────────────────────

SVG_ICONS = {
    "ig":   '<path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>',
    "tt":   '<path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-2.88 2.5 2.89 2.89 0 0 1-2.89-2.89 2.89 2.89 0 0 1 2.89-2.89c.28 0 .54.04.79.1V9.01a6.27 6.27 0 0 0-.79-.05 6.34 6.34 0 0 0-6.34 6.34 6.34 6.34 0 0 0 6.34 6.34 6.34 6.34 0 0 0 6.33-6.34V9.05a8.16 8.16 0 0 0 4.78 1.52V7.14a4.85 4.85 0 0 1-1.01-.45z"/>',
    "yt":   '<path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>',
    "li":   '<path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>',
    "fb":   '<path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>',
    "tw":   '<path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.748l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>',
    "blog": '<path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>',
    "email":'<path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/>',
    "globe":'<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>',
}

def svg_sprite():
    parts = ['<svg style="display:none" xmlns="http://www.w3.org/2000/svg">']
    for k, v in SVG_ICONS.items():
        parts.append(f'<symbol id="icon-{k}" viewBox="0 0 24 24">{v}</symbol>')
    parts.append('</svg>')
    return ''.join(parts)

def plat_icon_svg(icon, size=14):
    return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="white"><use href="#icon-{icon}"/></svg>'

# ── BADGES ───────────────────────────────────────────────────────────────────

def plat_dot(name, macro_estado="", link=""):
    m   = PLAT_META.get(name, {"c": TEXT2, "bg": "#888888", "icon": "globe"})
    bg  = m.get("bg", "#888888")
    ico = m.get("icon", "globe")
    svg = plat_icon_svg(ico)
    if macro_estado == "Publicado" and link:
        return (f'<a href="{link}" target="_blank" rel="noopener" class="pdot pdot-link" title="{name} ↗" '
                f'onclick="event.stopPropagation()" style="background:{bg}">{svg}</a>')
    return f'<span class="pdot" title="{name}" style="background:{bg}">{svg}</span>'

def tipo_badge(name):
    if not name: return ""
    m = TIPO_META.get(name, {"c": TEXT2, "bg": "#f3f3f3"})
    return f'<span class="badge tipo-b" style="color:{m["c"]};background:{m["bg"]}">{name}</span>'

def estado_badge(name):
    if not name: return ""
    m = ESTADO_META.get(name, {"c": TEXT2, "bg": "#f3f3f3", "d": TEXT2})
    return (f'<span class="estado-b" style="color:{m["c"]};background:{m["bg"]}">'
            f'<i style="background:{m["d"]}"></i>{name}</span>')

# ── WEEK CARD ────────────────────────────────────────────────────────────────

def build_card(item):
    cat   = item["categoria"]
    plats = ", ".join(item["plataformas"])
    macro = item["macro_estado"]
    pdots = "".join(plat_dot(p, macro, item["link"]) for p in item["plataformas"])
    hora  = f'<span class="mi">🕐 {item["hora"]} CLT</span>' if item["hora"] else ""
    resp  = f'<span class="mi resp">{item["responsable"]}</span>' if item["responsable"] else ""
    url   = item.get("card_url", "")
    click = f'onclick="window.open(\'{url}\',\'_blank\')" style="cursor:pointer" title="Abrir contenido"' if url else ""
    return (f'<div class="card" data-cat="{cat}" data-plats="{plats}" data-estado="{macro}" {click}>'
            f'<div class="ct">{tipo_badge(item["tipo"])}{estado_badge(item["estado"])}</div>'
            f'<div class="ctitle">{item["titulo"] or "(sin título)"}</div>'
            f'<div class="cmeta">{hora}{resp}</div>'
            f'<div class="cplats">{pdots}</div></div>')

# ── MONTH MINI CARD ───────────────────────────────────────────────────────────

def build_mini(item):
    cid   = item.get("cid", "")
    cat   = item["categoria"]
    plats = ", ".join(item["plataformas"])
    m     = TIPO_META.get(item["tipo"], {"c": TEXT2, "bg": "#f3f3f3"})
    macro = item["macro_estado"]
    title = (item["titulo"][:34] + "…") if len(item["titulo"]) > 34 else item["titulo"]
    hora  = f' · {item["hora"]}' if item["hora"] else ""
    pdots = "".join(
        f'<span class="mpdot" title="{p}" style="background:{PLAT_META.get(p,{"bg":"#888"})["bg"]}">'
        f'{plat_icon_svg(PLAT_META.get(p,{"icon":"globe"})["icon"], 9)}</span>'
        for p in item["plataformas"]
    )
    return (f'<div class="mini" data-cat="{cat}" data-plats="{plats}" data-estado="{macro}">'
            f'<div class="mchip" style="color:{m["c"]};background:{m["bg"]};border-left:3px solid {m["c"]}">'
            f'<span class="mctxt">{title}{hora}</span>'
            f'<span class="mcplats">{pdots}</span>'
            f'</div></div>')

# ── WEEK GRID ────────────────────────────────────────────────────────────────

def build_week_grid(items, week_start, grid_id):
    today_s = datetime.now().strftime("%Y-%m-%d")
    # Exclude Ideas from main grid
    visible = [x for x in items if x["macro_estado"] != "Idea"]
    cols = []
    for i in range(7):
        d  = week_start + timedelta(days=i)
        ds = d.strftime("%Y-%m-%d")
        di = [x for x in visible if x["fecha"] == ds]
        is_today = ds == today_s
        is_past  = ds < today_s
        cnt_h  = f'<span class="dcnt">{len(di)}</span>' if di else ""
        cards  = "".join(build_card(it) for it in di)
        empty  = '<div class="eday">Sin contenido</div>' if not di else ""
        cls    = " today" if is_today else (" past" if is_past else "")
        cols.append(
            f'<div class="dcol{cls}">'
            f'<div class="dhdr" onclick="openDay(\'{ds}\')" title="Ver {DIAS_ES[d.weekday()]} {d.day}">'
            f'<span class="dname">{DIAS_ES[d.weekday()]} {d.day}</span>{cnt_h}'
            f'<span class="dopen">+</span></div>'
            f'<div class="dbody">{cards}{empty}</div></div>'
        )
    return (f'<div class="week-grid" id="{grid_id}" style="display:none">'
            f'<div class="drow">{"".join(cols)}</div></div>')

def week_label(mon_str):
    mon = datetime.strptime(mon_str, "%Y-%m-%d")
    sun = mon + timedelta(days=6)
    iso = mon.isocalendar()[1]
    return f"W{iso} · {mon.day} {MESES_S[mon.month]} — {sun.day} {MESES_S[sun.month]} {sun.year}"

# ── MONTH GRID ───────────────────────────────────────────────────────────────

def build_month_grid(items, year, month, grid_id):
    today_s  = datetime.now().strftime("%Y-%m-%d")
    visible  = [x for x in items if x["macro_estado"] != "Idea"]
    first    = datetime(year, month, 1)
    last_day = cal_mod.monthrange(year, month)[1]
    last     = datetime(year, month, last_day)
    start    = first - timedelta(days=first.weekday())
    end      = last  + timedelta(days=(6 - last.weekday()))
    hdrs  = "".join(f'<div class="mhdr">{d}</div>' for d in DIAS_ES)
    cells = []
    cur   = start
    while cur <= end:
        ds      = cur.strftime("%Y-%m-%d")
        di      = [x for x in visible if x["fecha"] == ds]
        in_mon  = cur.month == month
        is_today = ds == today_s
        minis   = "".join(build_mini(it) for it in di)
        dn      = (f'<div class="mdn today-dn">{cur.day}</div>' if is_today
                   else f'<div class="mdn">{cur.day}</div>')
        cls = (" out" if not in_mon else "") + (" mtoday" if is_today else "")
        cells.append(
            f'<div class="mcell{cls}" onclick="openDay(\'{ds}\')" title="Ver {cur.day}/{cur.month}">'
            f'{dn}<div class="mcitems">{minis}</div></div>'
        )
        cur += timedelta(days=1)
    return (f'<div class="month-grid" id="{grid_id}" style="display:none">'
            f'<div class="mhdr-row">{hdrs}</div>'
            f'<div class="mcells">{"".join(cells)}</div></div>')

# ── BUILD HTML ────────────────────────────────────────────────────────────────

def build_html(items):
    today     = datetime.now()
    today_s   = today.strftime("%Y-%m-%d")
    generated = today.strftime("%d/%m/%Y %H:%M")

    # ── Weeks ──
    weeks_set = set()
    for it in items:
        if it["macro_estado"] == "Idea": continue
        d   = datetime.strptime(it["fecha"], "%Y-%m-%d")
        mon = d - timedelta(days=d.weekday())
        weeks_set.add(mon.strftime("%Y-%m-%d"))
    cur_mon = today - timedelta(days=today.weekday())
    for offset in range(-2, 5):
        w = cur_mon + timedelta(weeks=offset)
        weeks_set.add(w.strftime("%Y-%m-%d"))
    weeks = sorted(weeks_set)
    cur_wi = next(i for i, w in enumerate(weeks) if w == cur_mon.strftime("%Y-%m-%d"))

    week_grids  = [build_week_grid(items, datetime.strptime(w, "%Y-%m-%d"), f"wk-{i}")
                   for i, w in enumerate(weeks)]
    week_labels = [week_label(w) for w in weeks]
    week_ids    = [f"wk-{i}" for i in range(len(weeks))]

    # ── Months ──
    months_set = set()
    for it in items:
        if it["macro_estado"] == "Idea": continue
        d = datetime.strptime(it["fecha"], "%Y-%m-%d")
        months_set.add((d.year, d.month))
    for offset in range(-1, 3):
        m = today.month + offset
        y = today.year + (m - 1) // 12
        m = ((m - 1) % 12) + 1
        months_set.add((y, m))
    months = sorted(months_set)
    cur_mi = next(i for i, (y, m) in enumerate(months)
                  if y == today.year and m == today.month)

    month_grids  = [build_month_grid(items, y, m, f"mo-{i}")
                    for i, (y, m) in enumerate(months)]
    month_labels = [f"{MESES_F[m]} {y}" for y, m in months]
    month_ids    = [f"mo-{i}" for i in range(len(months))]

    # ── DAY_CARDS (excludes Ideas) ──
    day_map = defaultdict(list)
    for it in items:
        if it["macro_estado"] != "Idea":
            day_map[it["fecha"]].append(build_card(it))
    day_cards_json = {k: "".join(v) for k, v in day_map.items()}

    # ── IDEAS list ──
    ideas = [it for it in items if it["macro_estado"] == "Idea"]
    ideas_json = [{"cid": it["cid"], "titulo": it["titulo"], "tipo": it["tipo"],
                   "fecha": it["fecha"], "descripcion": it["descripcion"],
                   "ref": it["ref"], "responsable": it["responsable"]} for it in ideas]

    # ── Stats (current week, excluding Ideas) ──
    wk_items   = [it for it in items
                  if it["macro_estado"] != "Idea" and
                  abs((datetime.strptime(it["fecha"], "%Y-%m-%d") - cur_mon).days) < 7]
    published  = sum(1 for it in wk_items if it["macro_estado"] == "Publicado")
    scheduled  = sum(1 for it in wk_items if it["macro_estado"] == "Programado")
    production = sum(1 for it in wk_items if it["macro_estado"] == "En Producción")
    ideas_count = len(ideas)

    # ── Platform sub-filter options ──
    visible_items = [it for it in items if it["macro_estado"] != "Idea"]
    video_plats = sorted({p for it in visible_items if it["categoria"] == "video" for p in it["plataformas"]})
    pub_plats   = sorted({p for it in visible_items if it["categoria"] == "publicacion" for p in it["plataformas"]})
    if not video_plats: video_plats = ["Instagram", "TikTok", "YouTube", "YouTube Shorts"]
    if not pub_plats:   pub_plats   = ["Instagram", "TikTok", "LinkedIn", "Facebook"]

    def pfbtn(p):
        m   = PLAT_META.get(p, {"bg": "#888", "icon": "globe"})
        dot = (f'<span style="display:inline-flex;align-items:center;justify-content:center;'
               f'width:16px;height:16px;border-radius:50%;background:{m["bg"]};flex-shrink:0">'
               f'{plat_icon_svg(m["icon"], 9)}</span>')
        return (f'<button class="filter-btn" data-fp onclick="filterPlat(\'{p}\',this)">'
                f'<span style="display:inline-flex;align-items:center;gap:5px">{dot}{p}</span></button>')

    vp_btns = "\n".join(pfbtn(p) for p in video_plats)
    pp_btns = "\n".join(pfbtn(p) for p in pub_plats)

    ideas_badge   = (f'<span class="ideas-count">{ideas_count}</span>' if ideas_count else "")

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>IMPULSA Suite · Marketing Content Hub</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@600;700&family=Roboto:wght@400;500&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Roboto',sans-serif;background:{BG};color:{TEXT};min-height:100vh;font-size:13px;display:flex;flex-direction:column}}
a{{text-decoration:none;color:inherit}}

/* HEADER */
.hdr{{background:{WHITE};border-bottom:1px solid {BORDER};padding:0 32px;display:flex;align-items:center;justify-content:space-between;height:60px;position:sticky;top:0;z-index:100;box-shadow:0 2px 6px rgba(5,139,138,.07)}}
.hdr-l{{display:flex;align-items:center;gap:12px}}
.logo-bar{{width:4px;height:30px;background:{PRIMARY};border-radius:3px;flex-shrink:0}}
.logo-txt{{font-family:'Poppins',sans-serif;font-size:14px;font-weight:700;text-transform:uppercase;letter-spacing:.8px}}
.logo-txt span{{color:{PRIMARY}}}
.logo-sub{{font-size:10px;color:{TEXT3};letter-spacing:.4px;margin-top:1px}}
.hdr-r{{display:flex;align-items:center;gap:10px}}
.upd{{font-size:11px;color:{TEXT3};background:{PRIMARY_L};border:1px solid {BORDER};border-radius:20px;padding:4px 12px}}
.sheet-btn{{font-size:11px;font-weight:500;color:{PRIMARY};background:{PRIMARY_L};border:1px solid {PRIMARY};border-radius:35px;padding:6px 16px;transition:all .15s;cursor:pointer;display:inline-block}}
.sheet-btn:hover{{background:{PRIMARY};color:{WHITE}}}

/* STATS */
.stats{{background:{WHITE};border-bottom:1px solid {BORDER};padding:12px 32px;display:flex;gap:8px;flex-wrap:wrap}}
.sc{{display:flex;align-items:center;gap:9px;background:{BG};border:1px solid {BORDER};border-radius:14px;padding:9px 18px;min-width:120px}}
.si{{width:34px;height:34px;border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:15px;flex-shrink:0}}
.sn{{font-family:'Poppins',sans-serif;font-size:19px;font-weight:700;line-height:1}}
.sl{{font-size:10px;color:{TEXT3};margin-top:2px;font-weight:500}}

/* CONTROLS */
.ctrl{{background:{WHITE};border-bottom:1px solid {BORDER};padding:10px 32px;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}}
.view-toggle{{display:flex;background:{BG};border:1px solid {BORDER};border-radius:35px;padding:3px;gap:2px}}
.vbtn{{font-family:'Roboto',sans-serif;font-size:12px;font-weight:500;padding:5px 18px;border-radius:35px;background:transparent;border:none;color:{TEXT2};cursor:pointer;transition:all .15s}}
.vbtn.active{{background:{PRIMARY};color:{WHITE};font-weight:700;box-shadow:0 2px 6px rgba(5,139,138,.3)}}
.ideas-btn{{display:inline-flex;align-items:center;gap:7px;font-family:'Roboto',sans-serif;font-size:12px;font-weight:600;padding:6px 16px;border-radius:35px;background:#fef3dc;border:1.5px solid #f0d080;color:#b06a00;cursor:pointer;transition:all .15s;position:relative}}
.ideas-btn:hover{{background:#f5e5a0;border-color:#d4a820}}
.ideas-count{{background:#d98909;color:{WHITE};border-radius:20px;font-size:10px;font-weight:700;padding:1px 7px;line-height:1.4}}
.period-nav{{display:flex;align-items:center;gap:10px}}
.nav-arr{{background:{PRIMARY_L};border:1px solid {BORDER};color:{PRIMARY};border-radius:50%;width:32px;height:32px;display:flex;align-items:center;justify-content:center;cursor:pointer;font-size:14px;font-weight:700;transition:all .15s;user-select:none;flex-shrink:0}}
.nav-arr:hover{{background:{PRIMARY};color:{WHITE}}}
.plbl{{font-family:'Poppins',sans-serif;font-size:13px;font-weight:700;color:{TEXT};min-width:220px;text-align:center}}

/* FILTERS */
.frow{{background:{WHITE};border-bottom:1px solid {BORDER};padding:9px 32px;display:flex;align-items:center;gap:7px;flex-wrap:wrap}}
.flbl{{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.7px;color:{TEXT3};white-space:nowrap}}
.filter-btn{{font-family:'Roboto',sans-serif;font-size:11px;font-weight:500;padding:5px 13px;border-radius:35px;background:{BG};border:1px solid {BORDER};color:{TEXT2};cursor:pointer;transition:all .15s}}
.filter-btn:hover{{border-color:{PRIMARY};color:{PRIMARY}}}
.filter-btn.active{{background:{PRIMARY};border-color:{PRIMARY};color:{WHITE};font-weight:700}}
.fdiv{{width:1px;height:18px;background:{BORDER};margin:0 3px;flex-shrink:0}}
.sub-frow{{background:#fafefe;border-bottom:1px solid {BORDER2};padding:7px 32px;display:none;align-items:center;gap:7px;flex-wrap:wrap}}

/* MAIN CONTENT */
.main{{flex:1;padding:20px 32px}}

/* WEEK GRID */
.drow{{display:grid;grid-template-columns:repeat(7,1fr);gap:10px;min-height:360px}}
.dcol{{background:{WHITE};border:1px solid {BORDER};border-radius:14px;overflow:hidden;display:flex;flex-direction:column;box-shadow:{SH};transition:box-shadow .2s}}
.dcol:hover{{box-shadow:{SH_H}}}
.dcol.today{{border-color:{PRIMARY};box-shadow:0 0 0 2px {PRIMARY_L},{SH}}}
.dcol.past{{opacity:.82}}
.dhdr{{padding:9px 11px 7px;display:flex;align-items:center;justify-content:space-between;background:{PRIMARY_M};border-bottom:1px solid {BORDER};cursor:pointer;transition:background .15s;user-select:none}}
.dhdr:hover{{background:#c8ede9}}
.today .dhdr{{background:{PRIMARY}}}
.today .dhdr:hover{{background:#046b6a}}
.dname{{font-family:'Poppins',sans-serif;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:{TEXT2}}}
.today .dname{{color:{WHITE}}}
.dopen{{font-size:14px;color:{TEXT3};line-height:1;margin-left:2px}}
.today .dopen{{color:rgba(255,255,255,.6)}}
.dhdr:hover .dopen{{color:{PRIMARY}}}
.today .dhdr:hover .dopen{{color:{WHITE}}}
.dcnt{{background:{PRIMARY};color:{WHITE};border-radius:10px;font-size:10px;font-weight:700;padding:1px 7px}}
.today .dcnt{{background:{WHITE};color:{PRIMARY}}}
.dbody{{display:flex;flex-direction:column;gap:7px;padding:8px;flex:1}}
.eday{{flex:1;display:flex;align-items:center;justify-content:center;color:{TEXT3};font-size:11px;border:1.5px dashed {BORDER};border-radius:9px;padding:16px 0;margin:2px 0}}

/* WEEK CARD */
.card{{background:{BG};border:1px solid {BORDER};border-radius:10px;padding:9px 10px;transition:all .15s;cursor:pointer}}
.card:hover{{box-shadow:{SH_H};transform:translateY(-1px);background:{WHITE};border-color:{PRIMARY}55}}
.ct{{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px}}
.ctitle{{font-size:12px;font-weight:500;color:{TEXT};line-height:1.4;margin-bottom:6px}}
.cmeta{{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px}}
.mi{{font-size:10px;color:{TEXT3};background:{WHITE};border:1px solid {BORDER};border-radius:20px;padding:1px 7px}}
.resp{{color:{TEXT2};font-weight:500}}
.cplats{{display:flex;flex-wrap:wrap;gap:5px}}
.pdot{{display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:50%;cursor:default;transition:transform .15s,box-shadow .15s}}
.pdot:hover{{transform:scale(1.15);box-shadow:0 2px 8px rgba(0,0,0,.15)}}
.pdot-link{{cursor:pointer}}
.pdot-link:hover{{transform:scale(1.2);box-shadow:0 3px 12px rgba(0,0,0,.22)}}

/* BADGES */
.badge{{display:inline-flex;align-items:center;gap:3px;font-size:10px;font-weight:600;border-radius:20px;padding:2px 8px;white-space:nowrap}}
.tipo-b{{font-weight:700}}
.estado-b{{display:inline-flex;align-items:center;gap:5px;font-size:10px;font-weight:700;border-radius:20px;padding:2px 8px;white-space:nowrap}}
.estado-b i{{width:6px;height:6px;border-radius:50%;flex-shrink:0;font-style:normal}}

/* MONTH GRID */
.mhdr-row{{display:grid;grid-template-columns:repeat(7,1fr);gap:3px;margin-bottom:4px}}
.mhdr{{text-align:center;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:{TEXT3};padding:5px 0}}
.mcells{{display:grid;grid-template-columns:repeat(7,1fr);gap:4px}}
.mcell{{background:{WHITE};border:1px solid {BORDER};border-radius:10px;padding:7px 8px;min-height:88px;transition:all .15s;cursor:pointer}}
.mcell:hover{{box-shadow:{SH_H};border-color:{PRIMARY}55}}
.mcell.out{{background:#f9fbfb;opacity:.55}}
.mcell.mtoday{{border-color:{PRIMARY};box-shadow:0 0 0 2px {PRIMARY_L}}}
.mdn{{font-family:'Poppins',sans-serif;font-size:12px;font-weight:700;color:{TEXT2};margin-bottom:5px}}
.today-dn{{background:{PRIMARY};color:{WHITE};width:22px;height:22px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:10px}}
.mcitems{{display:flex;flex-direction:column;gap:3px}}
.mini{{cursor:pointer}}
.mchip{{font-size:10px;font-weight:500;padding:3px 7px;border-radius:5px;display:flex;align-items:center;justify-content:space-between;gap:5px;transition:opacity .1s;line-height:1.3}}
.mchip:hover{{opacity:.8}}
.mctxt{{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1}}
.mcplats{{display:flex;gap:2px;flex-shrink:0}}
.mpdot{{display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;border-radius:50%}}

/* DAY VIEW MODAL */
.overlay{{position:fixed;inset:0;background:rgba(4,40,40,.45);z-index:200;animation:fadein .18s;display:none}}
.daymodal{{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);width:500px;max-width:94vw;max-height:84vh;background:{WHITE};border-radius:18px;overflow:hidden;display:none;flex-direction:column;z-index:201;box-shadow:0 24px 64px rgba(0,0,0,.22);animation:scalein .18s}}
.dm-hdr{{background:{PRIMARY};color:{WHITE};padding:18px 22px;display:flex;align-items:center;justify-content:space-between;flex-shrink:0}}
.dm-date{{font-family:'Poppins',sans-serif;font-size:15px;font-weight:700;text-transform:capitalize;line-height:1.2}}
.dm-sub{{font-size:11px;opacity:.75;margin-top:3px}}
.dm-close{{background:rgba(255,255,255,.18);border:none;color:{WHITE};border-radius:50%;width:30px;height:30px;cursor:pointer;font-size:16px;font-family:'Roboto',sans-serif;transition:background .15s;flex-shrink:0}}
.dm-close:hover{{background:rgba(255,255,255,.32)}}
.dm-body{{padding:16px;overflow-y:auto;flex:1;display:flex;flex-direction:column;gap:8px}}
.dm-empty{{text-align:center;color:{TEXT3};padding:44px 16px}}
.dm-empty div{{font-size:32px;margin-bottom:10px}}
.dm-empty p{{font-size:13px;color:{TEXT2}}}

/* IDEAS PANEL MODAL */
.id-overlay{{position:fixed;inset:0;background:rgba(4,40,40,.45);z-index:400;display:none;animation:fadein .18s}}
.ideasmodal{{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);width:640px;max-width:95vw;max-height:88vh;background:{WHITE};border-radius:18px;overflow:hidden;display:none;flex-direction:column;z-index:401;box-shadow:0 28px 72px rgba(0,0,0,.26);animation:scalein .18s}}
.id-hdr{{background:#d98909;color:{WHITE};padding:18px 24px;display:flex;align-items:center;justify-content:space-between;flex-shrink:0}}
.id-hdr-txt{{font-family:'Poppins',sans-serif;font-size:16px;font-weight:700}}
.id-hdr-sub{{font-size:11px;opacity:.8;margin-top:3px}}
.id-body{{padding:16px 20px;overflow-y:auto;flex:1;display:flex;flex-direction:column;gap:10px}}
.id-empty{{text-align:center;padding:48px 16px;color:{TEXT3}}}
.id-empty div{{font-size:36px;margin-bottom:12px}}
.id-card{{background:{BG};border:1px solid #f0d080;border-radius:12px;padding:14px 16px;transition:all .15s;cursor:pointer}}
.id-card:hover{{background:#fefae8;box-shadow:0 4px 16px rgba(217,137,9,.12);transform:translateY(-1px)}}
.id-card-top{{display:flex;align-items:flex-start;justify-content:space-between;gap:8px;margin-bottom:8px}}
.id-title{{font-size:13px;font-weight:600;color:{TEXT};line-height:1.4;flex:1}}
.id-meta{{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}}
.id-pill{{font-size:10px;color:{TEXT3};background:{WHITE};border:1px solid {BORDER};border-radius:20px;padding:2px 8px}}
.id-desc{{font-size:12px;color:{TEXT2};line-height:1.5;margin-top:6px;padding-top:6px;border-top:1px solid {BORDER}}}
.id-ref{{font-size:11px;color:{PRIMARY};margin-top:5px}}

@keyframes fadein{{from{{opacity:0}}to{{opacity:1}}}}
@keyframes scalein{{from{{opacity:0;transform:translate(-50%,-52%) scale(.96)}}to{{opacity:1;transform:translate(-50%,-50%) scale(1)}}}}

/* FOOTER */
.footer{{background:{PRIMARY};color:{WHITE};text-align:center;padding:16px 32px;font-size:11px;flex-shrink:0}}
.footer a{{color:#a9d7d7}}
.footer a:hover{{color:{WHITE}}}

/* RESPONSIVE */
@media(max-width:1100px){{.drow{{grid-template-columns:repeat(4,1fr)}}}}
@media(max-width:750px){{
  .drow{{grid-template-columns:repeat(2,1fr)}}
  .mcells{{grid-template-columns:repeat(4,1fr)}}
  .hdr,.stats,.ctrl,.frow,.sub-frow,.main{{padding-left:14px;padding-right:14px}}
}}
@media(max-width:480px){{
  .drow{{grid-template-columns:1fr}}
  .mcells{{grid-template-columns:repeat(2,1fr)}}
  .daymodal,.ideasmodal{{width:98vw}}
}}
</style>
</head>
<body>

{svg_sprite()}

<!-- HEADER -->
<header class="hdr">
  <div class="hdr-l">
    <div class="logo-bar"></div>
    <div>
      <div class="logo-txt">IMPULSA<span> Suite</span></div>
      <div class="logo-sub">Marketing Content Hub</div>
    </div>
  </div>
  <div class="hdr-r">
    <span class="upd">Actualizado: {generated}</span>
    <a href="https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#gid=1371647617"
       target="_blank" class="sheet-btn">📋 Abrir Sheet</a>
    <a href="/" class="sheet-btn" style="background:#e6f7f7;border-color:#b2e0df;color:#058b8a">🏠 Hub</a>
  </div>
</header>

<!-- STATS -->
<div class="stats">
  <div class="sc">
    <div class="si" style="background:{PRIMARY_L};color:{PRIMARY}">📅</div>
    <div><div class="sn">{len(wk_items)}</div><div class="sl">Esta semana</div></div>
  </div>
  <div class="sc">
    <div class="si" style="background:#e6f5ed;color:#1a7a4a">✓</div>
    <div><div class="sn" style="color:#1a7a4a">{published}</div><div class="sl">Publicados</div></div>
  </div>
  <div class="sc">
    <div class="si" style="background:#ece8f9;color:#412f86">⏱</div>
    <div><div class="sn" style="color:#412f86">{scheduled}</div><div class="sl">Programados</div></div>
  </div>
  <div class="sc">
    <div class="si" style="background:#fef3dc;color:#b06a00">⚙</div>
    <div><div class="sn" style="color:#b06a00">{production}</div><div class="sl">En producción</div></div>
  </div>
</div>

<!-- CONTROLS -->
<div class="ctrl">
  <div class="view-toggle">
    <button class="vbtn active" id="btn-week"  onclick="setView('week')">📅 Semana</button>
    <button class="vbtn"        id="btn-month" onclick="setView('month')">🗓 Mes</button>
  </div>
  <div class="period-nav">
    <div class="nav-arr" onclick="prevPeriod()">←</div>
    <div class="plbl" id="plbl"></div>
    <div class="nav-arr" onclick="nextPeriod()">→</div>
  </div>
  <button class="ideas-btn" onclick="openIdeas()">💡 Ideas{ideas_badge}</button>
</div>

<!-- FILTERS ROW 1 -->
<div class="frow">
  <span class="flbl">Contenido:</span>
  <button class="filter-btn active" data-ft onclick="filterTipo('all',this)">Todos</button>
  <button class="filter-btn" data-ft onclick="filterTipo('articulo',this)">📝 Artículo</button>
  <button class="filter-btn" data-ft onclick="filterTipo('video',this)">🎬 Video</button>
  <button class="filter-btn" data-ft onclick="filterTipo('publicacion',this)">📱 Publicación</button>
  <button class="filter-btn" data-ft onclick="filterTipo('email',this)">✉ Email</button>
  <button class="filter-btn" data-ft onclick="filterTipo('evento',this)">📅 Evento</button>
  <div class="fdiv"></div>
  <span class="flbl">Estado:</span>
  <button class="filter-btn active" data-fe onclick="filterEstado('all',this)">Todos</button>
  <button class="filter-btn" data-fe onclick="filterEstado('Publicado',this)">✓ Publicado</button>
  <button class="filter-btn" data-fe onclick="filterEstado('Programado',this)">⏱ Programado</button>
  <button class="filter-btn" data-fe onclick="filterEstado('En Producción',this)">⚙ En Producción</button>
</div>

<!-- FILTERS ROW 2 -->
<div class="sub-frow" id="platrow">
  <span class="flbl">Plataforma:</span>
  <div id="vp" style="display:none;gap:6px;flex-wrap:wrap;align-items:center">
    <button class="filter-btn active" data-fp onclick="filterPlat('all',this)">Todas</button>
    {vp_btns}
  </div>
  <div id="pp" style="display:none;gap:6px;flex-wrap:wrap;align-items:center">
    <button class="filter-btn active" data-fp onclick="filterPlat('all',this)">Todas</button>
    {pp_btns}
  </div>
</div>

<!-- MAIN CONTENT -->
<div class="main">
  <div id="vw">{"".join(week_grids)}</div>
  <div id="vm" style="display:none">{"".join(month_grids)}</div>
</div>

<!-- DAY VIEW MODAL -->
<div class="overlay" id="overlay" onclick="closeDay()"></div>
<div class="daymodal" id="daymodal">
  <div class="dm-hdr">
    <div>
      <div class="dm-date" id="dm-date">—</div>
      <div class="dm-sub" id="dm-sub"></div>
    </div>
    <button class="dm-close" onclick="closeDay()">✕</button>
  </div>
  <div class="dm-body" id="dm-body"></div>
</div>


<!-- IDEAS PANEL MODAL -->
<div class="id-overlay" id="id-overlay" onclick="closeIdeas()"></div>
<div class="ideasmodal" id="ideasmodal">
  <div class="id-hdr">
    <div>
      <div class="id-hdr-txt">💡 Banco de Ideas</div>
      <div class="id-hdr-sub" id="id-hdr-sub"></div>
    </div>
    <button class="dm-close" onclick="closeIdeas()">✕</button>
  </div>
  <div class="id-body" id="id-body"></div>
</div>

<!-- FOOTER -->
<footer class="footer">
  IMPULSA Suite · Content Hub ·
  <a href="https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#gid=1371647617" target="_blank">
    Editar en Google Sheets
  </a>
</footer>

<script>
const wLabels = {json.dumps(week_labels)};
const mLabels = {json.dumps(month_labels)};
const wIds    = {json.dumps(week_ids)};
const mIds    = {json.dumps(month_ids)};
const DAY_CARDS   = {json.dumps(day_cards_json)};
const IDEAS_LIST  = {json.dumps(ideas_json)};
const TIPO_META_JS = {json.dumps({k: v for k, v in TIPO_META.items()})};
const MESES_F = ["","Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
const DIAS_F  = ["Domingo","Lunes","Martes","Miércoles","Jueves","Viernes","Sábado"];

let view  = 'week';
let wi    = {cur_wi};
let mi    = {cur_mi};
let fCat  = 'all';
let fEst  = 'all';
let fPlat = 'all';

function updateLabel() {{
  document.getElementById('plbl').textContent = view === 'week' ? wLabels[wi] : mLabels[mi];
}}

function showGrid() {{
  wIds.forEach(id => {{ const e=document.getElementById(id); if(e) e.style.display='none'; }});
  mIds.forEach(id => {{ const e=document.getElementById(id); if(e) e.style.display='none'; }});
  const id = view === 'week' ? wIds[wi] : mIds[mi];
  const el = document.getElementById(id);
  if (el) el.style.display = '';
}}

function setView(v) {{
  view = v;
  document.getElementById('vw').style.display = v==='week'  ? '' : 'none';
  document.getElementById('vm').style.display = v==='month' ? '' : 'none';
  document.getElementById('btn-week').classList.toggle('active',  v==='week');
  document.getElementById('btn-month').classList.toggle('active', v==='month');
  showGrid(); updateLabel();
}}

function prevPeriod() {{
  if (view==='week'  && wi > 0)              wi--;
  else if (view==='month' && mi > 0)         mi--;
  showGrid(); updateLabel();
}}
function nextPeriod() {{
  if (view==='week'  && wi < wIds.length-1)  wi++;
  else if (view==='month' && mi < mIds.length-1) mi++;
  showGrid(); updateLabel();
}}

// ── FILTERS ──────────────────────────────────────────────────────────
function filterTipo(cat, btn) {{
  fCat = cat; fPlat = 'all';
  document.querySelectorAll('[data-ft]').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const showPlat = (cat==='video' || cat==='publicacion');
  document.getElementById('platrow').style.display = showPlat ? 'flex' : 'none';
  document.getElementById('vp').style.display = cat==='video'       ? 'flex' : 'none';
  document.getElementById('pp').style.display = cat==='publicacion' ? 'flex' : 'none';
  document.querySelectorAll('[data-fp]').forEach(b => {{
    b.classList.remove('active');
    if (b.textContent.trim()==='Todas') b.classList.add('active');
  }});
  applyFilters();
}}

function filterEstado(est, btn) {{
  fEst = est;
  document.querySelectorAll('[data-fe]').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  applyFilters();
}}

function filterPlat(plat, btn) {{
  fPlat = plat;
  const par = btn.closest('#vp,#pp');
  if (par) par.querySelectorAll('[data-fp]').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  applyFilters();
}}

function applyFilters() {{
  document.querySelectorAll('.card,.mini').forEach(el => {{
    const cat   = el.dataset.cat   || '';
    const est   = el.dataset.estado || '';
    const plats = (el.dataset.plats || '').toLowerCase();
    let show = true;
    if (fCat  !== 'all') show = show && cat === fCat;
    if (fEst  !== 'all') show = show && est === fEst;
    if (fPlat !== 'all') show = show && plats.includes(fPlat.toLowerCase());
    el.style.display = show ? '' : 'none';
  }});
}}

// ── DAY VIEW ─────────────────────────────────────────────────────────
function openDay(date) {{
  const parts = date.split('-');
  const d = new Date(+parts[0], +parts[1]-1, +parts[2]);
  const label = DIAS_F[d.getDay()] + ', ' + d.getDate() + ' de ' + MESES_F[d.getMonth()+1] + ' ' + d.getFullYear();
  const cards = DAY_CARDS[date];
  document.getElementById('dm-date').textContent = label;
  const cnt = cards ? (cards.match(/class="card"/g)||[]).length : 0;
  document.getElementById('dm-sub').textContent = cnt ? cnt + (cnt===1?' pieza de contenido':' piezas de contenido') : '';
  document.getElementById('dm-body').innerHTML = cards ||
    '<div class="dm-empty"><div>📭</div><p>No hay contenido programado para este día.</p></div>';
  document.getElementById('overlay').style.display = '';
  document.getElementById('daymodal').style.display = 'flex';
  document.body.style.overflow = 'hidden';
}}

function closeDay() {{
  document.getElementById('overlay').style.display = 'none';
  document.getElementById('daymodal').style.display = 'none';
  document.body.style.overflow = '';
}}

// ── IDEAS PANEL ───────────────────────────────────────────────────────
function openIdeas() {{
  const ideas = IDEAS_LIST;
  document.getElementById('id-hdr-sub').textContent =
    ideas.length ? ideas.length + (ideas.length===1?' idea':' ideas') + ' en el banco' : 'Sin ideas registradas';

  if (!ideas.length) {{
    document.getElementById('id-body').innerHTML =
      '<div class="id-empty"><div>💡</div><p>No hay ideas registradas aún.<br>Agrega filas con Estado "Idea" en el Sheet.</p></div>';
  }} else {{
    document.getElementById('id-body').innerHTML = ideas.map(idea => {{
      const tm = TIPO_META_JS[idea.tipo] || {{c:'#646464',bg:'#f3f3f3'}};
      const tipoBadge = idea.tipo
        ? `<span class="badge tipo-b" style="color:${{tm.c}};background:${{tm.bg}}">${{idea.tipo}}</span>` : '';
      const fechaPill = idea.fecha
        ? `<span class="id-pill">📅 ${{idea.fecha}}</span>` : '';
      const respPill  = idea.responsable
        ? `<span class="id-pill">👤 ${{idea.responsable}}</span>` : '';
      const desc = idea.descripcion
        ? `<div class="id-desc">${{idea.descripcion}}</div>` : '';
      const ref  = idea.ref
        ? `<div class="id-ref">🔗 Referencia: <a href="${{idea.ref.startsWith('http')?idea.ref:'#'}}" target="_blank" style="color:inherit">${{idea.ref}}</a></div>` : '';
      return `<div class="id-card">
        <div class="id-card-top"><span class="id-title">${{idea.titulo||'(sin título)'}}</span>${{tipoBadge}}</div>
        <div class="id-meta">${{fechaPill}}${{respPill}}</div>
        ${{desc}}${{ref}}
      </div>`;
    }}).join('');
  }}

  document.getElementById('id-overlay').style.display = '';
  document.getElementById('ideasmodal').style.display = 'flex';
  document.body.style.overflow = 'hidden';
}}

function closeIdeas() {{
  document.getElementById('id-overlay').style.display = 'none';
  document.getElementById('ideasmodal').style.display = 'none';
  document.body.style.overflow = '';
}}

document.addEventListener('keydown', e => {{
  if (e.key==='Escape') {{ closeDay(); closeIdeas(); }}
}});

// Init
showGrid(); updateLabel();
</script>
</body>
</html>"""

# ── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    creds = Credentials.from_service_account_file(SA_KEY, scopes=[
        "https://www.googleapis.com/auth/spreadsheets.readonly",
    ])
    service = build("sheets", "v4", credentials=creds)
    print("📥 Leyendo Calendario Editorial...")
    rows = read_sheet()
    print("🔍 Cargando referencias de otras pestañas...")
    ref_data = load_references(service, SHEET_ID)
    items = normalize(rows, ref_data)
    print(f"   {len(items)} piezas cargadas")
    print("🏗️  Generando HTML...")
    html = build_html(items)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ {OUT_FILE} listo ({len(html)//1024}KB)")

    # Copiar al Hub para Vercel
    try:
        import shutil
        from pathlib import Path
        hub_content = Path(__file__).resolve().parent.parent.parent.parent / 'Hub' / 'public' / 'content'
        hub_content.mkdir(parents=True, exist_ok=True)
        shutil.copy2(OUT_FILE, hub_content / 'index.html')
        print(f"✅ Hub/public/content/index.html actualizado")
    except Exception as e:
        print(f"⚠ Hub copy: {e}")
