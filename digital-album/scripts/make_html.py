"""Render plan.json into a single self-contained HTML plan (thumbnails embedded)."""
import base64
import io
import json
from datetime import datetime, timezone
from html import escape
from typing import Any

from PIL import Image

PLAN = json.load(open("plan.json"))
SEC = PLAN["sections"]
PH = {p["n"]: p for p in PLAN["photos"]}
PAGES = PLAN["pages"]
PW, PH_CM = 30.0, 22.0

# ---- defaults; album_config.py overrides them (run from the album folder) ----
THEMES: list[tuple] = []  # (key, Hebrew name, English name, tag, why, [sample image names in themes/])
COVER_TITLE_HE = COVER_SUB_HE = INTRO_TITLE_HE = INTRO_TEXT_HE = ""
LANG = "he"  # title language: "he" (Hebrew) or "en" (English); the book reads right to left either way
ALBUM_TAB_TITLE = ALBUM_TITLE = "Album plan"
ALBUM_LINE = ""
OUTPUT_HTML = "album-plan.html"
STORE_KEY = "album-marks"
PRODUCT_HTML = ""
TRIP_FACTS: list[tuple[str, str]] = []
COVER_ONLY = False
OPENING_TITLE_HE = OPENING_TEXT_HE = OPENING_SIGN_HE = ""
INTRO_TEXT_BOX = True
TEXT_HALF: dict = {}
QR_CODES: list = []
LUPA_OFFSET = None  # page numbers shown = Lupa's numbering (Lupa counts its opening-words page as page 1)  # (Hebrew fact, English source note) from the family's trip documents
import os, sys  # noqa: E401
sys.path.insert(0, os.getcwd())
from album_config import *  # noqa: F401,F403,E402
LANG_NAME = {"he": "Hebrew", "en": "English"}.get(LANG, LANG)
OPENING_SPAN = f"<span>{escape(OPENING_TEXT_HE)}</span>" if globals().get("OPENING_TEXT_SHOW", True) else ""
OFF = LUPA_OFFSET if LUPA_OFFSET is not None else (1 if (COVER_ONLY and OPENING_TEXT_HE) else 0)


def img_b64(path: str, size: int, quality: int = 72) -> str:
    """JPEG preview as base64."""
    im = Image.open(path).convert("RGB")
    im.thumbnail((size, size))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode()


def local_date(n: int) -> str:
    """Photo date in trip-local time."""
    p = PH[n]
    return datetime.fromtimestamp((p["cts"] + (p["tz"] or 0)) / 1000, timezone.utc).strftime("%d.%m.%Y")


def tune_txt(t: dict[str, int]) -> str:
    """Human-readable tuning string."""
    f = lambda v: f"+{v}" if v > 0 else str(v)
    return f"Brightness {f(t['bright'])}% · Contrast {f(t['contrast'])}% · Saturation {f(t['sat'])}%"


photos = PLAN["photos"]
keep = [p for p in photos if p["keep"]]
out = [p for p in photos if not p["keep"]]
space = [p for p in out if p.get("space_cut")]
n_hero = sum(1 for pg in PAGES if pg["kind"] == "hero")
n_spread = len({pg["photos"][0] for pg in PAGES if pg["kind"] == "spread"})
n_pages = len(PAGES)

frames: dict[int, str] = {}
for pg in PAGES:
    for r in pg.get("rects", []):
        if r["n"] in frames:
            continue
        where = (f"spread pages {pg['no'] - 1 + OFF}–{pg['no'] + OFF} (60×22 cm canvas, measured from the left page's left edge)" if pg.get("merged") and pg["shift"] == 0 else
                 f"spread pages {pg['no'] + OFF}–{pg['no'] + 1 + OFF} (60×22 cm canvas, measured from the left page's left edge)" if pg.get("merged") or pg["kind"] == "spread" else f"page {pg['no'] + OFF}")
        frames[r["n"]] = f"{where}: frame {r['w']:.1f} × {r['h']:.1f} cm, at {r['x']:.1f} / {r['y']:.1f} cm from top-left"

