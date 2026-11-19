#!/usr/bin/env python3
"""
THE WORLD IN A DAY -- build-time drawing program (round 1, 18 Nov 2026).

Draws the one-page broadsheet summing up the world news of Wednesday
18 November 2026. Runs at build time only, on a machine with Pillow
and the DejaVu fonts, and writes the finished PNG to entry.png next
to this file. Fully deterministic: fixed geometry, no randomness, no
clock, no network -- two runs produce a byte-identical PNG.

The server never runs this file. The competition's program/v1 runtime
is stdlib-only (no Pillow, no system fonts), so the submitted main.py
is a small stdlib copier that ships the pre-rendered entry.png to the
output path. Regenerate by running:

    python3 draw.py

Requires: Python 3 + Pillow (PIL). Everything else is stdlib.

LAYOUT: the winners' formula -- density, structure and an illustration
for every story. Masthead with the giant date; three large illustrated
panels; ten numbered mini-panels, each with its own drawing, a coloured
region kicker and a headline; a Voyager strip; a world map with numbered
pins ("WHERE IT HAPPENED"); and a numbered "ALSO ON WEDNESDAY
18 NOVEMBER" one-liner list. 43 stories in all. The full story list
with source notes lives in STORIES.md.
"""

import math
import os

from PIL import Image, ImageDraw, ImageFont

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

W = H = 1024
OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "entry.png")

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
F_SERIF_BOLD = os.path.join(FONT_DIR, "DejaVuSerif-Bold.ttf")
F_SANS_BOLD = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")
F_SANS = os.path.join(FONT_DIR, "DejaVuSans.ttf")

PAPER = (247, 243, 231)
INK = (20, 24, 32)
RED = (178, 24, 24)
NAVY = (24, 52, 92)
SKY = (199, 222, 238)
SEA = (58, 110, 160)
SAND = (238, 226, 196)
LAND = (233, 223, 194)
MAPSEA = (198, 220, 236)
GREY = (90, 96, 106)
WHITE = (255, 255, 255)
BLACK = (10, 10, 12)
ORANGE = (232, 119, 34)
YELLOW = (245, 197, 49)
GREEN = (46, 160, 90)

# Region colours: kicker text, number chips and map pins.
EUROPE = (37, 99, 179)
MIDEAST = (224, 122, 26)
ASIA = (142, 68, 173)
AFRICA = (34, 139, 76)
AMERICAS = (197, 48, 84)
OCEANIA = (23, 150, 140)
GLOBALC = (100, 110, 125)

MARGIN = 12
CW = W - 2 * MARGIN  # content width = 1000


# --------------------------------------------------------------------------
# Text helpers
# --------------------------------------------------------------------------

def font(path, size):
    return ImageFont.truetype(path, size)


def fit_font(d, text, path, max_w, start):
    """Largest size <= start at which text fits max_w (single line)."""
    size = start
    while size > 8:
        f = font(path, size)
        if d.textlength(text, font=f) <= max_w:
            return f
        size -= 1
    return font(path, 8)


def wrap(d, text, f, max_w):
    """Greedy word wrap; returns lines that each fit max_w."""
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if d.textlength(trial, font=f) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit_block(d, text, path, max_w, max_lines, start, minimum):
    """Largest font <= start whose wrap fits within max_lines lines."""
    size = start
    while size > minimum:
        f = font(path, size)
        if len(wrap(d, text, f, max_w)) <= max_lines:
            return f
        size -= 1
    return font(path, minimum)


def tc(d, cx, y, text, f, fill=INK):
    d.text((cx, y), text, font=f, fill=fill, anchor="ma")


def tl(d, x, y, text, f, fill=INK):
    d.text((x, y), text, font=f, fill=fill, anchor="la")


def tr(d, x, y, text, f, fill=INK):
    d.text((x, y), text, font=f, fill=fill, anchor="ra")


def block_l(d, x, y, lines, f, lh):
    for ln in lines:
        tl(d, x, y, ln, f)
        y += lh
    return y


def chip(d, cx, cy, r, num, colour):
    """Numbered circle badge in the region colour."""
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=colour)
    f = font(F_SANS_BOLD, int(r * 1.05))
    d.text((cx, cy + 1), str(num), font=f, fill=WHITE, anchor="mm")


def tag(d, x, y, text, fill, size=10, fg=WHITE, pad=5):
    """Small filled label, top-left at (x, y); returns its width."""
    f = font(F_SANS_BOLD, size)
    w = d.textlength(text, font=f)
    d.rectangle([x, y, x + w + 2 * pad, y + size + 7], fill=fill)
    tl(d, x + pad, y + 3, text, f, fill=fg)
    return w + 2 * pad


def tag_r(d, xr, y, text, colour, size=10):
    """tag() right-aligned: the tag's right edge sits at xr."""
    f = font(F_SANS_BOLD, size)
    w = d.textlength(text, font=f) + 10
    return tag(d, xr - w, y, text, colour, size=size)


def star(d, cx, cy, r, fill):
    """Five-point star polygon."""
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    d.polygon(pts, fill=fill)


def burst(d, cx, cy, r, fill=ORANGE):
    """Explosion starburst."""
    pts = []
    for i in range(16):
        ang = i * math.pi / 8
        rad = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    d.polygon(pts, fill=fill)


# --------------------------------------------------------------------------
# Flags (drawn into a rect, with a thin outline)
# --------------------------------------------------------------------------

def _flag_frame(d, box):
    d.rectangle(box, outline=INK, width=1)


def flag_us(d, box):
    x0, y0, x1, y1 = box
    h = y1 - y0
    stripe = h / 7
    for i in range(7):
        if i % 2 == 0:
            d.rectangle([x0, y0 + i * stripe, x1, y0 + (i + 1) * stripe],
                        fill=(178, 34, 52))
    cw = (x1 - x0) * 0.45
    d.rectangle([x0, y0, x0 + cw, y0 + stripe * 4], fill=NAVY)
    for ry in range(3):
        for rx in range(4):
            sx = x0 + 4 + rx * (cw - 6) / 3
            sy = y0 + 3 + ry * (stripe * 4 - 6) / 2
            d.ellipse([sx - 1.6, sy - 1.6, sx + 1.6, sy + 1.6], fill=WHITE)
    _flag_frame(d, box)


def flag_cn(d, box):
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=(222, 41, 16))
    cx, cy = x0 + (x1 - x0) * 0.22, y0 + (y1 - y0) * 0.28
    star(d, cx, cy, (y1 - y0) * 0.22, YELLOW)
    for sx, sy in [(0.42, 0.14), (0.5, 0.3), (0.46, 0.48), (0.32, 0.5)]:
        star(d, x0 + (x1 - x0) * sx, y0 + (y1 - y0) * sy,
             (y1 - y0) * 0.09, YELLOW)
    _flag_frame(d, box)


