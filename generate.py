#!/usr/bin/env python3
"""
IMPULSA Content Panel — Generator v3
Uso: python3 generate.py
"""

import json, calendar as cal_mod
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
import gspread

SHEET_ID = "1tp1MRjJU6g6vF5VD78k-xbV6tcSM5XVZb_FQe9HIdIs"
SA_KEY   = "/Users/sebastian/.config/claude-keys/google-sheets-sa.json"
TAB_NAME = "Calendario Editorial"
OUT_FILE = "index.html"

# ── READ & NORMALIZE ─────────────────────────────────────────────────────────

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

def normalize(rows):
    items = []
    for r in rows:
        fecha = parse_fecha(r.get("FECHA", ""))
        if not fecha:
            continue
        items.append({
            "fecha":       fecha,
            "hora":        r.get("HORA (CLT)", ""),
            "tipo":        r.get("TIPO", ""),
            "categoria":   TIPO_TO_CAT.get(r.get("TIPO", ""), "otro"),
            "plataformas": [p.strip() for p in r.get("PLATAFORMAS", "").split("·") if p.strip()],
            "titulo":      r.get("TITULO / DESCRIPCIÓN", ""),
            "estado":      r.get("ESTADO", ""),
            "link":        r.get("LINK", ""),
            "responsable": r.get("RESPONSABLE", ""),
            "notas":       r.get("NOTAS", ""),
        })
    items.sort(key=lambda x: (x["fecha"], x["hora"] or "23:59"))
    return items

# ── BRAND TOKENS ─────────────────────────────────────────────────────────────

PRIMARY      = "#058b8a"
PRIMARY_DARK = "#046b6a"
PRIMARY_L    = "#e6f7f7"
PRIMARY_MID  = "#dcf5f0"
BG           = "#f4fafa"
WHITE        = "#ffffff"
BORDER       = "#d4eeee"
BORDER2      = "#e8f5f5"
TEXT         = "#4d4d4d"
TEXT2        = "#646464"
TEXT3        = "#999999"
SH           = "0 2px 12px rgba(5,139,138,.08)"
SH_H         = "0 6px 20px rgba(5,139,138,.16)"

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
    "Instagram":        {"c": "#e1306c", "bg": "#fce8f1", "i": "📸"},
    "TikTok":           {"c": "#ff0050", "bg": "#ffe5ee", "i": "🎵"},
    "YouTube":          {"c": "#cc0000", "bg": "#ffe5e5", "i": "▶"},
    "YouTube Shorts":   {"c": "#cc0000", "bg": "#ffe5e5", "i": "⚡"},
    "LinkedIn":         {"c": "#0a66c2", "bg": "#e5f0fb", "i": "💼"},
    "Blog":             {"c": PRIMARY,   "bg": PRIMARY_L, "i": "📝"},
    "Blog SistemaImpulsa": {"c": PRIMARY, "bg": PRIMARY_L, "i": "📝"},
    "Blog ImpulsaSuite":   {"c": PRIMARY, "bg": PRIMARY_L, "i": "📝"},
    "Blog CRMPeru":     {"c": PRIMARY,   "bg": PRIMARY_L, "i": "📝"},
    "Blog Colombia":    {"c": PRIMARY,   "bg": PRIMARY_L, "i": "📝"},
    "Email":            {"c": "#d98909", "bg": "#fef3dc", "i": "✉"},
    "Facebook":         {"c": "#1877f2", "bg": "#e5effe", "i": "📘"},
    "Twitter":          {"c": "#1da1f2", "bg": "#e5f5fe", "i": "🐦"},
}
ESTADO_META = {
    "Publicado":     {"c": "#1a7a4a", "bg": "#e6f5ed", "d": "#1a7a4a"},
    "Programado":    {"c": "#412f86", "bg": "#ece8f9", "d": "#412f86"},
    "En Producción": {"c": "#b06a00", "bg": "#fef3dc", "d": "#d98909"},
    "Borrador":      {"c": "#646464", "bg": "#f3f3f3", "d": "#999"},
    "Idea":          {"c": "#3578aa", "bg": "#e5eef7", "d": "#3578aa"},
    "Cancelado":     {"c": "#c0392b", "bg": "#fde8e6", "d": "#c0392b"},
}