big = {n for pg in PAGES if pg["kind"] in ("hero", "spread", "title") for n in pg["photos"]}
mates: dict[int, list[int]] = {}
for i, pg in enumerate(PAGES):
    group = [r["n"] for r in pg.get("rects", [])] if pg.get("merged") else list(pg["photos"])
    for n in group:
        mates.setdefault(n, [])
        mates[n] += [m for m in group if m != n and m not in mates[n]]
data = {
    str(p["n"]): {
        "n": p["n"], "o": p["album_order"], "k": p["keep"], "sc": bool(p.get("space_cut")),
        "pl": p["place"], "s": p["scene"], "q": p["quality"], "pg": ("cover" if p["page"] == 0 else p["page"] + OFF if p["page"] else p["page"]), "sec": p["sec"],
        "r": p["out_reason"], "t": p["tune"], "tt": tune_txt(p["tune"]), "d": local_date(p["n"]),
        "fx": p["fix"], "note": p.get("note", ""), "fr": frames.get(p["n"], ""),
        "h": p["n"] in big, "ar": round(p["w"] / p["h"], 3), "mt": mates.get(p["n"], []),
    }
    for p in photos
}
imgs = {str(p["n"]): img_b64(f"thumbs/{p['n']:03d}.jpg", 600 if p["n"] in big else 360) for p in photos}
map_img = img_b64("map/route_map.png", 1800, 82)
for _i, _n in globals().get("BG_TEXTURES", {}).items():  # spread backgrounds: the sharp print file, not the 600 px thumb
    imgs[f"tex{_i}"] = img_b64(f"ready/upload/texbg_s{_i:02d}_{_n}.jpg", 1800, 85)
new_photos = [p for p in photos if p.get("new")]  # extra photos the user shared on 09.10 – candidates, not in the book yet
new_html = ("<h2 id='new'>New photos to consider · #" + f"{new_photos[0]['n']}–#{new_photos[-1]['n']}</h2>"
            "<div class='muted'>Shared 09.10. Not in the book yet – tell me by number to add one, to replace a photo, or to use it as a page background.</div>"
            "<div class='newgrid' style='display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:12px;margin:12px 0 28px'>"
            + "".join(f"<figure style='margin:0'><img src='data:image/jpeg;base64,{imgs[str(p['n'])]}' alt='#{p['n']}' "
                      f"style='width:100%;height:150px;object-fit:contain;background:#222;border-radius:6px'>"
                      f"<figcaption style='font-size:12px;line-height:1.35'><b>#{p['n']}</b> · {local_date(p['n'])} · {escape(p['place'])}<br>"
                      f"{escape(p['scene'])}<br><span class='muted'>{escape(p['note'])}</span></figcaption></figure>" for p in new_photos)
            + "</div>") if new_photos else ""

theme_imgs = {f: img_b64(f"themes/{f}.jpg", 750, 80) for *_, fs in THEMES for f in fs}

EMO = json.load(open("symbols/emoji/map.json")) if os.path.exists("symbols/emoji/map.json") else {}  # optional symbols
def png_b64(path: str, size: int) -> str:
    """Small transparent PNG as base64."""
    im = Image.open(path).convert("RGBA")
    im.thumbnail((size, size))
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


emo_b64 = {k: png_b64(f"symbols/emoji/{k}.png", 160) for k in EMO}
USED_SYM: set[str] = set()
SHOW_SYMBOLS = False  # no icons/symbols in page headers


def symbol_once(sec: str) -> str:
    """The place's cartoon symbol — each symbol appears once in the whole book."""
    if not SHOW_SYMBOLS or sec not in EMO or sec in USED_SYM:
        return ""
    USED_SYM.add(sec)
    return f"<b class='sym s-emo_{sec}' title='symbol'></b>"


def sym_css() -> str:
    """One CSS rule per symbol, so each image is embedded once."""
    return "\n".join(f".s-emo_{k}{{background-image:url(data:image/png;base64,{b})}}" for k, b in emo_b64.items())


