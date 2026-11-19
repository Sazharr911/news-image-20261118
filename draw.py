#!/usr/bin/env python3
"""
THE WORLD IN A DAY -- build-time drawing program (rewritten, round 1).

Paints the one-page broadsheet that sums up the world news of
Wednesday 18 November 2026. Build time only: it needs Pillow and the
DejaVu fonts, runs on the builder's machine, and writes entry.png
next to this file. The competition server never runs it -- the
submitted main.py is a stdlib-only copier that ships the finished
PNG to the output path. Regenerate with:

    python3 draw.py   # writes entry.png next to this file

Deterministic by construction: fixed geometry, no randomness, no
clock, no network, so two runs give a byte-identical PNG.

This file is the table-driven rewrite of the first draft. Panels,
flags and map shapes are described by data -- tuples, compact
strings and small lookup tables -- and painted by one generic
renderer plus a handful of tiny scene painters, instead of one
hand-written block per panel. The picture it produces is the same
broadsheet: a giant-date masthead, three large illustrated panels,
ten numbered mini-panels with their own drawings, the Voyager
strip, a world map with numbered pins, and the "ALSO ON WEDNESDAY
18 NOVEMBER" list. 43 stories in all; the researched story list
with source notes lives in STORIES.md.
"""

import math, os

from PIL import Image
from PIL import ImageDraw, ImageFont

PAGE = 1024
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "entry.png")

FONTS = "/usr/share/fonts/truetype/dejavu"
SERIF_B = os.path.join(FONTS, "DejaVuSerif-Bold.ttf")
SANS_B = os.path.join(FONTS, "DejaVuSans-Bold.ttf")
SANS = os.path.join(FONTS, "DejaVuSans.ttf")


def _hex(code):
    """Six hex digits (no '#') -> an (r, g, b) tuple."""
    return (int(code[0:2], 16), int(code[2:4], 16), int(code[4:6], 16))


PAPER = _hex("f7f3e7")
INK = _hex("141820")
CRIMSON = _hex("b21818")
NAVY = _hex("18345c")
SKY = _hex("c7deee")
SEA = _hex("3a6ea0")
SAND = _hex("eee2c4")
LAND = _hex("e9dfc2")
OCEAN = _hex("c6dcec")
GREY = _hex("5a606a")
WHITE = _hex("ffffff")
BLACK = _hex("0a0a0c")
TANGERINE = _hex("e87722")
GOLD = _hex("f5c531")
LEAF = _hex("2ea05a")

REGION = {
    "europe": _hex("2563b3"),
    "mideast": _hex("e07a1a"),
    "asia": _hex("8e44ad"),
    "africa": _hex("228b4c"),
    "americas": _hex("c53054"),
    "oceania": _hex("17968c"),
    "global": _hex("646e7d"),
}

EDGE = 12
SPAN = PAGE - 2 * EDGE


def _corners(box):
    """Unpack a (left, top, right, bottom) box tuple."""
    return box[0], box[1], box[2], box[3]


# ---------------------------------------------------------------------------
# Text plumbing
# ---------------------------------------------------------------------------

def load_font(path, pts):
    return ImageFont.truetype(path, pts)


def shrink_to_width(cnv, text, path, width, start):
    """Biggest size <= start that still fits width on one line."""
    trial_size = start
    while trial_size > 8:
        trial = load_font(path, trial_size)
        if cnv.textlength(text, font=trial) <= width:
            return trial
        trial_size -= 1
    return load_font(path, 8)


def greedy_wrap(cnv, text, fnt, width):
    """Greedy word wrap; every returned line fits width."""
    out = []
    current = []
    words = text.split()
    for word in words:
        cand = " ".join(current + [word])
        if cnv.textlength(cand, font=fnt) <= width:
            current.append(word)
        else:
            if current:
                out.append(" ".join(current))
            current = [word]
    if current:
        out.append(" ".join(current))
    return out


def shrink_to_block(cnv, text, path, width, max_lines, start, floor):
    """Biggest size <= start whose wrap stays within max_lines."""
    trial_size = start
    while trial_size > floor:
        trial = load_font(path, trial_size)
        if len(greedy_wrap(cnv, text, trial, width)) <= max_lines:
            return trial
        trial_size -= 1
    return load_font(path, floor)


def put_mid(cnv, cx, y, text, fnt, fill=INK):
    cnv.text((cx, y), text, font=fnt, fill=fill, anchor="ma")


def put_left(cnv, x, y, text, fnt, fill=INK):
    cnv.text((x, y), text, font=fnt, fill=fill, anchor="la")


def put_right(cnv, x, y, text, fnt, fill=INK):
    cnv.text((x, y), text, font=fnt, fill=fill, anchor="ra")


def paint_lines(cnv, x, y, lines, fnt, leading):
    for ln in lines:
        put_left(cnv, x, y, ln, fnt)
        y += leading
    return y


# ---------------------------------------------------------------------------
# Small reusable marks
# ---------------------------------------------------------------------------

def disc(cnv, cx, cy, radius, number, paint):
    """Numbered circle badge in a region colour."""
    cnv.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                fill=paint)
    fnt = load_font(SANS_B, int(radius * 1.05))
    cnv.text((cx, cy + 1), str(number), font=fnt, fill=WHITE, anchor="mm")


def label(cnv, x, y, text, paint, size=10, fg=WHITE, pad=5):
    """Small filled label, top-left at (x, y); returns its width."""
    fnt = load_font(SANS_B, size)
    w = cnv.textlength(text, font=fnt)
    cnv.rectangle([x, y, x + w + 2 * pad, y + size + 7], fill=paint)
    put_left(cnv, x + pad, y + 3, text, fnt, fill=fg)
    return w + 2 * pad


def label_right(cnv, xr, y, text, paint, size=10):
    """label() right-aligned: the label's right edge sits at xr."""
    fnt = load_font(SANS_B, size)
    w = cnv.textlength(text, font=fnt) + 10
    return label(cnv, xr - w, y, text, paint, size=size)


def star5(cnv, cx, cy, radius, paint):
    """Five-point star polygon."""
    corners = []
    for step in range(10):
        theta = -math.pi / 2 + step * math.pi / 5
        reach = radius if step % 2 == 0 else radius * 0.45
        corners.append((cx + reach * math.cos(theta),
                        cy + reach * math.sin(theta)))
    cnv.polygon(corners, fill=paint)


def flare(cnv, cx, cy, radius, paint=TANGERINE):
    """Explosion starburst."""
    tips = []
    for step in range(16):
        theta = step * math.pi / 8
        reach = radius if step % 2 == 0 else radius * 0.45
        tips.append((cx + reach * math.cos(theta),
                     cy + reach * math.sin(theta)))
    cnv.polygon(tips, fill=paint)


# ---------------------------------------------------------------------------
# Flags, painted into a box with a thin outline.
# ---------------------------------------------------------------------------

def _outline(cnv, box):
    cnv.rectangle(box, outline=INK, width=1)


def _bands_h(cnv, box, paints):
    """Three horizontal bands of equal height (top, middle, bottom)."""
    x0, y0, x1, y1 = _corners(box)
    step = (y1 - y0) // 3
    for i, paint in enumerate(paints):
        top = y0 + i * step
        bottom = y1 if i == 2 else y0 + (i + 1) * step
        cnv.rectangle([x0, top, x1, bottom], fill=paint)


