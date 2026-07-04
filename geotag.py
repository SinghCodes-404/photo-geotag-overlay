#!/usr/bin/env python3
"""Burn a GPS-Map-Camera-style LOCATION banner onto geotagged photos.

Reads GPS from each image's EXIF, reverse-geocodes it (OpenStreetMap /
Nominatim), fetches an OSM map thumbnail, and composites a bottom banner:

    [ map ]   <bold place title>
              <full address, wrapped>
              Lat: xx.xxxxxx°  Long: yy.yyyyyy°

No time/date information is written to the banner.

Usage:
    python3 geotag.py                 # process every *.jpg in this folder
    python3 geotag.py IMG20260625174721.jpg    # process specific file(s)

Output goes to ./geotagged/ with the original filename. Originals untouched.
"""
import io
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw, ImageFont
from PIL.ExifTags import TAGS, GPSTAGS

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------
OUT_DIR = "geotagged"
CACHE_FILE = ".geocode_cache.json"
ZOOM = 17                       # OSM tile zoom for the map thumbnail
CONTACT = "gs6117531@gmail.com"  # required by OSM/Nominatim usage policy
UA = f"geotag-script/1.0 ({CONTACT})"

FONT_BOLD = "/usr/share/fonts/liberation/LiberationSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/liberation/LiberationSans-Regular.ttf"

# Banner layout as fractions of image size (tuned to the sample photo)
MARGIN_F = 0.020        # left / bottom margin (of width)
MAP_F = 0.150           # map square side (of height)
TITLE_F = 0.0200        # title font size (of height)
BODY_F = 0.0145         # body font size (of height)
GAP_F = 0.0070          # line gap (of height)

TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"


# --------------------------------------------------------------------------
# EXIF / GPS
# --------------------------------------------------------------------------
def get_gps(path):
    """Return (lat, lon) decimal degrees, or None."""
    exif = Image.open(path)._getexif()
    if not exif:
        return None
    gps = None
    for k, v in exif.items():
        if TAGS.get(k) == "GPSInfo":
            gps = {GPSTAGS.get(kk, kk): vv for kk, vv in v.items()}
    if not gps or "GPSLatitude" not in gps:
        return None

    def dms(vals):
        d, m, s = (float(x) for x in vals)
        return d + m / 60 + s / 3600

    lat = dms(gps["GPSLatitude"])
    lon = dms(gps["GPSLongitude"])
    if gps.get("GPSLatitudeRef") == "S":
        lat = -lat
    if gps.get("GPSLongitudeRef") == "W":
        lon = -lon
    return lat, lon


# --------------------------------------------------------------------------
# Reverse geocoding (Nominatim) with on-disk cache
# --------------------------------------------------------------------------
_cache = {}
if os.path.exists(CACHE_FILE):
    try:
        _cache = json.load(open(CACHE_FILE))
    except Exception:
        _cache = {}


def _save_cache():
    json.dump(_cache, open(CACHE_FILE, "w"))


def reverse_geocode(lat, lon):
    """Return (title, full_address). Cached by rounded coords."""
    key = f"{lat:.5f},{lon:.5f}"
    if key in _cache:
        return tuple(_cache[key])

    url = "https://nominatim.openstreetmap.org/reverse?" + urllib.parse.urlencode(
        {"format": "jsonv2", "lat": lat, "lon": lon, "zoom": 18, "addressdetails": 1}
    )
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    data = json.load(urllib.request.urlopen(req, timeout=20))
    time.sleep(1.1)  # Nominatim: max 1 req/sec

    addr = data.get("address", {})
    full = data.get("display_name", f"{lat:.6f}, {lon:.6f}")
    # Title: locality, state, country  (matches the sample photo)
    locality = (
        addr.get("village") or addr.get("town") or addr.get("city")
        or addr.get("suburb") or addr.get("hamlet") or addr.get("county")
        or addr.get("municipality") or ""
    )
    parts = [p for p in (locality, addr.get("state"), addr.get("country")) if p]
    title = ", ".join(parts) if parts else full.split(",")[0]

    _cache[key] = [title, full]
    _save_cache()
    return title, full


# --------------------------------------------------------------------------
# OSM map thumbnail
# --------------------------------------------------------------------------
_tile_cache = {}


def _fetch_tile(z, x, y):
    k = (z, x, y)
    if k not in _tile_cache:
        url = TILE_URL.format(z=z, x=x, y=y)
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        _tile_cache[k] = Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=20).read())).convert("RGB")
    return _tile_cache[k]