def title_html(secs: list[str], page_used: list[bool]) -> str:
    """Hebrew place title(s); at most one symbol per page."""
    parts = []
    for s_ in secs:
        if s_ in SHOWN_SECS:  # a header is never repeated — later pages of the same place get none
            continue
        SHOWN_SECS.add(s_)
        sym = "" if page_used[0] else symbol_once(s_)
        if sym:
            page_used[0] = True
        parts.append(f"<span class='tt'>{sym}{escape(SEC[s_]['he'])}</span>")
    out = " · ".join(parts)
    if parts and not any("\u0590" <= ch <= "\u05ff" for ch in out):  # all-English header reads left to right
        return f"<span dir='ltr'>{out}</span>"
    return out


SHOWN_SECS: set[str] = set()
page_titles: dict[int, str] = {}
for pg in PAGES:
    k = pg["kind"]
    page_titles[pg["no"]] = {"title": "", "intro": INTRO_TITLE_HE, "map": "", "closing": globals().get("CLOSING_TITLE_HE", ""), "opening": "",
                             "text": "", "hero": "", "spread": ""}.get(k, "PLACE")
    if k == "hero" and pg["no"] in globals().get("HERO_TITLE_PAGES", set()):
        page_titles[pg["no"]] = "PLACE"  # a full-page photo that keeps its section title


def pct(v: float, total: float) -> str:
    """cm -> percent of page."""
    return f"{v / total * 100:.3f}%"