DIAS_ES   = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
MESES_F   = ["", "Enero","Febrero","Marzo","Abril","Mayo","Junio",
             "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
MESES_S   = ["", "ene","feb","mar","abr","may","jun",
             "jul","ago","sep","oct","nov","dic"]

# ── BADGE HELPERS ─────────────────────────────────────────────────────────────

def plat_badge(name):
    m = PLAT_META.get(name, {"c": TEXT2, "bg": "#f3f3f3", "i": "🌐"})
    return (f'<span class="pdot" title="{name}" '
            f'style="background:{m["bg"]};border:1.5px solid {m["c"]}33">'
            f'{m["i"]}</span>')

def tipo_badge(name):
    if not name: return ""
    m = TIPO_META.get(name, {"c": TEXT2, "bg": "#f3f3f3"})
    return f'<span class="badge tipo-b" style="color:{m["c"]};background:{m["bg"]}">{name}</span>'

def estado_badge(name):
    if not name: return ""
    m = ESTADO_META.get(name, {"c": TEXT2, "bg": "#f3f3f3", "d": TEXT2})
    return (f'<span class="estado-b" style="color:{m["c"]};background:{m["bg"]}">'
            f'<i style="background:{m["d"]}"></i>{name}</span>')

# ── WEEK CARD (full) ──────────────────────────────────────────────────────────

def build_card(item):
    cat   = item["categoria"]
    plats = ", ".join(item["plataformas"])
    plb   = "".join(plat_badge(p) for p in item["plataformas"])
    lo    = f'<a href="{item["link"]}" target="_blank" rel="noopener" class="cl">' if item["link"] else '<span class="cl">'
    lc    = "</a>" if item["link"] else "</span>"
    arrow = ' <span class="arr">↗</span>' if item["link"] else ""
    hora  = f'<span class="mi">🕐 {item["hora"]} CLT</span>' if item["hora"] else ""
    resp  = f'<span class="mi resp">{item["responsable"]}</span>' if item["responsable"] else ""
    return (f'<div class="card" data-cat="{cat}" data-plats="{plats}" data-estado="{item["estado"]}">'
            f'<div class="ct">{tipo_badge(item["tipo"])}{estado_badge(item["estado"])}</div>'
            f'<div class="ctitle">{lo}{item["titulo"] or "(sin título)"}{arrow}{lc}</div>'
            f'<div class="cmeta">{hora}{resp}</div>'
            f'<div class="cplats">{plb}</div></div>')

# ── MONTH MINI-CARD ───────────────────────────────────────────────────────────

def build_mini(item):
    cat   = item["categoria"]
    plats = ", ".join(item["plataformas"])
    m     = TIPO_META.get(item["tipo"], {"c": TEXT2, "bg": "#f3f3f3"})
    title = (item["titulo"][:36] + "…") if len(item["titulo"]) > 36 else item["titulo"]
    lo    = f'<a href="{item["link"]}" target="_blank" rel="noopener">' if item["link"] else "<div>"
    lc    = "</a>" if item["link"] else "</div>"
    hora  = f' · {item["hora"]}' if item["hora"] else ""
    pdots = "".join(
        f'<span class="mpdot" title="{p}" style="background:{PLAT_META.get(p,{"bg":"#f3f3f3"})["bg"]};border:1px solid {PLAT_META.get(p,{"c":TEXT3})["c"]}22">'
        f'{PLAT_META.get(p,{"i":"🌐"})["i"]}</span>'
        for p in item["plataformas"]
    )
    return (f'<div class="mini" data-cat="{cat}" data-plats="{plats}" data-estado="{item["estado"]}">'
            f'{lo}<div class="mchip" style="color:{m["c"]};background:{m["bg"]};border-left:3px solid {m["c"]}">'
            f'<span class="mchip-txt">{title}{hora}</span>'
            f'<span class="mchip-plats">{pdots}</span>'
            f'</div>{lc}</div>')

# ── WEEK GRID ─────────────────────────────────────────────────────────────────

def build_week_grid(items, week_start, grid_id):
    today_s = datetime.now().strftime("%Y-%m-%d")
    cols = []
    for i in range(7):
        d  = week_start + timedelta(days=i)
        ds = d.strftime("%Y-%m-%d")
        di = [x for x in items if x["fecha"] == ds]
        is_today = ds == today_s
        is_past  = ds < today_s
        cnt_h = f'<span class="dcnt">{len(di)}</span>' if di else ""
        cards = "".join(build_card(it) for it in di)
        empty = '<div class="eday">Sin contenido</div>' if not di else ""
        cols.append(
            f'<div class="dcol{"" if not is_today else " today"}{"" if not is_past else " past"}">'
            f'<div class="dhdr"><span class="dname">{DIAS_ES[d.weekday()]} {d.day}</span>{cnt_h}</div>'
            f'<div class="dbody">{cards}{empty}</div></div>'
        )
    return (f'<div class="week-grid" id="{grid_id}" style="display:none">'
            f'<div class="drow">{"".join(cols)}</div></div>')

def week_label(mon_str):
    mon = datetime.strptime(mon_str, "%Y-%m-%d")
    sun = mon + timedelta(days=6)
    iso = mon.isocalendar()[1]
    return f"W{iso} · {mon.day} {MESES_S[mon.month]} — {sun.day} {MESES_S[sun.month]} {sun.year}"

# ── MONTH GRID ────────────────────────────────────────────────────────────────

def build_month_grid(items, year, month, grid_id):
    today_s  = datetime.now().strftime("%Y-%m-%d")
    first    = datetime(year, month, 1)
    last_day = cal_mod.monthrange(year, month)[1]
    last     = datetime(year, month, last_day)
    start    = first - timedelta(days=first.weekday())
    end      = last  + timedelta(days=(6 - last.weekday()))

    hdrs = "".join(f'<div class="mhdr">{d}</div>' for d in DIAS_ES)
    cells = []
    cur = start
    while cur <= end:
        ds       = cur.strftime("%Y-%m-%d")
        di       = [x for x in items if x["fecha"] == ds]
        in_mon   = (cur.month == month)
        is_today = (ds == today_s)
        minis    = "".join(build_mini(it) for it in di)
        dn_style = (f'<div class="mdn today-dn">{cur.day}</div>' if is_today
                    else f'<div class="mdn">{cur.day}</div>')
        cells.append(
            f'<div class="mcell{"" if in_mon else " out"}{"" if not is_today else " mtoday"}">'
            f'{dn_style}<div class="mcitems">{minis}</div></div>'
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
        d   = datetime.strptime(it["fecha"], "%Y-%m-%d")
        mon = d - timedelta(days=d.weekday())
        weeks_set.add(mon.strftime("%Y-%m-%d"))
    cur_mon = today - timedelta(days=today.weekday())
    weeks_set.add(cur_mon.strftime("%Y-%m-%d"))
    weeks = sorted(weeks_set)
    cur_wi = weeks.index(cur_mon.strftime("%Y-%m-%d")) if cur_mon.strftime("%Y-%m-%d") in weeks else 0

    week_grids  = [build_week_grid(items, datetime.strptime(w, "%Y-%m-%d"), f"wk-{i}")
                   for i, w in enumerate(weeks)]
    week_labels = [week_label(w) for w in weeks]
    week_ids    = [f"wk-{i}" for i in range(len(weeks))]

    # ── Months ──
    months_set = set()
    for it in items:
        d = datetime.strptime(it["fecha"], "%Y-%m-%d")
        months_set.add((d.year, d.month))
    months_set.add((today.year, today.month))
    months = sorted(months_set)
    cur_mi = next((i for i, (y, m) in enumerate(months)
                   if y == today.year and m == today.month), 0)

    month_grids  = [build_month_grid(items, y, m, f"mo-{i}")
                    for i, (y, m) in enumerate(months)]
    month_labels = [f"{MESES_F[m]} {y}" for y, m in months]
    month_ids    = [f"mo-{i}" for i in range(len(months))]

    # ── Stats ──
    wk_items  = [it for it in items
                 if abs((datetime.strptime(it["fecha"], "%Y-%m-%d") - cur_mon).days) < 7]
    published  = sum(1 for it in wk_items if it["estado"] == "Publicado")
    scheduled  = sum(1 for it in wk_items if it["estado"] == "Programado")
    production = sum(1 for it in wk_items if it["estado"] == "En Producción")

    # ── Platform sets ──
    video_plats = sorted({p for it in items if it["categoria"] == "video"
                          for p in it["plataformas"]})
    pub_plats   = sorted({p for it in items if it["categoria"] == "publicacion"
                          for p in it["plataformas"]})
    # fallback defaults if empty
    if not video_plats:
        video_plats = ["Instagram", "TikTok", "YouTube", "YouTube Shorts"]
    if not pub_plats:
        pub_plats   = ["Instagram", "TikTok", "LinkedIn", "Facebook"]

    vp_btns = "\n".join(
        f'<button class="filter-btn" data-fp onclick="filterPlat(\'{p}\',this)">'
        f'{PLAT_META.get(p,{}).get("i","🌐")} {p}</button>' for p in video_plats)
    pp_btns = "\n".join(
        f'<button class="filter-btn" data-fp onclick="filterPlat(\'{p}\',this)">'
        f'{PLAT_META.get(p,{}).get("i","🌐")} {p}</button>' for p in pub_plats)

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>IMPULSA · Content Hub</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@600;700&family=Roboto:wght@400;500&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Roboto',sans-serif;background:{BG};color:{TEXT};min-height:100vh;font-size:13px}}
a{{text-decoration:none;color:inherit}}

/* HEADER */
.hdr{{background:{WHITE};border-bottom:1px solid {BORDER};padding:0 32px;display:flex;align-items:center;justify-content:space-between;height:60px;position:sticky;top:0;z-index:100;box-shadow:0 2px 6px rgba(5,139,138,.07)}}
.hdr-l{{display:flex;align-items:center;gap:12px}}
.logo-bar{{width:4px;height:30px;background:{PRIMARY};border-radius:3px}}
.logo-txt{{font-family:'Poppins',sans-serif;font-size:14px;font-weight:700;text-transform:uppercase;letter-spacing:.8px}}
.logo-txt span{{color:{PRIMARY}}}
.logo-sub{{font-size:10px;color:{TEXT3};letter-spacing:.4px;margin-top:1px}}
.hdr-r{{display:flex;align-items:center;gap:10px}}
.upd{{font-size:11px;color:{TEXT3};background:{PRIMARY_L};border:1px solid {BORDER};border-radius:20px;padding:4px 12px}}
.sheet-btn{{font-size:11px;font-weight:500;color:{PRIMARY};background:{PRIMARY_L};border:1px solid {PRIMARY};border-radius:35px;padding:6px 16px;transition:all .15s;cursor:pointer}}
.sheet-btn:hover{{background:{PRIMARY};color:{WHITE}}}

/* STATS */
.stats{{background:{WHITE};border-bottom:1px solid {BORDER};padding:12px 32px;display:flex;gap:8px;flex-wrap:wrap}}
.sc{{display:flex;align-items:center;gap:9px;background:{BG};border:1px solid {BORDER};border-radius:14px;padding:9px 18px;min-width:120px}}
.si{{width:34px;height:34px;border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:15px;flex-shrink:0}}
.sn{{font-family:'Poppins',sans-serif;font-size:19px;font-weight:700;line-height:1}}
.sl{{font-size:10px;color:{TEXT3};margin-top:2px;font-weight:500}}

/* CONTROLS BAR */
.ctrl{{background:{WHITE};border-bottom:1px solid {BORDER};padding:10px 32px;display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap}}
.view-toggle{{display:flex;background:{BG};border:1px solid {BORDER};border-radius:35px;padding:3px;gap:2px}}
.vbtn{{font-family:'Roboto',sans-serif;font-size:12px;font-weight:500;padding:5px 18px;border-radius:35px;background:transparent;border:none;color:{TEXT2};cursor:pointer;transition:all .15s}}
.vbtn.active{{background:{PRIMARY};color:{WHITE};font-weight:700;box-shadow:0 2px 6px rgba(5,139,138,.3)}}
.period-nav{{display:flex;align-items:center;gap:10px}}
.nav-arr{{background:{PRIMARY_L};border:1px solid {BORDER};color:{PRIMARY};border-radius:35px;width:32px;height:32px;display:flex;align-items:center;justify-content:center;cursor:pointer;font-size:14px;font-weight:700;transition:all .15s;user-select:none}}
.nav-arr:hover{{background:{PRIMARY};color:{WHITE}}}
.period-lbl{{font-family:'Poppins',sans-serif;font-size:13px;font-weight:700;color:{TEXT};min-width:220px;text-align:center}}

/* FILTERS */
.frow{{background:{WHITE};border-bottom:1px solid {BORDER};padding:9px 32px;display:flex;align-items:center;gap:7px;flex-wrap:wrap}}
.flbl{{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.7px;color:{TEXT3};white-space:nowrap}}
.filter-btn{{font-family:'Roboto',sans-serif;font-size:11px;font-weight:500;padding:5px 14px;border-radius:35px;background:{BG};border:1px solid {BORDER};color:{TEXT2};cursor:pointer;transition:all .15s}}
.filter-btn:hover{{border-color:{PRIMARY};color:{PRIMARY}}}
.filter-btn.active{{background:{PRIMARY};border-color:{PRIMARY};color:{WHITE};font-weight:700}}
.fdiv{{width:1px;height:18px;background:{BORDER};margin:0 3px}}
.sub-frow{{background:#fafefe;border-bottom:1px solid {BORDER2};padding:7px 32px;display:none;align-items:center;gap:7px;flex-wrap:wrap}}

/* CONTENT AREA */
.content{{padding:22px 32px}}

/* WEEK GRID */
.drow{{display:grid;grid-template-columns:repeat(7,1fr);gap:10px;min-height:380px}}
.dcol{{background:{WHITE};border:1px solid {BORDER};border-radius:14px;overflow:hidden;display:flex;flex-direction:column;box-shadow:{SH};transition:box-shadow .2s}}
.dcol:hover{{box-shadow:{SH_H}}}
.dcol.today{{border-color:{PRIMARY};box-shadow:0 0 0 2px {PRIMARY_L},{SH}}}
.dcol.past{{opacity:.82}}
.dhdr{{padding:9px 11px 7px;display:flex;align-items:center;justify-content:space-between;background:{PRIMARY_MID};border-bottom:1px solid {BORDER}}}
.today .dhdr{{background:{PRIMARY}}}
.dname{{font-family:'Poppins',sans-serif;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:{TEXT2}}}
.today .dname{{color:{WHITE}}}
.dcnt{{background:{PRIMARY};color:{WHITE};border-radius:10px;font-size:10px;font-weight:700;padding:1px 7px}}
.today .dcnt{{background:{WHITE};color:{PRIMARY}}}
.dbody{{display:flex;flex-direction:column;gap:7px;padding:8px;flex:1}}
.eday{{flex:1;display:flex;align-items:center;justify-content:center;color:{TEXT3};font-size:11px;border:1.5px dashed {BORDER};border-radius:9px;padding:16px 0;margin:2px 0}}

/* WEEK CARD */
.card{{background:{BG};border:1px solid {BORDER};border-radius:10px;padding:9px 10px;transition:all .15s;cursor:default}}
.card:hover{{box-shadow:{SH_H};transform:translateY(-1px);background:{WHITE};border-color:{PRIMARY}33}}
.ct{{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px}}
.ctitle{{font-size:12px;font-weight:500;color:{TEXT};line-height:1.4;margin-bottom:6px}}
.cl{{color:{TEXT}}}
.cl:hover{{color:{PRIMARY}}}
.arr{{font-size:10px;color:{PRIMARY};margin-left:2px}}
.cmeta{{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px}}
.mi{{font-size:10px;color:{TEXT3};background:{WHITE};border:1px solid {BORDER};border-radius:20px;padding:1px 7px}}
.resp{{color:{TEXT2};font-weight:500}}
.cplats{{display:flex;flex-wrap:wrap;gap:5px;margin-top:2px}}
.pdot{{display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:50%;font-size:13px;cursor:default;transition:transform .15s,box-shadow .15s;flex-shrink:0}}
.pdot:hover{{transform:scale(1.18);box-shadow:0 2px 8px rgba(0,0,0,.12)}}

/* BADGE */
.badge{{display:inline-flex;align-items:center;gap:3px;font-size:10px;font-weight:600;border-radius:20px;padding:2px 8px;white-space:nowrap}}
.tipo-b{{font-weight:700}}
.estado-b{{display:inline-flex;align-items:center;gap:5px;font-size:10px;font-weight:700;border-radius:20px;padding:2px 8px;white-space:nowrap}}
.estado-b i{{width:6px;height:6px;border-radius:50%;flex-shrink:0;font-style:normal}}

/* MONTH GRID */
.mhdr-row{{display:grid;grid-template-columns:repeat(7,1fr);gap:3px;margin-bottom:4px}}
.mhdr{{text-align:center;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:{TEXT3};padding:5px 0}}
.mcells{{display:grid;grid-template-columns:repeat(7,1fr);gap:4px}}
.mcell{{background:{WHITE};border:1px solid {BORDER};border-radius:10px;padding:7px 8px;min-height:90px;transition:box-shadow .15s}}
.mcell:hover{{box-shadow:{SH_H}}}
.mcell.out{{background:#f9fbfb;opacity:.55}}
.mcell.mtoday{{border-color:{PRIMARY};box-shadow:0 0 0 2px {PRIMARY_L}}}
.mdn{{font-family:'Poppins',sans-serif;font-size:12px;font-weight:700;color:{TEXT2};margin-bottom:5px}}
.today-dn{{background:{PRIMARY};color:{WHITE};width:22px;height:22px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:10px}}
.mcitems{{display:flex;flex-direction:column;gap:3px}}

/* MINI CARD */
.mini{{cursor:default}}
.mchip{{font-size:10px;font-weight:500;padding:3px 7px;border-radius:5px;display:flex;align-items:center;justify-content:space-between;gap:5px;transition:opacity .1s;line-height:1.3}}
.mchip:hover{{opacity:.8}}
.mchip-txt{{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1}}
.mchip-plats{{display:flex;gap:2px;flex-shrink:0}}
.mpdot{{display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;border-radius:50%;font-size:9px}}

/* FOOTER */
.footer{{background:{PRIMARY};color:{WHITE};text-align:center;padding:16px 32px;font-size:11px}}
.footer a{{color:#a9d7d7}}
.footer a:hover{{color:{WHITE}}}

/* RESPONSIVE */
@media(max-width:1100px){{.drow{{grid-template-columns:repeat(4,1fr)}}}}
@media(max-width:750px){{
  .drow{{grid-template-columns:repeat(2,1fr)}}
  .mcells{{grid-template-columns:repeat(4,1fr)}}
  .hdr,.stats,.ctrl,.frow,.sub-frow,.content{{padding-left:14px;padding-right:14px}}
}}
@media(max-width:480px){{
  .drow{{grid-template-columns:1fr}}
  .mcells{{grid-template-columns:repeat(2,1fr)}}
}}
</style>
</head>
<body>

<!-- HEADER -->
<header class="hdr">
  <div class="hdr-l">
    <div class="logo-bar"></div>
    <div>
      <div class="logo-txt">IMPULSA<span> Suite</span></div>
      <div class="logo-sub">Content Hub</div>
    </div>
  </div>
  <div class="hdr-r">
    <span class="upd">Actualizado: {generated}</span>
    <a href="https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#gid=1371647617"
       target="_blank" class="sheet-btn">📋 Abrir Sheet</a>
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
    <button class="vbtn active" id="btn-week" onclick="setView('week')">📅 Semana</button>
    <button class="vbtn"        id="btn-month" onclick="setView('month')">🗓 Mes</button>
  </div>
  <div class="period-nav">
    <div class="nav-arr" onclick="prevPeriod()">←</div>
    <div class="period-lbl" id="plbl"></div>
    <div class="nav-arr" onclick="nextPeriod()">→</div>
  </div>
  <div style="width:120px"></div>
</div>

<!-- FILTERS ROW 1: tipo -->
<div class="frow">
  <span class="flbl">Contenido:</span>
  <button class="filter-btn active" data-ft onclick="filterTipo('all',this)">Todos</button>
  <button class="filter-btn" data-ft onclick="filterTipo('articulo',this)">📝 Artículo</button>
  <button class="filter-btn" data-ft onclick="filterTipo('video',this)">🎬 Video</button>
  <button class="filter-btn" data-ft onclick="filterTipo('publicacion',this)">📱 Publicación</button>
  <button class="filter-btn" data-ft onclick="filterTipo('email',this)">✉ Email</button>
  <button class="filter-btn" data-ft onclick="filterTipo('evento',this)">📅 Evento</button>
</div>

<!-- FILTERS ROW 2: plataforma (condicional) -->
<div class="sub-frow" id="platrow">
  <span class="flbl">Plataforma:</span>
  <!-- video platforms -->
  <div id="vp" style="display:none;gap:6px;flex-wrap:wrap;align-items:center">
    <button class="filter-btn active" data-fp onclick="filterPlat('all',this)">Todas</button>
    {vp_btns}
  </div>
  <!-- publicacion platforms -->
  <div id="pp" style="display:none;gap:6px;flex-wrap:wrap;align-items:center">
    <button class="filter-btn active" data-fp onclick="filterPlat('all',this)">Todas</button>
    {pp_btns}
  </div>
</div>

<!-- CONTENT -->
<div class="content">
  <!-- week view -->
  <div id="vw">
    {"".join(week_grids)}
  </div>
  <!-- month view -->
  <div id="vm" style="display:none">
    {"".join(month_grids)}
  </div>
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

let view     = 'week';
let wi       = {cur_wi};
let mi       = {cur_mi};
let fCat     = 'all';
let fPlat    = 'all';

function updateLabel() {{
  document.getElementById('plbl').textContent =
    view === 'week' ? wLabels[wi] : mLabels[mi];
}}

function showGrid() {{
  wIds.forEach(id => {{ const e = document.getElementById(id); if(e) e.style.display='none'; }});
  mIds.forEach(id => {{ const e = document.getElementById(id); if(e) e.style.display='none'; }});
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
  showGrid();
  updateLabel();
}}

function prevPeriod() {{
  if (view==='week'  && wi > 0)              wi--;
  if (view==='month' && mi > 0)              mi--;
  showGrid(); updateLabel();
}}

function nextPeriod() {{
  if (view==='week'  && wi < wIds.length-1)  wi++;
  if (view==='month' && mi < mIds.length-1)  mi++;
  showGrid(); updateLabel();
}}

function filterTipo(cat, btn) {{
  fCat = cat; fPlat = 'all';
  document.querySelectorAll('[data-ft]').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');

  const showPlat = (cat === 'video' || cat === 'publicacion');
  document.getElementById('platrow').style.display = showPlat ? 'flex' : 'none';
  document.getElementById('vp').style.display = (cat==='video')       ? 'flex' : 'none';
  document.getElementById('pp').style.display = (cat==='publicacion') ? 'flex' : 'none';

  // reset plat buttons
  document.querySelectorAll('[data-fp]').forEach(b => {{
    b.classList.remove('active');
    if (b.textContent.trim() === 'Todas') b.classList.add('active');
  }});
  applyFilters();
}}

function filterPlat(plat, btn) {{
  fPlat = plat;
  const parent = btn.closest('#vp, #pp');
  if (parent) parent.querySelectorAll('[data-fp]').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  applyFilters();
}}

function applyFilters() {{
  document.querySelectorAll('.card, .mini').forEach(el => {{
    const cat   = el.dataset.cat   || '';
    const plats = (el.dataset.plats || '').toLowerCase();
    let show = true;
    if (fCat  !== 'all') show = show && cat === fCat;
    if (fPlat !== 'all') show = show && plats.includes(fPlat.toLowerCase());
    el.style.display = show ? '' : 'none';
  }});
}}

// Init
showGrid();
updateLabel();
</script>
</body>
</html>"""

# ── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    print("📥 Leyendo Calendario Editorial...")
    rows  = read_sheet()
    items = normalize(rows)
    print(f"   {len(items)} piezas cargadas")
    print("🏗️  Generando HTML...")
    html = build_html(items)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ {OUT_FILE} listo ({len(html)//1024}KB)")