def make_map(lat, lon, size, zoom=ZOOM):
    """Return an RGB map image of side `size`, centered on lat/lon, with a pin."""
    n = 2 ** zoom
    xt = (lon + 180.0) / 360.0 * n
    latr = math.radians(lat)
    yt = (1 - math.asinh(math.tan(latr)) / math.pi) / 2 * n

    px, py = xt * 256, yt * 256  # global pixel coords of center
    need = size + 512            # stitch a bit extra for centered crop
    x0 = int((px - need / 2) // 256)
    y0 = int((py - need / 2) // 256)
    ntiles = need // 256 + 2

    canvas = Image.new("RGB", (ntiles * 256, ntiles * 256), (230, 230, 230))
    for i in range(ntiles):
        for j in range(ntiles):
            tx, ty = x0 + i, y0 + j
            if 0 <= tx < n and 0 <= ty < n:
                try:
                    canvas.paste(_fetch_tile(zoom, tx, ty), (i * 256, j * 256))
                except Exception:
                    pass
    # crop so the coordinate sits at the center
    cx = px - x0 * 256
    cy = py - y0 * 256
    left = int(cx - size / 2)
    top = int(cy - size / 2)
    mp = canvas.crop((left, top, left + size, top + size))

    # draw a blue teardrop pin at center
    d = ImageDraw.Draw(mp)
    cx2, cy2 = size / 2, size / 2
    r = max(8, size * 0.055)
    blue = (37, 116, 232)
    d.ellipse([cx2 - r, cy2 - 2 * r, cx2 + r, cy2], fill=blue, outline=(255, 255, 255), width=max(2, int(r * 0.15)))
    d.polygon([(cx2 - r * 0.75, cy2 - r * 0.7), (cx2 + r * 0.75, cy2 - r * 0.7), (cx2, cy2 + r * 0.5)], fill=blue)
    d.ellipse([cx2 - r * 0.35, cy2 - r * 1.35, cx2 + r * 0.35, cy2 - r * 0.65], fill=(255, 255, 255))

    # attribution + thin border
    afont = ImageFont.truetype(FONT_REG, max(10, int(size * 0.035)))
    txt = "© OpenStreetMap"
    tb = d.textbbox((0, 0), txt, font=afont)
    d.rectangle([size - (tb[2] - tb[0]) - 8, size - (tb[3] - tb[1]) - 8, size, size], fill=(255, 255, 255))
    d.text((size - (tb[2] - tb[0]) - 4, size - (tb[3] - tb[1]) - 6), txt, fill=(90, 90, 90), font=afont)
    d.rectangle([0, 0, size - 1, size - 1], outline=(200, 200, 200), width=2)
    return mp


# --------------------------------------------------------------------------
# Compositing
# --------------------------------------------------------------------------
def wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textbbox((0, 0), t, font=font)[2] <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render(path, out_path):
    gps = get_gps(path)
    if not gps:
        print(f"  ! no GPS, skipping: {path}")
        return False
    lat, lon = gps
    title, address = reverse_geocode(lat, lon)
    coords = f"Lat: {lat:.6f}°  Long: {lon:.6f}°"

    img = Image.open(path).convert("RGB")
    W, H = img.size
    m = int(W * MARGIN_F)
    S = int(H * MAP_F)
    title_f = ImageFont.truetype(FONT_BOLD, int(H * TITLE_F))
    body_f = ImageFont.truetype(FONT_REG, int(H * BODY_F))
    gap = int(H * GAP_F)

    tx = m + S + int(m * 1.1)          # text left
    text_w = W - tx - m                 # available text width

    draw0 = ImageDraw.Draw(img)
    lines = [(title, title_f)]
    for ln in wrap(draw0, address, body_f, text_w):
        lines.append((ln, body_f))
    lines.append((coords, body_f))

    # total text height -> banner height
    def lh(f):
        return f.getbbox("Ag")[3] - f.getbbox("Ag")[1]
    text_h = sum(lh(f) + gap for _, f in lines) - gap
    banner_h = max(S, text_h) + 2 * m
    banner_top = H - banner_h

    # gradient (transparent -> dark) over the banner
    grad = Image.new("L", (1, banner_h), 0)
    for y in range(banner_h):
        grad.putpixel((0, y), int(215 * (y / banner_h) ** 0.7))
    grad = grad.resize((W, banner_h))
    shade = Image.new("RGB", (W, banner_h), (0, 0, 0))
    img.paste(shade, (0, banner_top), grad)

    # map
    mp = make_map(lat, lon, S)
    img.paste(mp, (m, H - m - S))

    # text
    draw = ImageDraw.Draw(img)
    y = banner_top + (banner_h - text_h) // 2
    for txt, f in lines:
        draw.text((tx, y), txt, fill=(255, 255, 255), font=f)
        y += lh(f) + gap

    img.save(out_path, quality=92)
    print(f"  ✓ {os.path.basename(out_path)}  ->  {title}")
    return True


def main():
    args = sys.argv[1:]
    files = args or sorted(
        f for f in os.listdir(".")
        if f.lower().endswith(".jpg") and "geotagged" not in f
    )
    os.makedirs(OUT_DIR, exist_ok=True)
    ok = 0
    for f in files:
        print(f"[{f}]")
        try:
            if render(f, os.path.join(OUT_DIR, os.path.basename(f))):
                ok += 1
        except Exception as e:
            print(f"  ! error: {e}")
    print(f"\nDone: {ok}/{len(files)} images written to {OUT_DIR}/")


if __name__ == "__main__":
    main()