def _bands_v(cnv, box, paints):
    """Three vertical bands of equal width (left, middle, right)."""
    x0, y0, x1, y1 = _corners(box)
    step = (x1 - x0) // 3
    for i, paint in enumerate(paints):
        left = x0 + i * step
        right = x1 if i == 2 else x0 + (i + 1) * step
        cnv.rectangle([left, y0, right, y1], fill=paint)


def flag_us(cnv, box):
    x0, y0, x1, y1 = _corners(box)
    band = (y1 - y0) / 7.0
    for n in range(7):
        if n & 1:
            continue
        cnv.rectangle([x0, y0 + n * band, x1, y0 + (n + 1) * band],
                      fill=_hex("b22234"))
    canton_w = (x1 - x0) * 0.45
    cnv.rectangle([x0, y0, x0 + canton_w, y0 + band * 4], fill=NAVY)
    for row in range(3):
        for col in range(4):
            sx = x0 + 4 + col * (canton_w - 6) / 3
            sy = y0 + 3 + row * (band * 4 - 6) / 2
            cnv.ellipse([sx - 1.6, sy - 1.6, sx + 1.6, sy + 1.6], fill=WHITE)
    _outline(cnv, box)


def flag_cn(cnv, box):
    x0, y0, x1, y1 = _corners(box)
    cnv.rectangle(box, fill=_hex("de2910"))
    mx, my = x0 + (x1 - x0) * 0.22, y0 + (y1 - y0) * 0.28
    star5(cnv, mx, my, (y1 - y0) * 0.22, GOLD)
    small = [(0.42, 0.14), (0.5, 0.3), (0.46, 0.48), (0.32, 0.5)]
    for fx, fy in small:
        star5(cnv, x0 + (x1 - x0) * fx, y0 + (y1 - y0) * fy,
              (y1 - y0) * 0.09, GOLD)
    _outline(cnv, box)


def flag_ru(cnv, box):
    _bands_h(cnv, box, [WHITE, _hex("0039a6"), _hex("d50032")])
    _outline(cnv, box)


def flag_in(cnv, box):
    _bands_h(cnv, box, [_hex("f48c32"), WHITE, _hex("1e8c3c")])
    x0, y0, x1, y1 = _corners(box)
    step = (y1 - y0) // 3
    mx, my = (x0 + x1) // 2, y0 + step + step // 2
    cnv.ellipse([mx - 5, my - 5, mx + 5, my + 5], outline=NAVY, width=2)
    _outline(cnv, box)


def flag_jp(cnv, box):
    x0, y0, x1, y1 = _corners(box)
    cnv.rectangle(box, fill=WHITE)
    mx, my = (x0 + x1) // 2, (y0 + y1) // 2
    rad = (y1 - y0) * 0.3
    cnv.ellipse([mx - rad, my - rad, mx + rad, my + rad], fill=_hex("bc002d"))
    _outline(cnv, box)