def flag_ru(d, box):
    x0, y0, x1, y1 = box
    t = (y1 - y0) // 3
    d.rectangle([x0, y0, x1, y0 + t], fill=WHITE)
    d.rectangle([x0, y0 + t, x1, y0 + 2 * t], fill=(0, 57, 166))
    d.rectangle([x0, y0 + 2 * t, x1, y1], fill=(213, 0, 50))
    _flag_frame(d, box)


def flag_in(d, box):
    x0, y0, x1, y1 = box
    t = (y1 - y0) // 3
    d.rectangle([x0, y0, x1, y0 + t], fill=(244, 140, 50))
    d.rectangle([x0, y0 + t, x1, y0 + 2 * t], fill=WHITE)
    d.rectangle([x0, y0 + 2 * t, x1, y1], fill=(30, 140, 60))
    cx, cy = (x0 + x1) // 2, y0 + t + t // 2
    d.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], outline=NAVY, width=2)
    _flag_frame(d, box)


def flag_jp(d, box):
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=WHITE)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    r = (y1 - y0) * 0.3
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(188, 0, 45))
    _flag_frame(d, box)


def flag_au(d, box):
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=(0, 35, 110))
    hw, hh = (x1 - x0) // 2, (y1 - y0) // 2
    d.line([(x0, y0 + hh // 2), (x0 + hw, y0 + hh // 2)], fill=WHITE, width=4)
    d.line([(x0 + hw // 2, y0), (x0 + hw // 2, y0 + hh)], fill=WHITE, width=4)
    d.line([(x0, y0 + hh // 2), (x0 + hw, y0 + hh // 2)], fill=(200, 30, 50),
           width=2)
    d.line([(x0 + hw // 2, y0), (x0 + hw // 2, y0 + hh)], fill=(200, 30, 50),
           width=2)
    star(d, x0 + hw // 2, y0 + hh + (y1 - y0 - hh) // 2, 5, WHITE)
    for sx, sy in [(0.72, 0.2), (0.8, 0.38), (0.74, 0.55), (0.84, 0.68),
                   (0.68, 0.42)]:
        star(d, x0 + (x1 - x0) * sx, y0 + (y1 - y0) * sy, 3, WHITE)
    _flag_frame(d, box)


def flag_mx(d, box):
    x0, y0, x1, y1 = box
    t = (x1 - x0) // 3
    d.rectangle([x0, y0, x0 + t, y1], fill=(0, 120, 70))
    d.rectangle([x0 + t, y0, x0 + 2 * t, y1], fill=WHITE)
    d.rectangle([x0 + 2 * t, y0, x1, y1], fill=(200, 30, 50))
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    d.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=(140, 100, 40))
    _flag_frame(d, box)


def flag_bo(d, box):
    x0, y0, x1, y1 = box
    t = (y1 - y0) // 3
    d.rectangle([x0, y0, x1, y0 + t], fill=(213, 0, 50))
    d.rectangle([x0, y0 + t, x1, y0 + 2 * t], fill=(250, 220, 0))
    d.rectangle([x0, y0 + 2 * t, x1, y1], fill=(0, 120, 70))
    _flag_frame(d, box)


def flag_cd(d, box):
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=(90, 170, 230))
    d.polygon([(x0, y1), (x0 + (x1 - x0) * 0.35, y1), (x1, y0),
               (x1, y0 + (y1 - y0) * 0.32)], fill=(220, 30, 45))
    star(d, x0 + (x1 - x0) * 0.3, y0 + (y1 - y0) * 0.32,
         (y1 - y0) * 0.26, (250, 220, 0))
    _flag_frame(d, box)


def flag_ph(d, box):
    x0, y0, x1, y1 = box
    h = y1 - y0
    d.rectangle([x0, y0, x1, y0 + h // 2], fill=(0, 56, 168))
    d.rectangle([x0, y0 + h // 2, x1, y1], fill=(206, 17, 38))
    d.polygon([(x0, y0), (x0, y1), (x0 + (x1 - x0) * 0.42, (y0 + y1) // 2)],
              fill=WHITE)
    d.ellipse([x0 + (x1 - x0) * 0.14 - 3, (y0 + y1) // 2 - 3,
               x0 + (x1 - x0) * 0.14 + 3, (y0 + y1) // 2 + 3],
              fill=(250, 220, 0))
    _flag_frame(d, box)


# --------------------------------------------------------------------------
# Panel illustrations. Each draws inside its box and nothing outside it.
# --------------------------------------------------------------------------

def art_shenzhen(d, box):
    """1: Shenzhen skyline, three flags, trilateral banner."""
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=(232, 238, 246))
    # skyline silhouettes (kept short so they stay below the flag names)
    gy = y1 - 6
    towers = [(8, 12), (34, 17), (64, 14), (92, 18), (122, 12),
              (152, 16), (182, 14), (212, 18), (244, 12), (274, 15)]
    for tx, th in towers:
        d.rectangle([x0 + tx, gy - th, x0 + tx + 20, gy], fill=(70, 84, 110))
        for wy in range(gy - th + 5, gy - 4, 8):
            d.rectangle([x0 + tx + 4, wy, x0 + tx + 8, wy + 3], fill=YELLOW)
            d.rectangle([x0 + tx + 12, wy, x0 + tx + 16, wy + 3], fill=YELLOW)
    d.rectangle([x0, gy, x1, y1], fill=(110, 74, 40))
    # three flags on poles above the skyline
    flags = [flag_cn, flag_ru, flag_us]
    names = ["CHINA", "RUSSIA", "US"]
    fw, fh = 56, 34
    gap = ((x1 - x0) - 3 * fw) // 4
    fy = y0 + 4
    for i, (fl, nm) in enumerate(zip(flags, names)):
        fx = x0 + gap + i * (fw + gap)
        d.line([(fx + fw // 2, fy), (fx + fw // 2, fy - 2)], fill=INK, width=1)
        fl(d, (fx, fy, fx + fw, fy + fh))
        tc(d, fx + fw // 2, fy + fh + 2, nm, font(F_SANS_BOLD, 8), fill=INK)
    tag(d, x0 + 5, y1 - 18, "TRILATERAL THURSDAY", NAVY, size=9)


def art_gulf(d, box):
    """2: simplified Gulf map -- Iran, Qeshm, Bahrain, Kuwait."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    d.rectangle(box, fill=SAND)
    # the sea: gulf running down from the top, strait at bottom right
    sea = [(0.40, 0.0), (0.52, 0.0), (0.55, 0.18), (0.50, 0.34),
           (0.56, 0.48), (0.68, 0.55), (0.80, 0.60), (0.92, 0.58),
           (1.0, 0.66), (1.0, 0.86), (0.88, 0.92), (0.76, 0.80),
           (0.64, 0.84), (0.58, 1.0), (0.50, 1.0), (0.52, 0.82),
           (0.44, 0.66), (0.38, 0.48), (0.40, 0.28)]
    d.polygon([(x0 + px * w, y0 + py * h) for px, py in sea], fill=SEA)
    f = font(F_SANS_BOLD, 10)
    tc(d, x0 + w * 0.24, y0 + 4, "I R A N", f, fill=INK)
    f9 = font(F_SANS_BOLD, 9)
    tl(d, x0 + 5, y0 + h * 0.52, "BAHRAIN", f9, fill=INK)
    tl(d, x0 + 4, y0 + h * 0.8, "KUWAIT", f9, fill=GREY)
    tr(d, x1 - 5, y0 + h * 0.3, "QESHM", f9, fill=INK)
    tr(d, x1 - 5, y0 + h * 0.66, "HORMUZ", f9, fill=WHITE)
    # drone strike on the Bahrain coast: dotted arc + red X
    bx, by = x0 + w * 0.42, y0 + h * 0.44
    for t in range(0, 11):
        px = x0 + w * (0.62 - 0.02 * t)
        py = y0 + h * (0.1 + 0.031 * t) + (t % 2) * 2
        d.ellipse([px - 1.5, py - 1.5, px + 1.5, py + 1.5], fill=RED)
    d.line([(bx - 6, by - 6), (bx + 6, by + 6)], fill=RED, width=3)
    d.line([(bx - 6, by + 6), (bx + 6, by - 6)], fill=RED, width=3)
    tag(d, x0 + 6, y0 + 6, "DRONES DOWNED", (178, 24, 24), size=9)
    # US strike burst on Qeshm
    burst(d, x0 + w * 0.84, y0 + h * 0.52, 11)
    tag(d, x0 + w * 0.60, y1 - 16, "US STRIKES", NAVY, size=9)


def art_bridge(d, box):
    """3: Kerch Bridge -- intact span, burst, collapsed span, strait."""
    x0, y0, x1, y1 = box
    sea_y = y0 + int((y1 - y0) * 0.55)
    d.rectangle([x0, y0, x1, sea_y], fill=SKY)
    d.rectangle([x0, sea_y, x1, y1], fill=SEA)
    deck_y = y0 + int((y1 - y0) * 0.5)
    top = y0 + 3
    for tx in (x0 + 52, x0 + 128):
        d.line([(tx, top), (tx, deck_y + 12)], fill=INK, width=5)
    d.line([(x0 + 52, top), (x0 + 128, top)], fill=INK, width=2)
    d.line([(x0 + 2, deck_y), (x0 + 52, top)], fill=INK, width=2)
    for tx in (x0 + 52, x0 + 128):
        for off in (24, 48, 72):
            d.line([(tx + off, top + off // 8), (tx + off, deck_y)],
                   fill=INK, width=1)
    # intact deck, burst, collapsed span, far stub
    d.line([(x0 + 2, deck_y), (x0 + 205, deck_y)], fill=INK, width=7)
    burst(d, x0 + 216, deck_y - 2, 15)
    d.line([(x0 + 210, deck_y + 1), (x0 + 268, y1 - 8)], fill=INK, width=7)
    d.line([(x0 + 282, y1 - 14), (x0 + 322, y1 - 20)], fill=INK, width=6)
    d.polygon([(x1 - 34, deck_y - 4), (x1 - 22, deck_y), (x1 - 34, deck_y + 4)],
              fill=INK)
    d.line([(x1 - 34, deck_y), (x1 - 2, deck_y)], fill=INK, width=7)
    # smoke over the break
    for sx, sy, r in [(222, 12, 9), (236, 8, 12), (252, 12, 8)]:
        d.ellipse([x0 + sx - r, y0 + sy - r // 2, x0 + sx + r, y0 + sy + r // 2],
                  fill=(120, 124, 130))
    for wx in range(x0 + 14, x1 - 24, 44):
        d.arc([wx, y1 - 9, wx + 20, y1 - 1], start=180, end=360,
              fill=WHITE, width=2)
    f = font(F_SANS_BOLD, 9)
    tl(d, x0 + 5, y0 + 3, "CRIMEA", f, fill=INK)
    tr(d, x1 - 5, y0 + 3, "RUSSIA", f, fill=INK)
    tag(d, x0 + 5, y1 - 18, "3RD HIT IN A WEEK", (178, 24, 24), size=9)


def art_senate(d, box):
    """4: Senate semicircle -- 56 blue vs 44 red, Alaska star."""
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=(243, 238, 224))
    cx, cy, r = (x0 + x1) // 2, y1 - 12, 20
    n = 25
    for i in range(n):
        ang = math.pi + i * math.pi / (n - 1)
        px, py = cx + r * math.cos(ang), cy + r * math.sin(ang)
        colour = EUROPE if i < 14 else (200, 40, 55)
        d.ellipse([px - 3.4, py - 3.4, px + 3.4, py + 3.4], fill=colour)
    r2 = r - 8
    for i in range(n - 4):
        ang = math.pi + i * math.pi / (n - 5)
        px, py = cx + r2 * math.cos(ang), cy + r2 * math.sin(ang)
        colour = EUROPE if i < 11 else (200, 40, 55)
        d.ellipse([px - 3, py - 3, px + 3, py + 3], fill=colour)
    tag(d, x0 + 4, y0 + 3, "DEMOCRATS 56", EUROPE, size=9)
    tag_r(d, x1 - 5, y0 + 3, "REPUBLICANS 44", (200, 40, 55), size=9)
    tc(d, cx, y1 - 11, "PELTOLA WINS ALASKA", font(F_SANS_BOLD, 8.5),
       fill=INK)


def art_measles(d, box):
    """5: three flags over a revoked-status banner."""
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=(246, 240, 232))
    flags = [flag_us, flag_mx, flag_bo]
    names = ["US", "MEXICO", "BOLIVIA"]
    fw, fh = 46, 22
    gap = ((x1 - x0) - 3 * fw) // 4
    for i, (fl, nm) in enumerate(zip(flags, names)):
        fx = x0 + gap + i * (fw + gap)
        fl(d, (fx, y0 + 2, fx + fw, y0 + 2 + fh))
        tc(d, fx + fw // 2, y0 + 4 + fh, nm, font(F_SANS_BOLD, 7), fill=INK)
    by = y1 - 13
    d.rectangle([x0 + 4, by, x1 - 4, y1 - 2], fill=(178, 24, 24))
    tc(d, (x0 + x1) // 2, by + 2, "MEASLES-FREE STATUS REVOKED",
       font(F_SANS_BOLD, 9), fill=WHITE)


def art_ebola(d, box):
    """6: Ebola -- red cross, virus, case-count tag."""
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=(233, 244, 236))
    cy = (y0 + y1) // 2
    # red cross in a white box
    bx = x0 + 14
    d.rectangle([bx, cy - 15, bx + 34, cy + 15], fill=WHITE, outline=INK)
    d.rectangle([bx + 13, cy - 10, bx + 21, cy + 10], fill=(200, 30, 40))
    d.rectangle([bx + 7, cy - 4, bx + 27, cy + 4], fill=(200, 30, 40))
    # virus: spiked circle
    vx, vy = x0 + 86, cy
    for a in range(0, 360, 30):
        ex = vx + 15 * math.cos(math.radians(a))
        ey = vy + 15 * math.sin(math.radians(a))
        d.line([(vx, vy), (ex, ey)], fill=(150, 40, 120), width=3)
        d.ellipse([ex - 3, ey - 3, ex + 3, ey + 3], fill=(150, 40, 120))
    d.ellipse([vx - 11, vy - 11, vx + 11, vy + 11], fill=(170, 60, 140))
    tag_r(d, x1 - 5, cy - 9, "11,000+ CASES", (20, 24, 32), size=9.5)
    flag_cd(d, (x0 + 118, y0 + 36, x0 + 152, y0 + 48))


def art_cop(d, box):
    """7: COP31 -- globe, draft document, thermometer."""
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=(235, 242, 246))
    cy = (y0 + y1) // 2
    # globe
    gx, gr = x0 + 30, 17
    d.ellipse([gx - gr, cy - gr, gx + gr, cy + gr], fill=(120, 180, 220),
              outline=NAVY, width=2)
    d.ellipse([gx - 7, cy - gr, gx + 7, cy + gr], outline=NAVY, width=1)
    d.line([(gx - gr, cy), (gx + gr, cy)], fill=NAVY, width=1)
    d.pieslice([gx - gr, cy - gr, gx + 2, cy + 6], start=90, end=230,
               fill=GREEN)
    # draft document
    dx = x0 + 58
    d.rectangle([dx, y0 + 5, dx + 84, y1 - 5], fill=WHITE, outline=INK)
    tl(d, dx + 5, y0 + 8, "DRAFT", font(F_SANS_BOLD, 8), fill=INK)
    tl(d, dx + 5, y0 + 18, "PHASE OUT", font(F_SANS_BOLD, 8.5), fill=RED)
    tl(d, dx + 5, y0 + 28, "FOSSIL FUELS?", font(F_SANS_BOLD, 8.5), fill=RED)
    for ly in (y0 + 40, y0 + 45):
        d.line([(dx + 5, ly), (dx + 76, ly)], fill=GREY, width=1)
    # thermometer
    tx = x1 - 18
    d.rectangle([tx - 3, y0 + 6, tx + 3, y1 - 12], fill=WHITE, outline=INK)
    d.rectangle([tx - 3, y0 + 24, tx + 3, y1 - 12], fill=(210, 40, 40))
    d.ellipse([tx - 7, y1 - 16, tx + 7, y1 - 2], fill=(210, 40, 40))


def art_gaza(d, box):
    """8: Gaza winter -- tents, the Yellow Line, flood tag."""
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=(240, 236, 224))
    gy = y1 - 8
    for tx in (x0 + 16, x0 + 62):
        d.polygon([(tx, gy), (tx + 20, y0 + 10), (tx + 40, gy)],
                  fill=(196, 178, 150), outline=INK)
        d.polygon([(tx + 15, gy), (tx + 20, y0 + 24), (tx + 25, gy)],
                  fill=(90, 80, 66))
    # the Yellow Line across the ground
    d.line([(x0 + 110, y0 + 4), (x0 + 110, y1 - 2)], fill=YELLOW, width=4)
    d.line([(x0 + 110, y0 + 4), (x0 + 110, y1 - 2)], fill=INK, width=1)
    # aid box with red cross
    ax = x0 + 128
    d.rectangle([ax, gy - 22, ax + 30, gy], fill=WHITE, outline=INK)
    d.rectangle([ax + 12, gy - 18, ax + 18, gy - 4], fill=(200, 30, 40))
    d.rectangle([ax + 8, gy - 14, ax + 22, gy - 8], fill=(200, 30, 40))
    tag_r(d, x1 - 5, y0 + 3, "950,000 AT RISK", (150, 30, 30), size=8.5)


def art_nvidia(d, box):
    """9: rising bars on black, the big figure."""
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=BLACK)
    base = y1 - 8
    for i, bh in enumerate((10, 16, 13, 24, 33)):
        bx = x0 + 10 + i * 15
        d.rectangle([bx, base - bh, bx + 10, base], fill=(90, 200, 90))
    tl(d, x0 + 92, y0 + 4, "$115.8BN", font(F_SANS_BOLD, 19),
       fill=(90, 220, 110))
    tl(d, x0 + 93, y0 + 28, "SALES X2", font(F_SANS_BOLD, 11),
       fill=(240, 220, 110))


def art_anthropic(d, box):
    """10: record offering -- rising line chart, big figure."""
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=(238, 236, 250))
    pts = [(x0 + 8, y1 - 14), (x0 + 40, y1 - 26), (x0 + 66, y1 - 20),
           (x0 + 96, y1 - 34), (x0 + 124, y1 - 30), (x0 + 156, y1 - 44),
           (x0 + 182, y1 - 46)]
    d.line(pts, fill=ASIA, width=3)
    d.ellipse([pts[-1][0] - 4, pts[-1][1] - 4, pts[-1][0] + 4, pts[-1][1] + 4],
              fill=RED)
    tl(d, x0 + 8, y0 + 4, "$81.3BN", font(F_SANS_BOLD, 19), fill=ASIA)
    tl(d, x0 + 9, y0 + 28, "RECORD OFFERING", font(F_SANS_BOLD, 10),
       fill=GREY)


def art_quad(d, box):
    """11: Quad summit -- banner, four flags, names (mini-panel size)."""
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=(243, 238, 224))
    d.rectangle([x0, y0, x1, y0 + 13], fill=(88, 60, 160))
    tc(d, (x0 + x1) // 2, y0 + 2, "QUAD SUMMIT · MANILA",
       font(F_SANS_BOLD, 10), fill=WHITE)
    flags = [flag_us, flag_in, flag_jp, flag_au]
    names = ["US", "INDIA", "JAPAN", "AUSTRALIA"]
    fw, fh = 40, 22
    gap = ((x1 - x0) - 4 * fw) // 5
    fy = y0 + 16
    for i, (fl, nm) in enumerate(zip(flags, names)):
        fx = x0 + gap + i * (fw + gap)
        fl(d, (fx, fy, fx + fw, fy + fh))
        tc(d, fx + fw // 2, fy + fh + 1, nm, font(F_SANS_BOLD, 7), fill=INK)


def art_eu_loan(d, box):
    """12: EU stars circle around the EUR 45bn figure."""
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=(232, 238, 248))
    cx, cy = x0 + 42, (y0 + y1) // 2
    d.ellipse([cx - 24, cy - 24, cx + 24, cy + 24], fill=(0, 51, 153))
    for i in range(12):
        ang = -math.pi / 2 + i * math.pi / 6
        sx = cx + 16 * math.cos(ang)
        sy = cy + 16 * math.sin(ang)
        star(d, sx, sy, 3, YELLOW)
    tl(d, x0 + 76, y0 + 4, "€45BN", font(F_SANS_BOLD, 21), fill=NAVY)
    tl(d, x0 + 77, y0 + 28, "LOAN FOR", font(F_SANS_BOLD, 10), fill=GREY)
    tl(d, x0 + 77, y0 + 39, "UKRAINE", font(F_SANS_BOLD, 10), fill=GREY)


def art_cyclone(d, box):
    """13: Category 5 cyclone -- spiral over the Cook Islands."""
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=(214, 230, 242))
    cx, cy = x0 + 70, (y0 + y1) // 2
    for r, col in [(24, (120, 170, 220)), (17, (90, 150, 205)),
                   (10, (60, 120, 190))]:
        d.arc([cx - r, cy - r, cx + r, cy + r], start=20, end=300,
              fill=col, width=4)
    d.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=WHITE, outline=INK)
    # a small island under the eye
    d.ellipse([cx + 30, y1 - 20, cx + 56, y1 - 12], fill=GREEN, outline=INK)
    tc(d, cx + 43, y1 - 11, "COOK IS.", font(F_SANS_BOLD, 7), fill=INK)
    tag_r(d, x1 - 5, y0 + 4, "CATEGORY 5", (178, 24, 24), size=10)
    tag_r(d, x1 - 5, y0 + 20, "XAVIER", (20, 24, 32), size=10)


def art_voyager(d, box):
    """14: Voyager probe, its signal crawling toward a small Earth."""
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=(14, 20, 44))
    for sx, sy in [(18, 10), (52, 44), (88, 8), (140, 50), (176, 14),
                   (200, 40), (30, 56), (120, 58)]:
        d.ellipse([x0 + sx, y0 + sy, x0 + sx + 2, y0 + sy + 2], fill=WHITE)
    cy = (y0 + y1) // 2
    # dish and bus
    d.pieslice([x0 + 8, cy - 20, x0 + 48, cy + 20], start=90, end=270,
               fill=(220, 224, 230))
    d.rectangle([x0 + 42, cy - 6, x0 + 62, cy + 6], fill=(170, 176, 186))
    d.line([(x0 + 62, cy), (x0 + 118, cy - 14)], fill=(170, 176, 186), width=3)
    d.ellipse([x0 + 114, cy - 17, x0 + 122, cy - 9], fill=YELLOW)
    # signal arcs to Earth
    for r in (12, 20, 28):
        d.arc([x0 + 128 - r // 2, cy - r, x0 + 128 + r, cy + r], start=300,
              end=60, fill=(120, 200, 250), width=2)
    ex = x1 - 22
    d.ellipse([ex - 11, cy - 11, ex + 11, cy + 11], fill=(70, 140, 220))
    d.pieslice([ex - 11, cy - 11, ex + 3, cy + 8], start=60, end=200,
               fill=GREEN)
    tc(d, (x0 + x1) // 2, y1 - 13, "ONE LIGHT-DAY", font(F_SANS_BOLD, 9),
       fill=WHITE)


# --------------------------------------------------------------------------
# World map (simplified equirectangular continents) with numbered pins
# --------------------------------------------------------------------------

NAM = [(-168, 65), (-158, 71), (-140, 70), (-130, 71), (-120, 71),
       (-110, 68), (-100, 69), (-95, 69), (-90, 69), (-85, 66), (-82, 66),
       (-79, 62), (-76, 60), (-70, 62), (-65, 60), (-60, 55), (-55, 52),
       (-56, 50), (-60, 46), (-65, 44), (-68, 44), (-70, 42), (-74, 39),
       (-76, 35), (-79, 33), (-80, 31), (-80, 27), (-81, 25), (-82, 27),
       (-84, 29), (-87, 30), (-89, 29), (-94, 29), (-97, 28), (-97, 25),
       (-97, 22), (-94, 17), (-90, 14), (-87, 13), (-83, 9), (-79, 9),
       (-81, 12), (-85, 15), (-90, 14), (-94, 16), (-97, 16), (-102, 19),
       (-105, 23), (-108, 25), (-111, 29), (-114, 31), (-117, 33),
       (-120, 34), (-122, 37), (-123, 40), (-124, 45), (-124, 48),
       (-128, 52), (-132, 55), (-137, 58), (-145, 60), (-152, 59),
       (-156, 58), (-161, 59), (-165, 60), (-168, 63)]
GREENLAND = [(-46, 59), (-40, 63), (-32, 68), (-22, 70), (-20, 73),
             (-25, 78), (-32, 80), (-45, 80), (-55, 78), (-58, 75),
             (-57, 70), (-55, 65), (-53, 61)]
SAM = [(-78, 7), (-75, 10), (-72, 12), (-68, 11), (-64, 10), (-61, 9),
       (-57, 7), (-54, 6), (-51, 4), (-50, 1), (-46, -1), (-42, -3),
       (-38, -5), (-35, -8), (-36, -10), (-38, -13), (-39, -18),
       (-40, -21), (-42, -23), (-45, -24), (-48, -26), (-50, -29),
       (-52, -32), (-54, -34), (-57, -37), (-58, -39), (-61, -39),
       (-62, -41), (-63, -43), (-65, -45), (-66, -47), (-67, -49),
       (-68, -51), (-68, -53), (-70, -54), (-72, -54), (-73, -51),
       (-74, -48), (-74, -44), (-73, -40), (-73, -36), (-72, -31),
       (-71, -27), (-70, -22), (-70, -18), (-72, -16), (-75, -14),
       (-77, -11), (-79, -8), (-80, -5), (-81, -3), (-80, 0), (-79, 2),
       (-78, 4)]
EURO_PE = [(-9, 37), (-9, 43), (-8, 44), (-4, 44), (-1, 45), (-2, 47),
          (-4, 48), (-1, 50), (1, 51), (3, 52), (5, 53), (7, 54),
          (8, 55), (7, 57), (8, 58), (10, 59), (7, 59), (5, 60), (5, 62),
          (8, 63), (11, 65), (14, 67), (17, 69), (21, 70), (26, 71),
          (31, 71), (38, 69), (44, 68), (48, 66), (50, 64), (48, 62),
          (44, 60), (42, 58), (40, 56), (38, 55), (35, 55), (33, 54),
          (31, 52), (30, 51), (28, 50), (27, 48), (29, 46), (28, 45),
          (29, 43), (28, 41), (27, 40), (26, 39), (27, 38), (26, 37),
          (24, 37), (23, 36), (22, 37), (21, 38), (20, 39), (19, 40),
          (16, 39), (15, 38), (12, 38), (13, 41), (12, 43), (10, 44),
          (7, 44), (3, 43), (0, 40), (-1, 38), (-2, 37)]
ITALY = [(8, 44), (10, 44), (11, 43), (13, 41), (14, 40), (16, 38),
         (18, 40), (16, 40), (14, 41), (12, 42), (10, 43), (8, 44)]
UK = [(-5, 50), (-3, 50), (-2, 52), (-3, 55), (-4, 57), (-3, 58),
      (-4, 59), (-6, 58), (-8, 55), (-6, 54), (-5, 52)]
IRELAND = [(-10, 52), (-8, 52), (-6, 52), (-6, 54), (-8, 55), (-10, 54)]
AFR_PE = [(-6, 35), (-2, 35), (3, 37), (9, 37), (11, 34), (15, 32),
          (20, 32), (25, 32), (30, 31), (32, 31), (33, 28), (35, 24),
          (37, 22), (39, 20), (40, 18), (42, 15), (43, 12), (45, 11),
          (48, 11), (51, 11), (48, 9), (46, 6), (43, 3), (41, -1),
          (40, -5), (40, -9), (39, -13), (38, -17), (37, -20), (36, -23),
          (35, -26), (33, -28), (31, -30), (29, -32), (27, -34),
          (25, -34), (22, -35), (20, -35), (19, -33), (18, -31),
          (17, -28), (16, -24), (15, -21), (14, -18), (13, -14),
          (12, -11), (11, -7), (10, -4), (9, -1), (9, 2), (8, 4), (6, 4),
          (3, 6), (-1, 5), (-4, 5), (-7, 4), (-9, 4), (-12, 7),
          (-14, 9), (-16, 12), (-17, 15), (-17, 18), (-16, 21),
          (-16, 24), (-15, 27), (-14, 29), (-11, 31), (-8, 33)]
MADAGASCAR = [(44, -12), (47, -13), (49, -15), (50, -17), (48, -20),
              (46, -23), (45, -25), (44, -23), (43, -20), (43, -16)]
ASIA_PE = [(26, 41), (28, 41), (30, 42), (31, 44), (30, 46), (31, 48),
        (30, 50), (32, 52), (34, 54), (36, 55), (39, 55), (42, 57),
        (44, 59), (46, 62), (48, 64), (50, 66), (55, 68), (62, 69),
        (68, 70), (73, 71), (78, 72), (84, 73), (90, 74), (96, 76),
        (102, 77), (108, 77), (113, 74), (118, 73), (124, 72), (130, 71),
        (136, 71), (142, 72), (148, 71), (154, 70), (160, 69), (166, 67),
        (172, 66), (178, 65), (173, 62), (168, 61), (163, 60), (159, 57),
        (157, 53), (156, 51), (153, 49), (150, 46), (145, 45), (142, 43),
        (141, 41), (139, 39), (137, 36), (134, 35), (131, 34), (129, 33),
        (126, 31), (123, 30), (121, 28), (120, 26), (119, 24), (116, 23),
        (112, 22), (109, 20), (108, 17), (107, 14), (106, 10), (104, 7),
        (102, 6), (100, 7), (99, 10), (98, 13), (97, 15), (95, 16),
        (93, 17), (91, 16), (90, 19), (89, 21), (88, 22), (86, 20),
        (84, 19), (82, 16), (80, 14), (78, 9), (77, 8), (76, 10),
        (75, 13), (73, 16), (72, 19), (70, 21), (68, 23), (66, 25),
        (63, 25), (60, 25), (57, 26), (55, 25), (53, 26), (51, 28),
        (50, 29), (49, 30), (48, 29), (50, 27), (52, 25), (54, 24),
        (56, 24), (58, 23), (59, 22), (57, 21), (55, 20), (53, 18),
        (51, 16), (49, 14), (47, 13), (45, 12), (43, 13), (42, 15),
        (41, 17), (40, 20), (39, 22), (37, 24), (35, 28), (34, 31),
        (34, 34), (36, 36), (35, 37), (33, 36), (31, 36), (29, 36),
        (27, 37), (26, 38)]
JAPAN = [(140, 36), (141, 38), (141, 40), (142, 42), (143, 43),
         (142, 45), (141, 44), (140, 41), (139, 38), (138, 36)]
JAPAN2 = [(131, 32), (132, 33), (134, 34), (135, 35), (133, 34),
          (131, 33)]
BORNEO = [(109, 1), (113, 3), (117, 5), (119, 2), (118, -1), (115, -3),
          (111, -3), (109, -1)]
SUMATRA = [(95, 5), (99, 3), (103, -1), (105, -4), (106, -6), (103, -4),
           (99, 0), (96, 3)]
JAVA = [(106, -6), (110, -7), (113, -7), (114, -8), (110, -8), (106, -7)]
SULAWESI = [(119, 0), (121, 1), (123, 0), (121, -2), (120, -4), (119, -2)]
NEWGUINEA = [(131, -1), (136, -2), (141, -3), (146, -4), (149, -6),
             (150, -8), (147, -9), (143, -7), (138, -5), (133, -3)]
PHILIPPINES = [(120, 18), (121, 16), (122, 14), (121, 13), (120, 14),
               (120, 16)]
AUSTRALIA = [(113, -22), (112, -25), (114, -29), (115, -32), (115, -34),
             (117, -35), (120, -34), (124, -33), (127, -32), (130, -32),
             (132, -32), (134, -33), (135, -35), (137, -36), (139, -37),
             (140, -38), (143, -38), (145, -38), (147, -39), (149, -38),
             (150, -37), (151, -34), (153, -31), (153, -28), (153, -25),
             (152, -23), (150, -21), (148, -19), (146, -18), (144, -15),
             (143, -13), (142, -11), (141, -15), (141, -17), (140, -19),
             (139, -18), (137, -16), (136, -15), (135, -12), (132, -11),
             (130, -12), (128, -13), (126, -14), (124, -16), (122, -17),
             (120, -19), (118, -20), (116, -21)]
NZ = [(167, -45), (169, -44), (171, -43), (172, -42), (173, -40),
      (174, -39), (175, -37), (176, -38), (175, -40), (173, -41),
      (171, -42), (169, -44), (167, -46)]

CONTINENTS = [NAM, GREENLAND, SAM, EURO_PE, ITALY, UK, IRELAND, AFR_PE,
              MADAGASCAR, ASIA_PE, JAPAN, JAPAN2, BORNEO, SUMATRA, JAVA,
              SULAWESI, NEWGUINEA, PHILIPPINES, AUSTRALIA, NZ]

# (number, lon, lat, dx, dy) -- dx/dy nudge pins out of tight clusters
PINS = [
    (1, 114, 22, 0, -6),    # Shenzhen
    (2, 50, 26, 4, 5),      # Qeshm / Bahrain
    (3, 37, 45, 5, -4),     # Kerch
    (4, -150, 64, 0, 0),    # Alaska
    (5, -98, 39, 0, 0),     # US measles
    (6, 23, -2, 0, 0),      # DR Congo
    (7, 31, 37, -7, 3),     # Antalya
    (8, 34, 31, 6, 8),      # Gaza
    (9, -122, 37, -9, -3),  # Nvidia, California
    (10, -74, 41, 0, 0),    # Anthropic offering, New York
    (11, 121, 15, 0, 0),    # Manila
    (12, 4, 51, -6, -3),    # Brussels
    (13, -160, -15, 0, 0),  # Cook Islands
]
PIN_COLOURS = {1: ASIA, 2: MIDEAST, 3: EUROPE, 4: AMERICAS, 5: AMERICAS,
               6: AFRICA, 7: GLOBALC, 8: MIDEAST, 9: AMERICAS,
               10: AMERICAS, 11: ASIA, 12: EUROPE, 13: OCEANIA}


def draw_map(d, box):
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=MAPSEA)
    sx = (x1 - x0) / 360.0
    sy = (y1 - y0) / 160.0

    def proj(lon, lat):
        return (x0 + (lon + 168) * sx, y0 + (88 - lat) * sy)

    for poly in CONTINENTS:
        d.polygon([proj(lon, lat) for lon, lat in poly], fill=LAND)
    for num, lon, lat, dx, dy in PINS:
        px, py = proj(lon, lat)
        chip(d, px + dx, py + dy, 9, num, PIN_COLOURS[num])
    d.rectangle(box, outline=INK, width=2)


# --------------------------------------------------------------------------
# Page content
# --------------------------------------------------------------------------

TOP_PANELS = [
    dict(num=1, colour=ASIA, kicker="ASIA · DIPLOMACY", art=art_shenzhen,
         headline="Xi and Putin meet in Shenzhen; trilateral set for Thursday",
         deck="First Trump–Xi–Putin meeting due at APEC. Xi vows to oppose "
              "protectionism; Putin hits Western sanctions."),
    dict(num=2, colour=MIDEAST, kicker="MIDDLE EAST · IRAN WAR",
         art=art_gulf,
         headline="US jets strike IRGC site on Qeshm; Iran's drones downed",
         deck="Iran answers with drones at US sites in Kuwait and Bahrain — "
              "all intercepted, no damage reported."),
    dict(num=3, colour=EUROPE, kicker="EUROPE · UKRAINE WAR", art=art_bridge,
         headline="Ukraine hits Kerch Bridge a third time in a week",
         deck="A road span collapses into the strait, Kyiv says. Russia "
              "vows to rebuild."),
]

MINI_PANELS = [
    dict(num=4, colour=AMERICAS, kicker="AMERICAS · POLITICS",
         art=art_senate,
         headline="Peltola wins Alaska; Senate 56–44",
         deck="Ninth Democratic flip of the midterms, AP projects."),
    dict(num=5, colour=AMERICAS, kicker="AMERICAS · HEALTH", art=art_measles,
         headline="US loses measles-free status after 26 years",
         deck="5,412 cases in 2026, most since 1991; Mexico and Bolivia "
              "lose status too."),
    dict(num=6, colour=AFRICA, kicker="AFRICA · HEALTH", art=art_ebola,
         headline="Ebola in DR Congo tops 11,000 cases",
         deck="About 5,400 deaths — the second-largest outbreak on record."),
    dict(num=7, colour=GLOBALC, kicker="GLOBAL · CLIMATE", art=art_cop,
         headline="COP31 deadlocked over fossil-fuel phase-out",
         deck="Climate check launches in Antalya; the talks close Friday."),
    dict(num=8, colour=MIDEAST, kicker="MIDDLE EAST · GAZA", art=art_gaza,
         headline="Board of Peace faults Israel and Hamas",
         deck="Tanks cross the Yellow Line; 950,000 displaced in "
              "flood-prone ground."),
    dict(num=9, colour=AMERICAS, kicker="AMERICAS · BUSINESS", art=art_nvidia,
         headline="Nvidia's quarterly sales double to $115.8bn",
         deck="The board will not reinstate ousted CEO Jensen Huang."),
    dict(num=10, colour=AMERICAS, kicker="AMERICAS · TECH",
         art=art_anthropic,
         headline="Anthropic raises $81.3bn, a record",
         deck="The largest stock offering on record, it says."),
    dict(num=11, colour=ASIA, kicker="ASIA · DIPLOMACY", art=art_quad,
         headline="Trump holds first Quad summit, in Manila",
         deck="A Philippines trade deal Manila calls an economic "
              "understanding."),
    dict(num=12, colour=EUROPE, kicker="EUROPE · POLITICS", art=art_eu_loan,
         headline="EU proposes a €45bn loan for Ukraine",
         deck="Repaid only after Russia pays war reparations, the plan says."),
    dict(num=13, colour=OCEANIA, kicker="OCEANIA · DISASTER", art=art_cyclone,
         headline="Category 5 Cyclone Xavier hits Cook Islands",
         deck="The Northern Cook Islands take the storm's full force."),
]

ALSO = [
    (15, EUROPE, "Russia fires 365 drones, missiles at Ukraine grid"),
    (16, EUROPE, "Russia, Ukraine agree largest prisoner swap"),
    (17, AMERICAS, "Rubio: 'no need' for major Iran combat"),
    (18, MIDEAST, "Houthis launch five drones at Saudi pipelines"),
    (19, MIDEAST, "Iran vows 'more crushing' reply; 3rd US carrier in Gulf"),
    (20, EUROPE, "UK sanctions eight Israeli settlement firms"),
    (21, MIDEAST, "Kahana elected Knesset speaker 66–52"),
    (22, AFRICA, "Ethiopia, Eritrea mass forces on border"),
    (23, EUROPE, "Turkish court bans İmamoğlu from politics"),
    (24, EUROPE, "Five EU states plan migrant hubs in Rwanda"),
    (25, EUROPE, "Tens of thousands join French pay protests"),
    (26, ASIA, "World Court to rule on Myanmar genocide case"),
    (27, AMERICAS, "Canada, China cut tariffs after Carney–Xi talks"),
    (28, ASIA, "EU approves trade deal with Indonesia"),
    (29, EUROPE, "UK inflation rises to 3.6%"),
    (30, OCEANIA, "Australian unemployment jumps to 4.9%"),
    (31, ASIA, "Japan exports jump 20.5% on chips"),
    (32, EUROPE, "Equinor hit by cyberattack as gas stays costly"),
    (33, AMERICAS, "Waymo halts driverless freeway rides in California"),
    (34, AMERICAS, "House Democrats nominate Jeffries for Speaker"),
    (35, AMERICAS, "US, Venezuela renew military ties"),
    (36, AMERICAS, "Salvadoran troops raze Haitian gang leader's home"),
    (37, AMERICAS, "Florida pastor convicted in Moïse plot"),
    (38, AMERICAS, "Isolated Awa group emerges in Amazon"),
    (39, ASIA, "Bangladesh unrest: clashes, arson, strikes"),
    (40, MIDEAST, "Iraq resumes oil exports via Turkey, 120,000 b/d"),
    (41, OCEANIA, "Fiji declares national disaster over drought"),
    (42, GLOBALC, "GTA VI launches after a 13-year wait"),
    (43, EUROPE, "Chelsea beat PSG 1–0; Alcaraz beats Medvedev"),
]


# --------------------------------------------------------------------------
# Page assembly
# --------------------------------------------------------------------------

def panel(d, box, spec, art_h, head_start, deck_size):
    x0, y0, x1, y1 = box
    d.rectangle(box, outline=INK, width=2)
    art_box = (x0 + 2, y0 + 2, x1 - 2, y0 + 2 + art_h)
    spec["art"](d, art_box)
    d.line([(x0 + 2, y0 + 2 + art_h), (x1 - 2, y0 + 2 + art_h)],
           fill=INK, width=1)
    inner_w = (x1 - x0) - 16
    kicker_cy = y0 + 2 + art_h + 13
    chip(d, x0 + 19, kicker_cy, 10 if art_h > 60 else 9, spec["num"],
         spec["colour"])
    d.text((x0 + 34, kicker_cy), spec["kicker"], font=font(F_SANS_BOLD, 12),
           fill=spec["colour"], anchor="lm")
    hy = kicker_cy + 11
    hf = fit_block(d, spec["headline"], F_SANS_BOLD, inner_w, 2, head_start, 13)
    lines = wrap(d, spec["headline"], hf, inner_w)
    hy = block_l(d, x0 + 8, hy, lines, hf, int(hf.size * 1.14))
    df = fit_block(d, spec["deck"], F_SANS, inner_w, 2, deck_size, 9)
    block_l(d, x0 + 8, hy + 3, wrap(d, spec["deck"], df, inner_w), df,
            int(df.size * 1.3))


def build():
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)

    # ---- masthead ------------------------------------------------------
    tl(d, MARGIN, 12, "THE WORLD IN A DAY", font(F_SERIF_BOLD, 23))
    tr(d, W - MARGIN, 16, "43 STORIES · 6 CONTINENTS · ALL FROM WEDNESDAY",
       font(F_SANS_BOLD, 15))
    f_date = fit_font(d, "WEDNESDAY 18 NOVEMBER 2026", F_SANS_BOLD, CW, 68)
    tc(d, W // 2, 40, "WEDNESDAY 18 NOVEMBER 2026", f_date, fill=RED)
    d.line([(MARGIN, 112), (W - MARGIN, 112)], fill=INK, width=3)
    d.line([(MARGIN, 118), (W - MARGIN, 118)], fill=INK, width=1)

    # ---- top row: three large panels ------------------------------------
    top_y0, top_y1 = 126, 316
    edges = [MARGIN + round(i * CW / 3) for i in range(4)]
    for i, spec in enumerate(TOP_PANELS):
        x0 = edges[i] + (4 if i else 0)
        x1 = edges[i + 1] - (4 if i < 2 else 0)
        panel(d, (x0, top_y0, x1, top_y1), spec, art_h=76, head_start=23,
              deck_size=12)

    # ---- grid: ten mini panels, five over five ---------------------------
    rows = [(324, 470), (478, 624)]
    edges = [MARGIN + round(i * CW / 5) for i in range(6)]
    for r, (gy0, gy1) in enumerate(rows):
        for c in range(5):
            spec = MINI_PANELS[r * 5 + c]
            x0 = edges[c] + (4 if c else 0)
            x1 = edges[c + 1] - (4 if c < 4 else 0)
            panel(d, (x0, gy0, x1, gy1), spec, art_h=50, head_start=17,
                  deck_size=11)

    # ---- Voyager strip (story 14) ----------------------------------------
    sy0, sy1 = 632, 698
    d.rectangle((MARGIN, sy0, W - MARGIN, sy1), outline=INK, width=2)
    art_voyager(d, (MARGIN + 2, sy0 + 2, MARGIN + 222, sy1 - 2))
    tx = MARGIN + 238
    chip(d, tx + 10, sy0 + 17, 10, 14, GLOBALC)
    d.text((tx + 27, sy0 + 17), "GLOBAL · SPACE",
           font=font(F_SANS_BOLD, 12), fill=GLOBALC, anchor="lm")
    tl(d, tx, sy0 + 28, "Voyager 1 reaches one light-day from Earth",
       font(F_SANS_BOLD, 20))
    tl(d, tx, sy0 + 52,
       "First human-made object to do so; its signals now take over a day. "
       "(NASA JPL)",
       font(F_SANS, 11.5), fill=GREY)

    # ---- bottom: map + also list ------------------------------------------
    by = 708
    tl(d, MARGIN, by, "WHERE IT HAPPENED", font(F_SANS_BOLD, 14))
    d.line([(MARGIN, by + 20), (MARGIN + 430, by + 20)], fill=INK, width=2)
    draw_map(d, (MARGIN, by + 26, MARGIN + 430, by + 246))
    legend = [("Europe", EUROPE), ("Middle East", MIDEAST), ("Asia", ASIA),
              ("Africa", AFRICA), ("Americas", AMERICAS),
              ("Oceania", OCEANIA), ("Global & space", GLOBALC)]
    lx = MARGIN
    for name, colour in legend[:4]:
        d.ellipse([lx, by + 254, lx + 8, by + 262], fill=colour)
        tl(d, lx + 12, by + 252, name, font(F_SANS, 10.5))
        lx += 14 + d.textlength(name, font=font(F_SANS, 10.5)) + 12
    lx = MARGIN
    for name, colour in legend[4:]:
        d.ellipse([lx, by + 268, lx + 8, by + 276], fill=colour)
        tl(d, lx + 12, by + 266, name, font(F_SANS, 10.5))
        lx += 14 + d.textlength(name, font=font(F_SANS, 10.5)) + 12
    tl(d, lx + 2, by + 266, "· Pins 1–13; 14 is in space", font(F_SANS, 10.5),
       fill=GREY)

    ax = MARGIN + 442
    tl(d, ax, by, "ALSO ON WEDNESDAY 18 NOVEMBER", font(F_SANS_BOLD, 14))
    d.line([(ax, by + 20), (W - MARGIN, by + 20)], fill=INK, width=2)
    col_w = (W - MARGIN - ax - 14) // 2
    cols = [ALSO[:15], ALSO[15:]]
    for ci, items in enumerate(cols):
        cx0 = ax + ci * (col_w + 14)
        iy = by + 28
        for num, colour, text in items:
            chip(d, cx0 + 8, iy + 6, 7.5, num, colour)
            f = fit_font(d, text, F_SANS, col_w - 22, 10.5)
            tl(d, cx0 + 21, iy, text, f)
            iy += 16.6

    # ---- footer ------------------------------------------------------------
    d.line([(MARGIN, 992), (W - MARGIN, 992)], fill=INK, width=1)
    tl(d, MARGIN, 998,
       "Every story happened or was first reported on Wednesday 18 November "
       "2026; contested claims are marked as claims.",
       font(F_SANS, 9.5), fill=GREY)
    tr(d, W - MARGIN, 998,
       "Sources: Reuters, AP, AFP, BBC, WHO, UN, PAHO, NASA JPL.",
       font(F_SANS, 9.5), fill=GREY)

    return img


def main():
    img = build()
    img.save(OUT_PATH, format="PNG")
    print("wrote", OUT_PATH, os.path.getsize(OUT_PATH), "bytes")


if __name__ == "__main__":
    main()