def ink(n: int, half: str = "") -> str:
    """Title colour that stands out on the blurred fill behind it (no box behind the text — ).
    half = "l"/"r" for a fill stretched across the open spread, "" for a fill that covers one page."""
    im = Image.open(f"thumbs/{n:03d}.jpg").convert("L")
    w, h = im.size
    box = {"l": (0, 0, w // 2, h // 8), "r": (w // 2, 0, w, h // 8)}.get(half, (0, 0, w, h // 8))
    lum = sum(i * c for i, c in enumerate(im.crop(box).histogram())) / max(1, sum(im.crop(box).histogram())) * 0.92
    return "ink-dark" if lum > 140 else "ink-light"


def tile(n: int, x: float, y: float, w: float, h: float, total_w: float = PW) -> str:
    """One photo frame, positioned in % of the page (x may be negative / beyond the page for lay-flat spreads)."""
    if x + w <= 0 or x >= PW:
        return ""
    vis = min(x + w, PW) - max(x, 0.0)
    if x >= -0.01 and x + w <= PW + 0.01:
        tag = f"<i>{n}</i>"
    elif vis >= w / 2:  # photo crosses the fold: tag on the page holding most of it, away from the fold
        tag = f"<i class='tl'>{n}</i>" if x + w > PW else f"<i>{n}</i>"
    else:
        tag = ""
    mk = "<s class='mk' title='Mark for replacement'>✕</s>" if -0.01 <= x < PW else ""
    return (f"<div class='ph' data-n='{n}' style='left:{pct(x, total_w)};top:{pct(y, PH_CM)};"
            f"width:{pct(w, total_w)};height:{pct(h, PH_CM)}'>{tag}{mk}</div>")


def pcol(page: str, no) -> str:
    """One page plus its number underneath (outside the page, like Lupa shows it)."""
    return f"<div class='pcol'>{page}<div class='pno'>{no}</div></div>"


def page_html(pg: dict[str, Any] | None, side: str, bg: int | None = None) -> str:
    """One album page (30 x 22 cm) drawn to scale. bg = photo whose blur runs across the whole open spread."""
    if pg is None:
        if side == "r" and COVER_ONLY and OPENING_TEXT_HE:  # Lupa's opening-words page faces page 1 (free extra page)
            ops = globals().get("OPENING_PHOTOS") or ([OPENING_PHOTO] if globals().get("OPENING_PHOTO") else [])
            op_html = "".join(tile(op["n"], op["x"], op["y"], op["w"], op["h"]) for op in ops)
            if globals().get("OPENING_BG"):  # faded photo behind the page
                op_html = (f"<img src='data:image/jpeg;base64,{img_b64(OPENING_BG, 900, 80)}' alt='page 1 background' "
                           f"style='position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:0'>") + op_html
            words = ("" if globals().get("OPENING_BG") else  # no text on page 1 – space for handwriting
                     f"<div class='textpage opening he'><b>{escape(OPENING_TITLE_HE)}</b>{OPENING_SPAN}<i>{escape(OPENING_SIGN_HE)}</i></div>")
            tag = "Page 1 · faded photo background, space for handwriting" if globals().get("OPENING_BG") else "Opening words · Lupa's editable text page (extra page, no charge)"
            return pcol(f"<div class='page opening {side}'>{words}{op_html}<div class='kindtag'>{tag}</div></div>", 1)
        return pcol(f"<div class='page empty {side}'><span>Inside cover</span></div>", "")
    no, kind = pg["no"], pg["kind"]
    title = page_titles.get(no, "")
    shift = pg.get("shift", 0.0)
    used = [False]
    if pg.get("merged") and kind == "intro":
        head = f"<div class='ptitle'>{symbol_once(pg['sec'])}{escape(title)}</div>" if shift else ""
    elif pg.get("merged"):
        head = ""
        for t in pg["titles"]:
            if t["sec"] in globals().get("HIDDEN_TITLES", {}).get(no, []) and (t["right"] <= 36) == (shift == 0):
                continue  # header the user removed
            on_left = t["right"] <= 36  # a title near the fold goes on the left page so it isn't cut
            if (shift == 0) == on_left:
                r = min(t["right"], 29.3) if on_left else t["right"] - shift
                th = title_html(t.get('secs', [t['sec']]), used)
                head += f"<div class='ptitle' style='right:{pct(PW - r, PW)}'>{th}</div>" if th else ""
    elif title == "PLACE":
        th = title_html(pg['secs'], used)
        head = f"<div class='ptitle'>{th}</div>" if th else ""
    else:
        head = f"<div class='ptitle'>{escape(title)}</div>" if title else ""
    if no in globals().get("TITLE_SCALE", {}) and head:  # smaller header so it fits beside a QR
        head = head.replace("class='ptitle'", f"class='ptitle' style='font-size:calc(clamp(11px,1.45vw,17px)*{globals()['TITLE_SCALE'][no]})'", 1)
    if no in globals().get("TITLE_BOTTOM", set()) and head:  # header moved to the page bottom
        head = head.replace("class='ptitle'", "class='ptitle pbottom'")
    extra = globals().get("EXTRA_TITLES", {}).get(no)
    if extra and extra not in head:
        head += f"<div class='ptitle'><span class='tt' dir='auto'>{escape(extra)}</span></div>"
    body = ""
    if kind == "title":
        r = pg["rects"][0]
        body = f"<div class='blur' data-bg='{r['n']}'></div>" + tile(r["n"], r["x"], r["y"], r["w"], r["h"])
        body += f"<div class='covertitle he'>{escape(COVER_TITLE_HE)}<small>{escape(COVER_SUB_HE)}</small></div><div class='kindtag'>Opening page · one family photo</div>"
        return pcol(f"<div class='page {kind} {side}' data-page='{no + OFF}'>{body}</div>", no + OFF)
    # blurred fill that continues across the facing page (one scene per open spread)
    wide_blur = (f"<div class='blur spreadblur' data-bg='{bg}' style='background-position:{'100% 50%' if side == 'r' else '0% 50%'}'></div>"
                 if bg else "")
    if kind == "hero":
        r = pg["rects"][0]
        body = (wide_blur or f"<div class='blur' data-bg='{r['n']}'></div>") + tile(r["n"], r["x"], r["y"], r["w"], r["h"])
        body += "<div class='kindtag'>Full page · blurred fill</div>"
        kind += " " + (ink(bg, side) if bg else ink(r["n"]))
    elif kind == "spread":
        r = pg["rects"][0]
        shift = 0 if pg["half"] == "left" else PW  # spread coords: left page = 0–30 cm, right page = 30–60 cm
        pos = "0% 50%" if pg["half"] == "left" else "100% 50%"
        body = f"<div class='blur spreadblur' data-bg='{r['n']}' style='background-position:{pos}'></div>"
        body += tile(r["n"], r["x"] - shift, r["y"], r["w"], r["h"])
        body += "<div class='kindtag'>Double-page spread · blurred fill</div>"
        kind += " " + ink(r["n"], "l" if pg["half"] == "left" else "r")
    elif kind == "map":
        body = "<img class='mapimg' src='data:image/jpeg;base64,MAPIMG' alt='Route map'><div class='kindtag'>Route map · full page</div>"
    elif kind == "opening":
        body = (f"<div class='textpage opening he'><b>{escape(OPENING_TITLE_HE)}</b>{OPENING_SPAN}"
                f"<i>{escape(OPENING_SIGN_HE)}</i></div><div class='kindtag'>Opening words · Lupa text page you can edit</div>")
    elif kind in ("text", "closing"):
        note = "Closing page: a few words + QR code to the trip videos" if kind == "closing" else "Short text page (a few words, or leave for notes)"
        body = f"<div class='textpage'>{escape(note)}</div>"
    else:
        body = "".join(tile(r["n"], r["x"] - shift, r["y"], r["w"], r["h"]) for r in pg["rects"])
        if kind == "feature":
            body += "<div class='kindtag'>Big photo · room for text in Lupa</div>"
        if pg.get("merged") and kind != "intro":
            body += "<div class='kindtag'>Lay-flat spread</div>" if pg["shift"] == 0 else ""
        if kind == "intro" and pg.get("shift") and INTRO_TEXT_BOX:
            body += f"<div class='introtext he'><b>{escape(INTRO_TITLE_HE)}</b>{escape(INTRO_TEXT_HE)}</div>"
        th = TEXT_HALF.get(pg["sec"]) if pg.get("textbox") else None
        if th and (th.get("title") or th.get("text")):  # empty = space left for handwriting
            body += (f"<div class='introtext he' style='left:{pct(1.0, PW)};top:{pct(2.4, PH_CM)};width:{pct(13.6, PW)};height:{pct(18.6, PH_CM)}'>"
                     f"<b>{escape(th['title'])}</b>{escape(th['text'])}</div>")
    for q in QR_CODES:  # QR code overlays (scan to open the linked video / album)
        if q["page"] == no:
            body += (f"<img class='qr' title='QR · {escape(q['note'])}' src='data:image/jpeg;base64,{img_b64(q['file'], 900, 95)}' "  # full resolution, so it scans from the screen
                     f"style='position:absolute;left:{pct(q['x'], PW)};top:{pct(q['y'], PH_CM)};width:{pct(q['s'], PW)};z-index:3;image-rendering:pixelated'>")
    if bg and kind not in ("hero", "title", "spread"):
        body = wide_blur + body
        kind += " onblur " + ink(bg, side)
    tex = globals().get("BG_TEXTURES", {}).get(no // 2)  # sharp texture photo running across this whole open spread
    if tex:
        soft = globals().get("BG_TEXTURE_SOFTEN", 0.18)
        body = f"<div class='texbg' data-bg='tex{no // 2}' style='--soft:{soft}'></div>" + (body.replace(wide_blur, "", 1) if wide_blur else body)
        kind = " ".join(c for c in kind.split() if not c.startswith("ink-") and c != "onblur") + " onblur " + ink(tex, side)
    return pcol(f"<div class='page {kind} {side}' data-page='{no + OFF}'>{head}{body}</div>", no + OFF)


# openings in right-to-left order: [inside cover | page 1], then (2 right, 3 left) ... [100 | inside back cover]
openings: list[tuple[Any, Any]] = [(None, PAGES[0])]
for k in range(1, n_pages // 2):
    openings.append((PAGES[2 * k - 1], PAGES[2 * k]))
openings.append((PAGES[-1], None))
def shared_blur(right: Any, left: Any) -> int | None:
    """If one page of the open spread is a full-page photo, its blur runs across the facing page too."""
    if not right or not left:
        return None
    for a, b in ((right, left), (left, right)):
        if a["kind"] == "hero" and b["kind"] in ("photos", "text", "closing"):
            return a["photos"][0]
    return None


spread_html = "".join(
    f"<div class='opening'><div class='pages'>{page_html(r, 'r', shared_blur(r, l))}{page_html(l, 'l', shared_blur(r, l))}</div></div>"
    for r, l in openings).replace("MAPIMG", map_img)

route, seen = [], []
for pg in PAGES:
    for s in pg.get("secs", []):
        if s not in seen and any(p["sec"] == s for p in photos):
            seen.append(s)
            route.append((s, pg["no"] + OFF))
sec_rows = []
for s, first_page in route:
    ph = [p for p in photos if p["sec"] == s]
    k = [p for p in ph if p["keep"]]
    nums = [p["n"] for p in ph]
    sec_rows.append(
        f"<tr><td class='he'>{escape(SEC[s]['he'])}</td><td class='muted'>{escape(SEC[s]['en'])}</td>"
        f"<td>{local_date(ph[0]['n'])}</td><td>{first_page}</td><td>{len(ph)}</td><td>{len(k)}</td>"
        f"<td class='muted'>{min(nums)}–{max(nums)}</td></tr>")

theme_html = []
for i, (key, he, en, tag, why, fs) in enumerate(THEMES):
    pics = "".join(f"<img src='data:image/jpeg;base64,{theme_imgs[f]}' alt='{escape(en)} sample'>" for f in fs)
    theme_html.append(
        f"<div class='theme {'top' if i == 0 else ''}'><div class='thead'><span class='rank'>{i + 1}</span>"
        f"<div><div class='he big'>{escape(he)}</div><div class='muted'>{escape(en)}</div></div><span class='tag'>{escape(tag)}</span></div>"
        f"<p>{escape(why)}</p><div class='tpics'>{pics}</div></div>")

out_reasons: dict[str, int] = {}
for p in out:
    r = p["out_reason"].lower()
    key = ("Cut to fit the page limit" if p.get("space_cut") else
           "Near-duplicate / similar shot" if any(w in r for w in ["duplicate", "similar", "better", "burst", "copy", "same"]) else
           "Blurry / soft" if any(w in r for w in ["blur", "soft", "shake", "motion"]) else
           "Too dark / exposure" if any(w in r for w in ["dark", "exposed", "exposure", "backlit", "bright"]) else
           "Low value / mundane" if any(w in r for w in ["mundane", "weak", "low", "filler", "generic", "repetitive", "plain"]) else
           "Document / screenshot / other")
    out_reasons[key] = out_reasons.get(key, 0) + 1
reason_rows = "".join(f"<tr><td>{escape(k)}</td><td>{v}</td></tr>" for k, v in sorted(out_reasons.items(), key=lambda x: -x[1]))
fills = [pg["fill"] for pg in PAGES if "fill" in pg]
km = json.load(open("map/route_stats.json"))["km"]
km_actual = (ROUTE_MILES_ACTUAL * 1.609344) if globals().get("ROUTE_MILES_ACTUAL") else None

CSS = open("plan.css").read() + "\n" + sym_css()
JS = open("plan.js").read()
cover_html = ""
if COVER_ONLY and COVER:
    cover_html = (f"<div class='card coverprev'><h3>Book cover</h3><div class='coverbox'><img src='data:image/jpeg;base64,{img_b64(globals().get('COVER_IMAGE') if os.path.exists(globals().get('COVER_IMAGE') or '') else f'thumbs/{COVER:03d}.jpg', 900)}' alt='cover'>"
                  "</div>"
                  f"<p class='muted'>{globals().get('COVER_NOTE', 'The cover photo fills the front cover; the title is drawn into the photo, on the sky.')}</p></div>")
if cover_html and globals().get("BACK_COVER_IMAGE") and os.path.exists(BACK_COVER_IMAGE):  # optional back-cover photo
    cover_html = cover_html.replace("<p class='muted'>", f"<h3 style='margin-top:14px'>Back cover</h3><div class='coverbox'><img src='data:image/jpeg;base64,{img_b64(BACK_COVER_IMAGE, 900)}' alt='back cover'></div><p class='muted'>", 1)
facts_html = (f"<div class='card facts' dir='{'rtl' if LANG == 'he' else 'ltr'}' lang='{LANG}'><h3>{'עובדות מהטיול' if LANG == 'he' else 'Trip facts'} <small dir='ltr'>· from your trip documents"
              " – use them for captions or the closing page</small></h3><ol>"
              + "".join(f"<li>{escape(t)}<span class='src'>{escape(src)}</span></li>" for t, src in TRIP_FACTS)
              + "</ol></div>") if TRIP_FACTS else ""
html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(ALBUM_TAB_TITLE)}</title>
<style>{CSS}
.facts ol{{columns:2 380px;column-gap:28px;margin:6px 0 0;padding-inline-start:22px;font-size:15px;line-height:1.5}}
.facts li{{break-inside:avoid;margin:0 0 6px}}
.facts .src{{display:block;direction:ltr;text-align:right;color:var(--muted);font-size:11.5px}}
.coverprev .coverbox{{position:relative;width:min(100%,560px)}} .coverprev img{{width:100%;border-radius:6px;display:block}}
.coverprev .covertitle{{position:absolute;top:0.4%;left:0;right:21.4%}}
.textpage.opening{{display:flex;flex-direction:column;gap:8px;justify-content:center;text-align:center;padding:8% 12%;line-height:1.5}}
.textpage.opening b{{font-size:1.4em}} .textpage.opening i{{font-style:normal;color:var(--muted)}}
.facts h3 small{{font-weight:400;color:var(--muted);font-size:13px}}</style>
</head>
<body>
<div class="wrap">
<h1>{escape(ALBUM_TITLE)}</h1>
<div class="muted">{ALBUM_LINE} · book reads <b>right to left</b>, place names in {LANG_NAME}</div>

<div class="kpis">
  <div class="card kpi"><b>{len(photos)}</b><span>Candidates, numbered 1–{len(photos)} by camera time</span></div>
  <div class="card kpi keep"><b>{len(keep)}</b><span>Kept in the album</span></div>
  <div class="card kpi out"><b>{len(out) - len(space)}</b><span>Left out for quality / duplicates</span></div>
  <div class="card kpi cut"><b>{len(space)}</b><span>Good but cut to fit the page limit — easy to add back</span></div>
  <div class="card kpi"><b>{n_pages}</b><span>Pages · {n_hero} full-page + {n_spread} double-page spreads + route map</span></div>
</div>

{facts_html}
{cover_html}
<div class="note"><b>How to use this page:</b> click a photo to see details. Click the red <b>✕</b> on any photo (or "Mark for replacement" in its details) and pick its replacement. To <b>swap two photos</b> on the same page or spread, open one and pick the other under "Swap with". For photos that are out, use "Add back". Your marks are saved in this browser. When you're done, press <b>Copy my marks</b> at the bottom right and paste the list to Claude.</div>

<div class="cols">
{PRODUCT_HTML.replace("__ROOM__", str(len(keep) + len(space)))}
<div class="card">
<h3>Layout rules in this version</h3>
<ul class="tight">
<li><b>No cropping.</b> Each frame has the photo's own shape (16:9, 4:3, portrait, panorama). Pages are drawn to scale; average page fill is {sum(fills) / len(fills) * 100:.0f}%.</li>
<li><b>In Lupa:</b> resize each frame to the size shown in the photo's details (cm), or turn off "fill frame". Frames are exact, so nothing gets cut.</li>
<li><b>Full pages and spreads</b> keep the photo's ratio. A blurred copy of the same photo fills the rest of the page and <b>continues across the facing page</b>, so the open spread reads as one scene. I can make these as ready-to-drop background images.</li>
<li><b>Portraits stay portrait.</b></li>
<li><b>Lay-flat spreads:</b> when both pages show the same place, they're designed as one 60×22 cm canvas and photos may cross the middle. When a spread holds two places, each place gets its own area, and the border between them may sit off the fold.</li>
<li><b>Place names in {LANG_NAME}</b>, plain text with no icons or symbols.</li>
<li><b>Margins:</b> to close wide empty margins, a frame may trim at most 5% off one side of a photo. No important detail is lost at that size. Average page fill: {sum(fills) / len(fills) * 100:.0f}%.</li>
<li><b>Order:</b> camera time{globals().get('ORDER_NOTE', ', with wrong camera clocks fixed')}. Photos from the same place (drone shots too) are grouped.</li>
<li><b>Big photo every 5–7 pages</b> ({n_hero} full pages, {n_spread} spreads, map on page 4).</li>
<li><b>Tuning:</b> per-photo brightness / contrast / saturation. Use the <b>Before / After</b> button.</li>
</ul>
<table>{reason_rows}</table>
</div>
</div>

<h2>Route map · page {next((pg["no"] + OFF for pg in PAGES if pg["kind"] == "map"), "–")}</h2>
<div class="card">
<img class="mapfull" src="data:image/jpeg;base64,{map_img}" alt="Route map of the trip">
<p class="muted">Built from your photos' own locations, 3 photos per place. The route follows real roads between stops: about {km:,.0f} km ({km / 1.609:,.0f} miles) stop to stop{f"; the map shows the real total from the RV bill, about {km_actual:,.0f} km ({km_actual / 1.609344:,.0f} miles), because the line misses driving inside the parks" if km_actual else ""}. {globals().get('MAP_NOTE', '')} Print file: <code>map/route_map.png</code> (30×22 cm at 300 dpi), ready to drop in as a full-page photo.</p>
</div>

<h2>{globals().get('COMPANY', 'Lupa')} theme recommendations</h2>
<div class="note">{globals().get('THEME_NOTE', 'Check in the album editor that the theme works with your chosen book and size before you start.')}</div>
{''.join(theme_html)}

<h2>Route & sections</h2>
<div class="card tablewrap"><table>
<tr><th>Place (page title)</th><th>English</th><th>Date</th><th>First page</th><th>Photos</th><th>Kept</th><th>Photo #</th></tr>
{''.join(sec_rows)}
</table></div>

<h2>Page-by-page plan</h2>
<div class="muted">Each row is one open spread as the book reads: <b>right page first</b>, then left. Pages are drawn to scale (30×22 cm). The yellow tag is the photo number.</div>
<div class="toolbar">
  <button id="ba">Show: Before</button>
  <span class="muted">Jump to page</span><input type="search" id="jump" placeholder="e.g. 48">
  <a class="btn" href="#index">Photo index ↓</a>
</div>
<div id="spreads">{spread_html}</div>

{new_html}
<h2 id="index">Photo index — all {len(photos)}</h2>
<div class="toolbar">
  <button class="f on" data-f="all">All {len(photos)}</button>
  <button class="f" data-f="keep">Kept {len(keep)}</button>
  <button class="f" data-f="out">Out {len(out) - len(space)}</button>
  <button class="f" data-f="cut">Cut for space {len(space)}</button>
  <button class="f" data-f="hero">Full page / spread</button>
  <button class="f" data-f="marked">My marks</button>
  <input type="search" id="q" placeholder="Photo # or word">
</div>
<div class="index" id="grid"></div>
</div>

<div class="markbar" id="markbar"><span id="markcount">No marks yet</span><button id="copy">Copy my marks</button><button id="clear">Clear</button></div>
<div class="lb" id="lb"><div class="lbin" id="lbin"></div></div>
<textarea id="copybox" aria-label="Marks to copy"></textarea>
<script>
const STORE_KEY = {json.dumps(STORE_KEY)};
const D = {json.dumps(data, ensure_ascii=False)};
const I = {json.dumps(imgs)};
const S = {json.dumps(SEC, ensure_ascii=False)};
{JS}
</script>
</body>
</html>
"""
open(OUTPUT_HTML, "w").write(html)
print("ok", round(len(html) / 1e6, 1), "MB")