def flag_au(cnv, box):
    x0, y0, x1, y1 = _corners(box)
    cnv.rectangle(box, fill=_hex("00236e"))
    half_w, half_h = (x1 - x0) // 2, (y1 - y0) // 2
    cnv.line([(x0, y0 + half_h // 2), (x0 + half_w, y0 + half_h // 2)],
             fill=WHITE, width=4)
    cnv.line([(x0 + half_w // 2, y0), (x0 + half_w // 2, y0 + half_h)],
             fill=WHITE, width=4)
    cnv.line([(x0, y0 + half_h // 2), (x0 + half_w, y0 + half_h // 2)],
             fill=_hex("c81e32"), width=2)
    cnv.line([(x0 + half_w // 2, y0), (x0 + half_w // 2, y0 + half_h)],
             fill=_hex("c81e32"), width=2)
    star5(cnv, x0 + half_w // 2, y0 + half_h + (y1 - y0 - half_h) // 2, 5,
          WHITE)
    for fx, fy in [(0.72, 0.2), (0.8, 0.38), (0.74, 0.55), (0.84, 0.68),
                   (0.68, 0.42)]:
        star5(cnv, x0 + (x1 - x0) * fx, y0 + (y1 - y0) * fy, 3, WHITE)
    _outline(cnv, box)


def flag_mx(cnv, box):
    _bands_v(cnv, box, [_hex("007846"), WHITE, _hex("c81e32")])
    x0, y0, x1, y1 = _corners(box)
    mx, my = (x0 + x1) // 2, (y0 + y1) // 2
    cnv.ellipse([mx - 4, my - 4, mx + 4, my + 4], fill=_hex("8c6428"))
    _outline(cnv, box)


def flag_bo(cnv, box):
    _bands_h(cnv, box, [_hex("d50032"), _hex("fadc00"), _hex("007846")])
    _outline(cnv, box)


def flag_cd(cnv, box):
    x0, y0, x1, y1 = _corners(box)
    cnv.rectangle(box, fill=_hex("5aaae6"))
    cnv.polygon([(x0, y1), (x0 + (x1 - x0) * 0.35, y1), (x1, y0),
                 (x1, y0 + (y1 - y0) * 0.32)], fill=_hex("dc1e2d"))
    star5(cnv, x0 + (x1 - x0) * 0.3, y0 + (y1 - y0) * 0.32,
          (y1 - y0) * 0.26, _hex("fadc00"))
    _outline(cnv, box)


def flag_ph(cnv, box):
    x0, y0, x1, y1 = _corners(box)
    h = y1 - y0
    cnv.rectangle([x0, y0, x1, y0 + h // 2], fill=_hex("0038a8"))
    cnv.rectangle([x0, y0 + h // 2, x1, y1], fill=_hex("ce1126"))
    cnv.polygon([(x0, y0), (x0, y1), (x0 + (x1 - x0) * 0.42, (y0 + y1) // 2)],
                fill=WHITE)
    cnv.ellipse([x0 + (x1 - x0) * 0.14 - 3, (y0 + y1) // 2 - 3,
                 x0 + (x1 - x0) * 0.14 + 3, (y0 + y1) // 2 + 3],
                fill=_hex("fadc00"))
    _outline(cnv, box)


# ---------------------------------------------------------------------------
# Panel illustrations. Each paints inside its box and nothing outside it.
# ---------------------------------------------------------------------------

def scene_shenzhen(cnv, box):
    """1: Shenzhen skyline, three flags, trilateral banner."""
    x0, y0, x1, y1 = _corners(box)
    cnv.rectangle(box, fill=_hex("e8eef6"))
    ground = y1 - 6
    xs = [int(v) for v in "8 34 64 92 122 152 182 212 244 274".split()]
    hs = [int(v) for v in "12 17 14 18 12 16 14 18 12 15".split()]
    for tx, th in zip(xs, hs):
        cnv.rectangle([x0 + tx, ground - th, x0 + tx + 20, ground],
                      fill=_hex("46546e"))
        for wy in range(ground - th + 5, ground - 4, 8):
            cnv.rectangle([x0 + tx + 4, wy, x0 + tx + 8, wy + 3], fill=GOLD)
            cnv.rectangle([x0 + tx + 12, wy, x0 + tx + 16, wy + 3], fill=GOLD)
    cnv.rectangle([x0, ground, x1, y1], fill=_hex("6e4a28"))
    banners = (flag_cn, flag_ru, flag_us)
    names = "CHINA RUSSIA US".split()
    fw, fh = 56, 34
    gap = ((x1 - x0) - 3 * fw) // 4
    fy = y0 + 4
    for pos, (fn, nm) in enumerate(zip(banners, names)):
        fx = x0 + gap + pos * (fw + gap)
        cnv.line([(fx + fw // 2, fy), (fx + fw // 2, fy - 2)], fill=INK,
                 width=1)
        fn(cnv, (fx, fy, fx + fw, fy + fh))
        put_mid(cnv, fx + fw // 2, fy + fh + 2, nm, load_font(SANS_B, 8),
                fill=INK)
    label(cnv, x0 + 5, y1 - 18, "TRILATERAL THURSDAY", NAVY, size=9)


def scene_gulf(cnv, box):
    """2: simplified Gulf map -- Iran, Qeshm, Bahrain, Kuwait."""
    x0, y0, x1, y1 = _corners(box)
    w, h = x1 - x0, y1 - y0
    cnv.rectangle(box, fill=SAND)
    sea_pts = []
    for pair in ("0.40,0.0;0.52,0.0;0.55,0.18;0.50,0.34;0.56,0.48;0.68,0.55;"
                 "0.80,0.60;0.92,0.58;1.0,0.66;1.0,0.86;0.88,0.92;0.76,0.80;"
                 "0.64,0.84;0.58,1.0;0.50,1.0;0.52,0.82;0.44,0.66;0.38,0.48;"
                 "0.40,0.28").split(";"):
        u, v = pair.split(",")
        sea_pts.append((float(u), float(v)))
    cnv.polygon([(x0 + u * w, y0 + v * h) for u, v in sea_pts], fill=SEA)
    fnt = load_font(SANS_B, 10)
    put_mid(cnv, x0 + w * 0.24, y0 + 4, "I R A N", fnt, fill=INK)
    small = load_font(SANS_B, 9)
    put_left(cnv, x0 + 5, y0 + h * 0.52, "BAHRAIN", small, fill=INK)
    put_left(cnv, x0 + 4, y0 + h * 0.8, "KUWAIT", small, fill=GREY)
    put_right(cnv, x1 - 5, y0 + h * 0.3, "QESHM", small, fill=INK)
    put_right(cnv, x1 - 5, y0 + h * 0.66, "HORMUZ", small, fill=WHITE)
    bx, by = x0 + w * 0.42, y0 + h * 0.44
    for t in range(0, 11):
        px = x0 + w * (0.62 - 0.02 * t)
        py = y0 + h * (0.1 + 0.031 * t) + (t % 2) * 2
        cnv.ellipse([px - 1.5, py - 1.5, px + 1.5, py + 1.5], fill=CRIMSON)
    cnv.line([(bx - 6, by - 6), (bx + 6, by + 6)], fill=CRIMSON, width=3)
    cnv.line([(bx - 6, by + 6), (bx + 6, by - 6)], fill=CRIMSON, width=3)
    label(cnv, x0 + 6, y0 + 6, "DRONES DOWNED", _hex("b21818"), size=9)
    flare(cnv, x0 + w * 0.84, y0 + h * 0.52, 11)
    label(cnv, x0 + w * 0.60, y1 - 16, "US STRIKES", NAVY, size=9)


def scene_bridge(cnv, box):
    """3: Kerch Bridge -- intact span, burst, collapsed span, strait."""
    x0, y0, x1, y1 = _corners(box)
    water = y0 + int((y1 - y0) * 0.55)
    cnv.rectangle([x0, y0, x1, water], fill=SKY)
    cnv.rectangle([x0, water, x1, y1], fill=SEA)
    deck = y0 + int((y1 - y0) * 0.5)
    top = y0 + 3
    for base in (52, 128):
        px = x0 + base
        cnv.line([(px, top), (px, deck + 12)], fill=INK, width=5)
    cnv.line([(x0 + 52, top), (x0 + 128, top)], fill=INK, width=2)
    cnv.line([(x0 + 2, deck), (x0 + 52, top)], fill=INK, width=2)
    for base in (52, 128):
        for off in (24, 48, 72):
            cnv.line([(x0 + base + off, top + off // 8),
                      (x0 + base + off, deck)], fill=INK, width=1)
    cnv.line([(x0 + 2, deck), (x0 + 205, deck)], fill=INK, width=7)
    flare(cnv, x0 + 216, deck - 2, 15)
    cnv.line([(x0 + 210, deck + 1), (x0 + 268, y1 - 8)], fill=INK, width=7)
    cnv.line([(x0 + 282, y1 - 14), (x0 + 322, y1 - 20)], fill=INK, width=6)
    cnv.polygon([(x1 - 34, deck - 4), (x1 - 22, deck), (x1 - 34, deck + 4)],
                fill=INK)
    cnv.line([(x1 - 34, deck), (x1 - 2, deck)], fill=INK, width=7)
    for px, py, pr in [(222, 12, 9), (236, 8, 12), (252, 12, 8)]:
        cnv.ellipse([x0 + px - pr, y0 + py - pr // 2,
                     x0 + px + pr, y0 + py + pr // 2], fill=_hex("787c82"))
    for wx in range(x0 + 14, x1 - 24, 44):
        cnv.arc([wx, y1 - 9, wx + 20, y1 - 1], start=180, end=360,
                fill=WHITE, width=2)
    fnt = load_font(SANS_B, 9)
    put_left(cnv, x0 + 5, y0 + 3, "CRIMEA", fnt, fill=INK)
    put_right(cnv, x1 - 5, y0 + 3, "RUSSIA", fnt, fill=INK)
    label(cnv, x0 + 5, y1 - 18, "3RD HIT IN A WEEK", _hex("b21818"), size=9)


def scene_senate(cnv, box):
    """4: Senate semicircle -- 56 blue vs 44 red, Alaska star."""
    x0, y0, x1, y1 = _corners(box)
    cnv.rectangle(box, fill=_hex("f3eee0"))
    mx, my, rad = (x0 + x1) // 2, y1 - 12, 20
    outer = 25
    for i in range(outer):
        theta = math.pi + i * math.pi / (outer - 1)
        px, py = mx + rad * math.cos(theta), my + rad * math.sin(theta)
        paint = REGION["europe"] if i < 14 else _hex("c82837")
        cnv.ellipse([px - 3.4, py - 3.4, px + 3.4, py + 3.4], fill=paint)
    inner_r = rad - 8
    for i in range(outer - 4):
        theta = math.pi + i * math.pi / (outer - 5)
        px, py = mx + inner_r * math.cos(theta), my + inner_r * math.sin(theta)
        paint = REGION["europe"] if i < 11 else _hex("c82837")
        cnv.ellipse([px - 3, py - 3, px + 3, py + 3], fill=paint)
    label(cnv, x0 + 4, y0 + 3, "DEMOCRATS 56", REGION["europe"], size=9)
    label_right(cnv, x1 - 5, y0 + 3, "REPUBLICANS 44", _hex("c82837"), size=9)
    put_mid(cnv, mx, y1 - 11, "PELTOLA WINS ALASKA", load_font(SANS_B, 8.5),
            fill=INK)


def scene_measles(cnv, box):
    """5: three flags over a revoked-status banner."""
    x0, y0, x1, y1 = _corners(box)
    cnv.rectangle(box, fill=_hex("f6f0e8"))
    banners = (flag_us, flag_mx, flag_bo)
    names = "US MEXICO BOLIVIA".split()
    fw, fh = 46, 22
    gap = (x1 - x0 - 3 * fw) // 4
    for pos, (fn, nm) in enumerate(zip(banners, names)):
        fx = x0 + gap + pos * (fw + gap)
        fn(cnv, (fx, y0 + 2, fx + fw, y0 + 2 + fh))
        put_mid(cnv, fx + fw // 2, y0 + 4 + fh, nm, load_font(SANS_B, 7),
                fill=INK)
    band_y = y1 - 13
    cnv.rectangle([x0 + 4, band_y, x1 - 4, y1 - 2], fill=_hex("b21818"))
    put_mid(cnv, (x0 + x1) // 2, band_y + 2, "MEASLES-FREE STATUS REVOKED",
            load_font(SANS_B, 9), fill=WHITE)


def scene_ebola(cnv, box):
    """6: Ebola -- red cross, virus, case-count tag."""
    x0, y0, x1, y1 = _corners(box)
    cnv.rectangle(box, fill=_hex("e9f4ec"))
    mid_y = (y0 + y1) // 2
    cross_x = x0 + 14
    cnv.rectangle([cross_x, mid_y - 15, cross_x + 34, mid_y + 15],
                  fill=WHITE, outline=INK)
    cnv.rectangle([cross_x + 13, mid_y - 10, cross_x + 21, mid_y + 10],
                  fill=_hex("c81e28"))
    cnv.rectangle([cross_x + 7, mid_y - 4, cross_x + 27, mid_y + 4],
                  fill=_hex("c81e28"))
    vx, vy = x0 + 86, mid_y
    for deg in range(0, 360, 30):
        ex = vx + 15 * math.cos(math.radians(deg))
        ey = vy + 15 * math.sin(math.radians(deg))
        cnv.line([(vx, vy), (ex, ey)], fill=_hex("962878"), width=3)
        cnv.ellipse([ex - 3, ey - 3, ex + 3, ey + 3], fill=_hex("962878"))
    cnv.ellipse([vx - 11, vy - 11, vx + 11, vy + 11], fill=_hex("aa3c8c"))
    label_right(cnv, x1 - 5, mid_y - 9, "11,000+ CASES", _hex("141820"),
                size=9.5)
    flag_cd(cnv, (x0 + 118, y0 + 36, x0 + 152, y0 + 48))


def scene_cop(cnv, box):
    """7: COP31 -- globe, draft document, thermometer."""
    x0, y0, x1, y1 = _corners(box)
    cnv.rectangle(box, fill=_hex("ebf2f6"))
    mid_y = (y0 + y1) // 2
    globe_x, globe_r = x0 + 30, 17
    cnv.ellipse([globe_x - globe_r, mid_y - globe_r,
                 globe_x + globe_r, mid_y + globe_r], fill=_hex("78b4dc"),
                outline=NAVY, width=2)
    cnv.ellipse([globe_x - 7, mid_y - globe_r, globe_x + 7, mid_y + globe_r],
                outline=NAVY, width=1)
    cnv.line([(globe_x - globe_r, mid_y), (globe_x + globe_r, mid_y)],
             fill=NAVY, width=1)
    cnv.pieslice([globe_x - globe_r, mid_y - globe_r, globe_x + 2, mid_y + 6],
                 start=90, end=230, fill=LEAF)
    doc_x = x0 + 58
    cnv.rectangle([doc_x, y0 + 5, doc_x + 84, y1 - 5], fill=WHITE, outline=INK)
    put_left(cnv, doc_x + 5, y0 + 8, "DRAFT", load_font(SANS_B, 8), fill=INK)
    put_left(cnv, doc_x + 5, y0 + 18, "PHASE OUT", load_font(SANS_B, 8.5),
             fill=CRIMSON)
    put_left(cnv, doc_x + 5, y0 + 28, "FOSSIL FUELS?", load_font(SANS_B, 8.5),
             fill=CRIMSON)
    for rule_y in (y0 + 40, y0 + 45):
        cnv.line([(doc_x + 5, rule_y), (doc_x + 76, rule_y)], fill=GREY,
                 width=1)
    therm_x = x1 - 18
    cnv.rectangle([therm_x - 3, y0 + 6, therm_x + 3, y1 - 12], fill=WHITE,
                  outline=INK)
    cnv.rectangle([therm_x - 3, y0 + 24, therm_x + 3, y1 - 12],
                  fill=_hex("d22828"))
    cnv.ellipse([therm_x - 7, y1 - 16, therm_x + 7, y1 - 2],
                fill=_hex("d22828"))


def scene_gaza(cnv, box):
    """8: Gaza winter -- tents, the Yellow Line, flood tag."""
    x0, y0, x1, y1 = _corners(box)
    cnv.rectangle(box, fill=_hex("f0ece0"))
    ground = y1 - 8
    for tent_x in (x0 + 16, x0 + 62):
        cnv.polygon([(tent_x, ground), (tent_x + 20, y0 + 10),
                     (tent_x + 40, ground)], fill=_hex("c4b296"), outline=INK)
        cnv.polygon([(tent_x + 15, ground), (tent_x + 20, y0 + 24),
                     (tent_x + 25, ground)], fill=_hex("5a5042"))
    cnv.line([(x0 + 110, y0 + 4), (x0 + 110, y1 - 2)], fill=GOLD, width=4)
    cnv.line([(x0 + 110, y0 + 4), (x0 + 110, y1 - 2)], fill=INK, width=1)
    aid_x = x0 + 128
    cnv.rectangle([aid_x, ground - 22, aid_x + 30, ground], fill=WHITE,
                  outline=INK)
    cnv.rectangle([aid_x + 12, ground - 18, aid_x + 18, ground - 4],
                  fill=_hex("c81e28"))
    cnv.rectangle([aid_x + 8, ground - 14, aid_x + 22, ground - 8],
                  fill=_hex("c81e28"))
    label_right(cnv, x1 - 5, y0 + 3, "950,000 AT RISK", _hex("961e1e"),
                size=8.5)


def scene_nvidia(cnv, box):
    """9: rising bars on black, the big figure."""
    x0, y0, x1, y1 = _corners(box)
    cnv.rectangle(box, fill=BLACK)
    floor_y = y1 - 8
    heights = [int(v) for v in "10 16 13 24 33".split()]
    for i, bh in enumerate(heights):
        bar_x = x0 + 10 + i * 15
        cnv.rectangle([bar_x, floor_y - bh, bar_x + 10, floor_y],
                      fill=_hex("5ac85a"))
    put_left(cnv, x0 + 92, y0 + 4, "$115.8BN", load_font(SANS_B, 19),
             fill=_hex("5adc6e"))
    put_left(cnv, x0 + 93, y0 + 28, "SALES X2", load_font(SANS_B, 11),
             fill=_hex("f0dc6e"))


def scene_anthropic(cnv, box):
    """10: record offering -- rising line chart, big figure."""
    x0, y0, x1, y1 = _corners(box)
    cnv.rectangle(box, fill=_hex("eeecfa"))
    steps = [(8, -14), (40, -26), (66, -20), (96, -34), (124, -30),
             (156, -44), (182, -46)]
    pts = [(x0 + dx, y1 + dy) for dx, dy in steps]
    cnv.line(pts, fill=REGION["asia"], width=3)
    cnv.ellipse([pts[-1][0] - 4, pts[-1][1] - 4,
                 pts[-1][0] + 4, pts[-1][1] + 4], fill=CRIMSON)
    put_left(cnv, x0 + 8, y0 + 4, "$81.3BN", load_font(SANS_B, 19),
             fill=REGION["asia"])
    put_left(cnv, x0 + 9, y0 + 28, "RECORD OFFERING", load_font(SANS_B, 10),
             fill=GREY)


def scene_quad(cnv, box):
    """11: Quad summit -- banner, four flags, names (mini-panel size)."""
    x0, y0, x1, y1 = _corners(box)
    cnv.rectangle(box, fill=_hex("f3eee0"))
    cnv.rectangle([x0, y0, x1, y0 + 13], fill=_hex("583ca0"))
    put_mid(cnv, (x0 + x1) // 2, y0 + 2, "QUAD SUMMIT · MANILA",
            load_font(SANS_B, 10), fill=WHITE)
    banners = (flag_us, flag_in, flag_jp, flag_au)
    names = "US INDIA JAPAN AUSTRALIA".split()
    fw, fh = 40, 22
    gap = ((x1 - x0) - 4 * fw) // 5
    fy = y0 + 16
    for pos, (fn, nm) in enumerate(zip(banners, names)):
        fx = x0 + gap + pos * (fw + gap)
        fn(cnv, (fx, fy, fx + fw, fy + fh))
        put_mid(cnv, fx + fw // 2, fy + fh + 1, nm, load_font(SANS_B, 7),
                fill=INK)


def scene_eu_loan(cnv, box):
    """12: EU stars circle around the EUR 45bn figure."""
    x0, y0, x1, y1 = _corners(box)
    cnv.rectangle(box, fill=_hex("e8eef8"))
    mx, my = x0 + 42, (y0 + y1) // 2
    cnv.ellipse([mx - 24, my - 24, mx + 24, my + 24], fill=_hex("003399"))
    for i in range(12):
        theta = -math.pi / 2 + i * math.pi / 6
        px = mx + 16 * math.cos(theta)
        py = my + 16 * math.sin(theta)
        star5(cnv, px, py, 3, GOLD)
    put_left(cnv, x0 + 76, y0 + 4, "€45BN", load_font(SANS_B, 21), fill=NAVY)
    put_left(cnv, x0 + 77, y0 + 28, "LOAN FOR", load_font(SANS_B, 10),
             fill=GREY)
    put_left(cnv, x0 + 77, y0 + 39, "UKRAINE", load_font(SANS_B, 10),
             fill=GREY)


def scene_cyclone(cnv, box):
    """13: Category 5 cyclone -- spiral over the Cook Islands."""
    x0, y0, x1, y1 = _corners(box)
    cnv.rectangle(box, fill=_hex("d6e6f2"))
    mx, my = x0 + 70, (y0 + y1) // 2
    for rad, paint in [(24, _hex("78aadc")), (17, _hex("5a96cd")),
                       (10, _hex("3c78be"))]:
        cnv.arc([mx - rad, my - rad, mx + rad, my + rad], start=20, end=300,
                fill=paint, width=4)
    cnv.ellipse([mx - 6, my - 6, mx + 6, my + 6], fill=WHITE, outline=INK)
    cnv.ellipse([mx + 30, y1 - 20, mx + 56, y1 - 12], fill=LEAF, outline=INK)
    put_mid(cnv, mx + 43, y1 - 11, "COOK IS.", load_font(SANS_B, 7), fill=INK)
    label_right(cnv, x1 - 5, y0 + 4, "CATEGORY 5", _hex("b21818"), size=10)
    label_right(cnv, x1 - 5, y0 + 20, "XAVIER", _hex("141820"), size=10)


def scene_voyager(cnv, box):
    """14: Voyager probe, its signal crawling toward a small Earth."""
    x0, y0, x1, y1 = _corners(box)
    cnv.rectangle(box, fill=_hex("0e142c"))
    for px, py in [(18, 10), (52, 44), (88, 8), (140, 50), (176, 14),
                   (200, 40), (30, 56), (120, 58)]:
        cnv.ellipse([x0 + px, y0 + py, x0 + px + 2, y0 + py + 2], fill=WHITE)
    mid_y = (y0 + y1) // 2
    cnv.pieslice([x0 + 8, mid_y - 20, x0 + 48, mid_y + 20], start=90, end=270,
                 fill=_hex("dce0e6"))
    cnv.rectangle([x0 + 42, mid_y - 6, x0 + 62, mid_y + 6], fill=_hex("aab0ba"))
    cnv.line([(x0 + 62, mid_y), (x0 + 118, mid_y - 14)], fill=_hex("aab0ba"),
             width=3)
    cnv.ellipse([x0 + 114, mid_y - 17, x0 + 122, mid_y - 9], fill=GOLD)
    for rad in (12, 20, 28):
        cnv.arc([x0 + 128 - rad // 2, mid_y - rad, x0 + 128 + rad, mid_y + rad],
                start=300, end=60, fill=_hex("78c8fa"), width=2)
    earth_x = x1 - 22
    cnv.ellipse([earth_x - 11, mid_y - 11, earth_x + 11, mid_y + 11],
                fill=_hex("468cdc"))
    cnv.pieslice([earth_x - 11, mid_y - 11, earth_x + 3, mid_y + 8],
                 start=60, end=200, fill=LEAF)
    put_mid(cnv, (x0 + x1) // 2, y1 - 13, "ONE LIGHT-DAY",
            load_font(SANS_B, 9), fill=WHITE)


# ---------------------------------------------------------------------------
# World map (simplified equirectangular continents) with numbered pins.
# Coastlines are stored as compact "lon,lat;lon,lat;..." strings and
# parsed once at import; pins are "num,lon,lat,dx,dy" rows the same way.
# ---------------------------------------------------------------------------

def _parse_poly(raw):
    pts = []
    for pair in raw.split(";"):
        lon_s, lat_s = pair.split(",")
        pts.append((int(lon_s), int(lat_s)))
    return pts


NAM_RAW = "-168,65;-158,71;-140,70;-130,71;-120,71;-110,68;-100,69;-95,69;-90,69;-85,66;-82,66;-79,62;-76,60;-70,62;-65,60;-60,55;-55,52;-56,50;-60,46;-65,44;-68,44;-70,42;-74,39;-76,35;-79,33;-80,31;-80,27;-81,25;-82,27;-84,29;-87,30;-89,29;-94,29;-97,28;-97,25;-97,22;-94,17;-90,14;-87,13;-83,9;-79,9;-81,12;-85,15;-90,14;-94,16;-97,16;-102,19;-105,23;-108,25;-111,29;-114,31;-117,33;-120,34;-122,37;-123,40;-124,45;-124,48;-128,52;-132,55;-137,58;-145,60;-152,59;-156,58;-161,59;-165,60;-168,63"
GREENLAND_RAW = "-46,59;-40,63;-32,68;-22,70;-20,73;-25,78;-32,80;-45,80;-55,78;-58,75;-57,70;-55,65;-53,61"
SAM_RAW = "-78,7;-75,10;-72,12;-68,11;-64,10;-61,9;-57,7;-54,6;-51,4;-50,1;-46,-1;-42,-3;-38,-5;-35,-8;-36,-10;-38,-13;-39,-18;-40,-21;-42,-23;-45,-24;-48,-26;-50,-29;-52,-32;-54,-34;-57,-37;-58,-39;-61,-39;-62,-41;-63,-43;-65,-45;-66,-47;-67,-49;-68,-51;-68,-53;-70,-54;-72,-54;-73,-51;-74,-48;-74,-44;-73,-40;-73,-36;-72,-31;-71,-27;-70,-22;-70,-18;-72,-16;-75,-14;-77,-11;-79,-8;-80,-5;-81,-3;-80,0;-79,2;-78,4"
EUROPE_RAW = "-9,37;-9,43;-8,44;-4,44;-1,45;-2,47;-4,48;-1,50;1,51;3,52;5,53;7,54;8,55;7,57;8,58;10,59;7,59;5,60;5,62;8,63;11,65;14,67;17,69;21,70;26,71;31,71;38,69;44,68;48,66;50,64;48,62;44,60;42,58;40,56;38,55;35,55;33,54;31,52;30,51;28,50;27,48;29,46;28,45;29,43;28,41;27,40;26,39;27,38;26,37;24,37;23,36;22,37;21,38;20,39;19,40;16,39;15,38;12,38;13,41;12,43;10,44;7,44;3,43;0,40;-1,38;-2,37"
ITALY_RAW = "8,44;10,44;11,43;13,41;14,40;16,38;18,40;16,40;14,41;12,42;10,43;8,44"
UK_RAW = "-5,50;-3,50;-2,52;-3,55;-4,57;-3,58;-4,59;-6,58;-8,55;-6,54;-5,52"
IRELAND_RAW = "-10,52;-8,52;-6,52;-6,54;-8,55;-10,54"
AFRICA_RAW = "-6,35;-2,35;3,37;9,37;11,34;15,32;20,32;25,32;30,31;32,31;33,28;35,24;37,22;39,20;40,18;42,15;43,12;45,11;48,11;51,11;48,9;46,6;43,3;41,-1;40,-5;40,-9;39,-13;38,-17;37,-20;36,-23;35,-26;33,-28;31,-30;29,-32;27,-34;25,-34;22,-35;20,-35;19,-33;18,-31;17,-28;16,-24;15,-21;14,-18;13,-14;12,-11;11,-7;10,-4;9,-1;9,2;8,4;6,4;3,6;-1,5;-4,5;-7,4;-9,4;-12,7;-14,9;-16,12;-17,15;-17,18;-16,21;-16,24;-15,27;-14,29;-11,31;-8,33"
MADAGASCAR_RAW = "44,-12;47,-13;49,-15;50,-17;48,-20;46,-23;45,-25;44,-23;43,-20;43,-16"
ASIA_RAW = "26,41;28,41;30,42;31,44;30,46;31,48;30,50;32,52;34,54;36,55;39,55;42,57;44,59;46,62;48,64;50,66;55,68;62,69;68,70;73,71;78,72;84,73;90,74;96,76;102,77;108,77;113,74;118,73;124,72;130,71;136,71;142,72;148,71;154,70;160,69;166,67;172,66;178,65;173,62;168,61;163,60;159,57;157,53;156,51;153,49;150,46;145,45;142,43;141,41;139,39;137,36;134,35;131,34;129,33;126,31;123,30;121,28;120,26;119,24;116,23;112,22;109,20;108,17;107,14;106,10;104,7;102,6;100,7;99,10;98,13;97,15;95,16;93,17;91,16;90,19;89,21;88,22;86,20;84,19;82,16;80,14;78,9;77,8;76,10;75,13;73,16;72,19;70,21;68,23;66,25;63,25;60,25;57,26;55,25;53,26;51,28;50,29;49,30;48,29;50,27;52,25;54,24;56,24;58,23;59,22;57,21;55,20;53,18;51,16;49,14;47,13;45,12;43,13;42,15;41,17;40,20;39,22;37,24;35,28;34,31;34,34;36,36;35,37;33,36;31,36;29,36;27,37;26,38"
JAPAN_RAW = "140,36;141,38;141,40;142,42;143,43;142,45;141,44;140,41;139,38;138,36"
JAPAN2_RAW = "131,32;132,33;134,34;135,35;133,34;131,33"
BORNEO_RAW = "109,1;113,3;117,5;119,2;118,-1;115,-3;111,-3;109,-1"
SUMATRA_RAW = "95,5;99,3;103,-1;105,-4;106,-6;103,-4;99,0;96,3"
JAVA_RAW = "106,-6;110,-7;113,-7;114,-8;110,-8;106,-7"
SULAWESI_RAW = "119,0;121,1;123,0;121,-2;120,-4;119,-2"
NEWGUINEA_RAW = "131,-1;136,-2;141,-3;146,-4;149,-6;150,-8;147,-9;143,-7;138,-5;133,-3"
PHILIPPINES_RAW = "120,18;121,16;122,14;121,13;120,14;120,16"
AUSTRALIA_RAW = "113,-22;112,-25;114,-29;115,-32;115,-34;117,-35;120,-34;124,-33;127,-32;130,-32;132,-32;134,-33;135,-35;137,-36;139,-37;140,-38;143,-38;145,-38;147,-39;149,-38;150,-37;151,-34;153,-31;153,-28;153,-25;152,-23;150,-21;148,-19;146,-18;144,-15;143,-13;142,-11;141,-15;141,-17;140,-19;139,-18;137,-16;136,-15;135,-12;132,-11;130,-12;128,-13;126,-14;124,-16;122,-17;120,-19;118,-20;116,-21"
NZ_RAW = "167,-45;169,-44;171,-43;172,-42;173,-40;174,-39;175,-37;176,-38;175,-40;173,-41;171,-42;169,-44;167,-46"

CONTINENTS = [_parse_poly(raw) for raw in (
    NAM_RAW, GREENLAND_RAW, SAM_RAW, EUROPE_RAW, ITALY_RAW, UK_RAW,
    IRELAND_RAW, AFRICA_RAW, MADAGASCAR_RAW, ASIA_RAW, JAPAN_RAW, JAPAN2_RAW,
    BORNEO_RAW, SUMATRA_RAW, JAVA_RAW, SULAWESI_RAW, NEWGUINEA_RAW,
    PHILIPPINES_RAW, AUSTRALIA_RAW, NZ_RAW)]

# (number, lon, lat, dx, dy) -- dx/dy nudge pins out of tight clusters.
PINS_RAW = "1,114,22,0,-6;2,50,26,4,5;3,37,45,5,-4;4,-150,64,0,0;5,-98,39,0,0;6,23,-2,0,0;7,31,37,-7,3;8,34,31,6,8;9,-122,37,-9,-3;10,-74,41,0,0;11,121,15,0,0;12,4,51,-6,-3;13,-160,-15,0,0"


def _parse_pins(raw):
    rows = []
    for chunk in raw.split(";"):
        num, lon, lat, dx, dy = (int(v) for v in chunk.split(","))
        rows.append((num, lon, lat, dx, dy))
    return rows


PINS = _parse_pins(PINS_RAW)
PIN_SHADE = {1: REGION["asia"], 2: REGION["mideast"], 3: REGION["europe"],
             4: REGION["americas"], 5: REGION["americas"],
             6: REGION["africa"], 7: REGION["global"], 8: REGION["mideast"],
             9: REGION["americas"], 10: REGION["americas"],
             11: REGION["asia"], 12: REGION["europe"],
             13: REGION["oceania"]}


def paint_map(cnv, box):
    x0, y0, x1, y1 = _corners(box)
    cnv.rectangle(box, fill=OCEAN)
    xscale = (x1 - x0) / 360.0
    yscale = (y1 - y0) / 160.0

    def project(lon, lat):
        return (x0 + (lon + 168) * xscale, y0 + (88 - lat) * yscale)

    for poly in CONTINENTS:
        cnv.polygon([project(lon, lat) for lon, lat in poly], fill=LAND)
    for num, lon, lat, dx, dy in PINS:
        px, py = project(lon, lat)
        disc(cnv, px + dx, py + dy, 9, num, PIN_SHADE[num])
    cnv.rectangle(box, outline=INK, width=2)


# ---------------------------------------------------------------------------
# Page content: (number, region key, kicker, scene, headline, deck).
# ---------------------------------------------------------------------------

TOP = [
    (1, "asia", "ASIA · DIPLOMACY", scene_shenzhen,
     "Xi and Putin meet in Shenzhen; trilateral set for Thursday",
     "First Trump–Xi–Putin meeting due at APEC. Xi vows to oppose "
     "protectionism; Putin hits Western sanctions."),
    (2, "mideast", "MIDDLE EAST · IRAN WAR", scene_gulf,
     "US jets strike IRGC site on Qeshm; Iran's drones downed",
     "Iran answers with drones at US sites in Kuwait and Bahrain — "
     "all intercepted, no damage reported."),
    (3, "europe", "EUROPE · UKRAINE WAR", scene_bridge,
     "Ukraine hits Kerch Bridge a third time in a week",
     "A road span collapses into the strait, Kyiv says. Russia "
     "vows to rebuild."),
]

MINI = [
    (4, "americas", "AMERICAS · POLITICS", scene_senate,
     "Peltola wins Alaska; Senate 56–44",
     "Ninth Democratic flip of the midterms, AP projects."),
    (5, "americas", "AMERICAS · HEALTH", scene_measles,
     "US loses measles-free status after 26 years",
     "5,412 cases in 2026, most since 1991; Mexico and Bolivia "
     "lose status too."),
    (6, "africa", "AFRICA · HEALTH", scene_ebola,
     "Ebola in DR Congo tops 11,000 cases",
     "About 5,400 deaths — the second-largest outbreak on record."),
    (7, "global", "GLOBAL · CLIMATE", scene_cop,
     "COP31 deadlocked over fossil-fuel phase-out",
     "Climate check launches in Antalya; the talks close Friday."),
    (8, "mideast", "MIDDLE EAST · GAZA", scene_gaza,
     "Board of Peace faults Israel and Hamas",
     "Tanks cross the Yellow Line; 950,000 displaced in "
     "flood-prone ground."),
    (9, "americas", "AMERICAS · BUSINESS", scene_nvidia,
     "Nvidia's quarterly sales double to $115.8bn",
     "The board will not reinstate ousted CEO Jensen Huang."),
    (10, "americas", "AMERICAS · TECH", scene_anthropic,
     "Anthropic raises $81.3bn, a record",
     "The largest stock offering on record, it says."),
    (11, "asia", "ASIA · DIPLOMACY", scene_quad,
     "Trump holds first Quad summit, in Manila",
     "A Philippines trade deal Manila calls an economic "
     "understanding."),
    (12, "europe", "EUROPE · POLITICS", scene_eu_loan,
     "EU proposes a €45bn loan for Ukraine",
     "Repaid only after Russia pays war reparations, the plan says."),
    (13, "oceania", "OCEANIA · DISASTER", scene_cyclone,
     "Category 5 Cyclone Xavier hits Cook Islands",
     "The Northern Cook Islands take the storm's full force."),
]

ALSO = [
    (15, "europe", "Russia fires 365 drones, missiles at Ukraine grid"),
    (16, "europe", "Russia, Ukraine agree largest prisoner swap"),
    (17, "americas", "Rubio: 'no need' for major Iran combat"),
    (18, "mideast", "Houthis launch five drones at Saudi pipelines"),
    (19, "mideast", "Iran vows 'more crushing' reply; 3rd US carrier in Gulf"),
    (20, "europe", "UK sanctions eight Israeli settlement firms"),
    (21, "mideast", "Kahana elected Knesset speaker 66–52"),
    (22, "africa", "Ethiopia, Eritrea mass forces on border"),
    (23, "europe", "Turkish court bans İmamoğlu from politics"),
    (24, "europe", "Five EU states plan migrant hubs in Rwanda"),
    (25, "europe", "Tens of thousands join French pay protests"),
    (26, "asia", "World Court to rule on Myanmar genocide case"),
    (27, "americas", "Canada, China cut tariffs after Carney–Xi talks"),
    (28, "asia", "EU approves trade deal with Indonesia"),
    (29, "europe", "UK inflation rises to 3.6%"),
    (30, "oceania", "Australian unemployment jumps to 4.9%"),
    (31, "asia", "Japan exports jump 20.5% on chips"),
    (32, "europe", "Equinor hit by cyberattack as gas stays costly"),
    (33, "americas", "Waymo halts driverless freeway rides in California"),
    (34, "americas", "House Democrats nominate Jeffries for Speaker"),
    (35, "americas", "US, Venezuela renew military ties"),
    (36, "americas", "Salvadoran troops raze Haitian gang leader's home"),
    (37, "americas", "Florida pastor convicted in Moïse plot"),
    (38, "americas", "Isolated Awa group emerges in Amazon"),
    (39, "asia", "Bangladesh unrest: clashes, arson, strikes"),
    (40, "mideast", "Iraq resumes oil exports via Turkey, 120,000 b/d"),
    (41, "oceania", "Fiji declares national disaster over drought"),
    (42, "global", "GTA VI launches after a 13-year wait"),
    (43, "europe", "Chelsea beat PSG 1–0; Alcaraz beats Medvedev"),
]


# ---------------------------------------------------------------------------
# Page assembly
# ---------------------------------------------------------------------------

def render_panel(cnv, box, spec, art_h, head_start, deck_size):
    num, region, kicker, scene, headline, deck = spec
    x0, y0, x1, y1 = _corners(box)
    cnv.rectangle(box, outline=INK, width=2)
    art_box = (x0 + 2, y0 + 2, x1 - 2, y0 + 2 + art_h)
    scene(cnv, art_box)
    cnv.line([(x0 + 2, y0 + 2 + art_h), (x1 - 2, y0 + 2 + art_h)],
             fill=INK, width=1)
    inner_w = (x1 - x0) - 16
    kicker_cy = y0 + 2 + art_h + 13
    disc(cnv, x0 + 19, kicker_cy, 10 if art_h > 60 else 9, num,
         REGION[region])
    cnv.text((x0 + 34, kicker_cy), kicker, font=load_font(SANS_B, 12),
             fill=REGION[region], anchor="lm")
    hy = kicker_cy + 11
    hfont = shrink_to_block(cnv, headline, SANS_B, inner_w, 2, head_start, 13)
    lines = greedy_wrap(cnv, headline, hfont, inner_w)
    hy = paint_lines(cnv, x0 + 8, hy, lines, hfont, int(hfont.size * 1.14))
    dfont = shrink_to_block(cnv, deck, SANS, inner_w, 2, deck_size, 9)
    paint_lines(cnv, x0 + 8, hy + 3, greedy_wrap(cnv, deck, dfont, inner_w),
                dfont, int(dfont.size * 1.3))


def compose():
    img = Image.new("RGB", (PAGE, PAGE), PAPER)
    cnv = ImageDraw.Draw(img)

    # ---- masthead ------------------------------------------------------
    put_left(cnv, EDGE, 12, "THE WORLD IN A DAY", load_font(SERIF_B, 23))
    put_right(cnv, PAGE - EDGE, 16,
              "43 STORIES · 6 CONTINENTS · ALL FROM WEDNESDAY",
              load_font(SANS_B, 15))
    date_font = shrink_to_width(cnv, "WEDNESDAY 18 NOVEMBER 2026", SANS_B,
                                SPAN, 68)
    put_mid(cnv, PAGE // 2, 40, "WEDNESDAY 18 NOVEMBER 2026", date_font,
            fill=CRIMSON)
    cnv.line([(EDGE, 112), (PAGE - EDGE, 112)], fill=INK, width=3)
    cnv.line([(EDGE, 118), (PAGE - EDGE, 118)], fill=INK, width=1)

    # ---- top row: three large panels ------------------------------------
    top_y0, top_y1 = 126, 316
    edges = [EDGE + round(i * SPAN / 3) for i in range(4)]
    for i, spec in enumerate(TOP):
        left = edges[i] + (4 if i else 0)
        right = edges[i + 1] - (4 if i < 2 else 0)
        render_panel(cnv, (left, top_y0, right, top_y1), spec, art_h=76,
                     head_start=23, deck_size=12)

    # ---- grid: ten mini panels, five over five ---------------------------
    bands = [(324, 470), (478, 624)]
    edges = [EDGE + round(i * SPAN / 5) for i in range(6)]
    for r, (gy0, gy1) in enumerate(bands):
        for c in range(5):
            spec = MINI[r * 5 + c]
            left = edges[c] + (4 if c else 0)
            right = edges[c + 1] - (4 if c < 4 else 0)
            render_panel(cnv, (left, gy0, right, gy1), spec, art_h=50,
                         head_start=17, deck_size=11)

    # ---- Voyager strip (story 14) ----------------------------------------
    sy0, sy1 = 632, 698
    cnv.rectangle((EDGE, sy0, PAGE - EDGE, sy1), outline=INK, width=2)
    scene_voyager(cnv, (EDGE + 2, sy0 + 2, EDGE + 222, sy1 - 2))
    vx = EDGE + 238
    disc(cnv, vx + 10, sy0 + 17, 10, 14, REGION["global"])
    cnv.text((vx + 27, sy0 + 17), "GLOBAL · SPACE",
             font=load_font(SANS_B, 12), fill=REGION["global"], anchor="lm")
    put_left(cnv, vx, sy0 + 28, "Voyager 1 reaches one light-day from Earth",
             load_font(SANS_B, 20))
    put_left(cnv, vx, sy0 + 52,
             "First human-made object to do so; its signals now take over "
             "a day. (NASA JPL)",
             load_font(SANS, 11.5), fill=GREY)

    # ---- bottom: map + also list ------------------------------------------
    base_y = 708
    put_left(cnv, EDGE, base_y, "WHERE IT HAPPENED", load_font(SANS_B, 14))
    cnv.line([(EDGE, base_y + 20), (EDGE + 430, base_y + 20)], fill=INK,
             width=2)
    paint_map(cnv, (EDGE, base_y + 26, EDGE + 430, base_y + 246))
    legend = [("Europe", "europe"), ("Middle East", "mideast"),
              ("Asia", "asia"), ("Africa", "africa"),
              ("Americas", "americas"), ("Oceania", "oceania"),
              ("Global & space", "global")]
    lx = EDGE
    for name, key in legend[:4]:
        cnv.ellipse([lx, base_y + 254, lx + 8, base_y + 262],
                    fill=REGION[key])
        put_left(cnv, lx + 12, base_y + 252, name, load_font(SANS, 10.5))
        lx += 14 + cnv.textlength(name, font=load_font(SANS, 10.5)) + 12
    lx = EDGE
    for name, key in legend[4:]:
        cnv.ellipse([lx, base_y + 268, lx + 8, base_y + 276],
                    fill=REGION[key])
        put_left(cnv, lx + 12, base_y + 266, name, load_font(SANS, 10.5))
        lx += 14 + cnv.textlength(name, font=load_font(SANS, 10.5)) + 12
    put_left(cnv, lx + 2, base_y + 266, "· Pins 1–13; 14 is in space",
             load_font(SANS, 10.5), fill=GREY)

    list_x = EDGE + 442
    put_left(cnv, list_x, base_y, "ALSO ON WEDNESDAY 18 NOVEMBER",
             load_font(SANS_B, 14))
    cnv.line([(list_x, base_y + 20), (PAGE - EDGE, base_y + 20)], fill=INK,
             width=2)
    col_w = (PAGE - EDGE - list_x - 14) // 2
    halves = [ALSO[:15], ALSO[15:]]
    for ci, items in enumerate(halves):
        col_x = list_x + ci * (col_w + 14)
        iy = base_y + 28
        for num, key, text in items:
            disc(cnv, col_x + 8, iy + 6, 7.5, num, REGION[key])
            fnt = shrink_to_width(cnv, text, SANS, col_w - 22, 10.5)
            put_left(cnv, col_x + 21, iy, text, fnt)
            iy += 16.6

    # ---- footer ------------------------------------------------------------
    cnv.line([(EDGE, 992), (PAGE - EDGE, 992)], fill=INK, width=1)
    put_left(cnv, EDGE, 998,
             "Every story happened or was first reported on Wednesday "
             "18 November 2026; contested claims are marked as claims.",
             load_font(SANS, 9.5), fill=GREY)
    put_right(cnv, PAGE - EDGE, 998,
              "Sources: Reuters, AP, AFP, BBC, WHO, UN, PAHO, NASA JPL.",
              load_font(SANS, 9.5), fill=GREY)

    return img


def main():
    img = compose()
    img.save(OUT, format="PNG")
    print("wrote", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()
