#!/usr/bin/env python3
"""
THE WORLD IN A DAY -- build-time drawing program (news-image-20261118,
round 2).

Paints the one-page broadsheet that sums up the world news of
Wednesday 18 November 2026. Build time only: it needs Pillow and the
Noto fonts, runs on the builder's machine, and writes entry.png next
to this file. The competition server never runs it -- the submitted
main.py is a stdlib-only copier that ships the finished PNG to the
output path. Regenerate with:

    python3 draw.py   # writes entry.png next to this file

Deterministic by construction: fixed geometry, no randomness, no
clock, no network, so two runs give a byte-identical PNG.

Round 2 is a full rebuild in the broadsheet formula that won the
sibling editions: a navy masthead with the date set huge in serif, a
field-taxonomy strip and a UTC timeline, three large illustrated
panels, eight numbered mini panels, a dot-matrix world map with
numbered pins, a stats strip, a numbered ALSO list and a red DATE
CHECK box -- 44 stories in all. Every story was re-verified against
Wednesday 18 November 2026 (UTC) reporting; the per-story notes and
the list of round-1 items dropped as stale live in STORIES.md.
"""

import math
import os

from PIL import Image
from PIL import ImageDraw, ImageFont

PAGE = 1024
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "entry.png")

FONT_DIR = "/usr/share/fonts/truetype/noto"
SERIF = os.path.join(FONT_DIR, "NotoSerif-Regular.ttf")
SERIF_B = os.path.join(FONT_DIR, "NotoSerif-Bold.ttf")
SERIF_BLK = os.path.join(FONT_DIR, "NotoSerif-Black.ttf")
SERIF_I = os.path.join(FONT_DIR, "NotoSerif-Italic.ttf")
SANS = os.path.join(FONT_DIR, "NotoSans-Regular.ttf")
SANS_B = os.path.join(FONT_DIR, "NotoSans-Bold.ttf")
SANS_I = os.path.join(FONT_DIR, "NotoSans-Italic.ttf")


def rgb(code):
    return (int(code[0:2], 16), int(code[2:4], 16), int(code[4:6], 16))


PAPER = rgb("f6f1e5")
CARD = rgb("fdfaf1")
INK = rgb("1c2126")
BODY = rgb("33383e")
NAVY = rgb("152a42")
NAVY_SOFT = rgb("22405f")
GOLD = rgb("b98a1c")
GOLD_LT = rgb("e3b341")
RED = rgb("b21818")
GREY = rgb("5c6066")
RULE = rgb("a2987e")
CREAM = rgb("efe7d2")
WHITE = rgb("ffffff")
SEA = rgb("e3e9ec")
LAND_DOT = rgb("64809c")

REGION_INK = {
    "europe": rgb("2563b3"),
    "mideast": rgb("bc5f16"),
    "asia": rgb("7d3c98"),
    "africa": rgb("1e8449"),
    "americas": rgb("b03a4b"),
    "oceania": rgb("148f7a"),
    "global": rgb("5d6d7e"),
}

CERT_STYLE = {
    "CONFIRMED": (NAVY, WHITE),
    "CLAIM": (RED, WHITE),
    "FORECAST": (GOLD, WHITE),
}

MARGIN = 14
WIDTH = PAGE - 2 * MARGIN

_cache = {}


def font(path, size):
    key = (path, size)
    if key not in _cache:
        _cache[key] = ImageFont.truetype(path, size)
    return _cache[key]


def text_w(dr, s, fnt):
    return dr.textlength(s, font=fnt)


def wrap_text(dr, s, fnt, width):
    """Greedy word wrap into lines no wider than `width`."""
    lines, cur = [], ""
    for word in s.split():
        trial = word if not cur else cur + " " + word
        if text_w(dr, trial, fnt) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def shrink_to_fit(dr, s, path, width, max_lines, start, floor):
    """Largest font size (start..floor) whose wrap fits max_lines."""
    size = start
    while size > floor:
        fnt = font(path, size)
        if len(wrap_text(dr, s, fnt, width)) <= max_lines:
            return fnt
        size -= 1
    return font(path, floor)


def text(dr, x, y, s, fnt, fill=INK, anchor="la"):
    dr.text((x, y), s, font=fnt, fill=fill, anchor=anchor)


def text_r(dr, x, y, s, fnt, fill=INK):
    dr.text((x, y), s, font=fnt, fill=fill, anchor="ra")


def tracked(dr, x, y, s, fnt, fill, gap=2):
    """Draw letterspaced text (broadsheet kickers); returns end x."""
    cx = x
    for ch in s:
        dr.text((cx, y), ch, font=fnt, fill=fill, anchor="la")
        cx += text_w(dr, ch, fnt) + gap
    return cx - gap


def stack(dr, x, y, lines, fnt, leading, fill=INK):
    for line in lines:
        dr.text((x, y), line, font=fnt, fill=fill, anchor="la")
        y += leading
    return y


def number_box(dr, cx, cy, num, size, fill, glyph=WHITE):
    """Square chip with the story number centred."""
    r = size // 2
    dr.rounded_rectangle([cx - r, cy - r, cx + r, cy + r], radius=3,
                         fill=fill)
    text(dr, cx, cy + 1, str(num), font(SANS_B, size - 5), fill=glyph,
         anchor="mm")


def pin_disc(dr, cx, cy, rad, num, fill):
    dr.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=fill,
               outline=WHITE, width=2)
    text(dr, cx, cy + 1, str(num), font(SANS_B, rad + 2), fill=WHITE,
         anchor="mm")


def cert_stamp(dr, x_right, cy, tag):
    """Small certainty pill, right-aligned at x_right; returns width."""
    bg, fg = CERT_STYLE[tag]
    fnt = font(SANS_B, 8)
    w = text_w(dr, tag, fnt) + 10
    dr.rounded_rectangle([x_right - w, cy - 7, x_right, cy + 7],
                         radius=2, fill=bg)
    text(dr, x_right - w / 2, cy + 1, tag, fnt, fill=fg, anchor="mm")
    return w


def data_chip(dr, x0, y1, label):
    """Navy data callout baked into the bottom-left of a scene."""
    fnt = font(SANS_B, 9)
    w = text_w(dr, label, fnt) + 12
    dr.rectangle([x0, y1 - 15, x0 + w, y1], fill=NAVY)
    text(dr, x0 + 6, y1 - 7, label, fnt, fill=WHITE, anchor="lm")


# ---------------------------------------------------------------------------
# Scene painters. Each fills box=(x0, y0, x1, y1) with flat shapes and
# bakes the story's key number into the artwork itself.
# ---------------------------------------------------------------------------

def scene_gulf(dr, box):
    """Stylised Gulf map: Kuwait, Bahrain, Qeshm, drone arcs."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    dr.rectangle(box, fill=rgb("b9cdd9"))
    # land masses: Arabia below-left, Iran above-right, sea between
    dr.polygon([(x0, y1), (x0, y0 + h * 0.52), (x0 + w * 0.30, y0 + h * 0.46),
                (x0 + w * 0.44, y0 + h * 0.60), (x0 + w * 0.40, y1)],
               fill=rgb("e5d29a"))
    dr.polygon([(x0 + w * 0.52, y0), (x1, y0), (x1, y0 + h * 0.30),
                (x0 + w * 0.72, y0 + h * 0.34), (x0 + w * 0.58, y0 + h * 0.18)],
               fill=rgb("e5d29a"))
    # Qeshm island
    dr.ellipse([x0 + w * 0.60, y0 + h * 0.30, x0 + w * 0.70, y0 + h * 0.40],
               fill=rgb("d9c084"))
    lab = font(SANS_B, 8)
    text(dr, x0 + w * 0.04, y0 + h * 0.60, "KUWAIT", lab, fill=rgb("7a6428"))
    text(dr, x0 + w * 0.30, y0 + h * 0.86, "SAUDI ARABIA", lab,
         fill=rgb("7a6428"))
    text(dr, x0 + w * 0.74, y0 + h * 0.06, "IRAN", lab, fill=rgb("7a6428"))
    text(dr, x0 + w * 0.615, y0 + h * 0.20, "QESHM", lab, fill=rgb("7a6428"))
    text(dr, x0 + w * 0.47, y0 + h * 0.52, "BAHRAIN", lab, fill=NAVY)
    # Ali Al Salem base marker in Kuwait
    bx, by = x0 + w * 0.13, y0 + h * 0.50
    dr.polygon([(bx, by - 5), (bx + 4, by + 3), (bx - 4, by + 3)], fill=NAVY)
    # dotted drone arcs from the east toward Kuwait and Bahrain
    for (sx, sy, ex, ey) in ((0.66, 0.36, 0.15, 0.48), (0.64, 0.40, 0.45, 0.55)):
        steps = 9
        for i in range(steps):
            t = i / steps
            px = x0 + w * (sx + (ex - sx) * t)
            py = y0 + h * (sy + (ey - sy) * t) - math.sin(t * math.pi) * h * 0.16
            dr.ellipse([px - 1.4, py - 1.4, px + 1.4, py + 1.4], fill=RED)
    # interception bursts at the arc ends
    for fx, fy in ((0.15, 0.42), (0.45, 0.50)):
        cx, cy = x0 + w * fx, y0 + h * fy
        for ang in range(0, 360, 45):
            dr.line([cx + 2 * math.cos(math.radians(ang)),
                     cy + 2 * math.sin(math.radians(ang)),
                     cx + 6 * math.cos(math.radians(ang)),
                     cy + 6 * math.sin(math.radians(ang))], fill=GOLD,
                    width=1)
        dr.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=RED)
    data_chip(dr, x0, y1, "ALI AL SALEM BASE · INTERCEPTED")


def scene_summit(dr, box):
    """Shenzhen tarmac: three flags, skyline, APEC opens."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    dr.rectangle(box, fill=rgb("bcd2de"))
    ground = y1 - 13
    dr.rectangle([x0, ground, x1, y1], fill=rgb("8fa9ba"))
    for fx, fh in ((0.60, 0.46), (0.70, 0.72), (0.80, 0.55), (0.90, 0.64)):
        tx = x0 + fx * w
        dr.rectangle([tx, ground - fh * h, tx + 11, ground],
                     fill=rgb("6e8aa0"))
    bw, bh = w * 0.145, h * 0.54
    for i, kind in enumerate(("us", "cn", "ru")):
        fx = x0 + w * (0.05 + i * 0.165)
        fy = y0 + 7
        dr.line([fx, fy - 3, fx, ground], fill=rgb("3c4652"), width=2)
        if kind == "us":
            dr.rectangle([fx + 2, fy, fx + 2 + bw, fy + bh], fill=WHITE)
            for s in range(4):
                dr.rectangle([fx + 2, fy + s * bh / 4, fx + 2 + bw,
                              fy + (s + 0.5) * bh / 4], fill=RED)
            dr.rectangle([fx + 2, fy, fx + 2 + bw * 0.45, fy + bh * 0.5],
                         fill=NAVY)
        elif kind == "cn":
            dr.rectangle([fx + 2, fy, fx + 2 + bw, fy + bh], fill=RED)
            for dx, dy, r in ((6, 6, 3), (13, 3, 1), (15, 8, 1),
                              (15, 13, 1), (13, 17, 1)):
                dr.ellipse([fx + 2 + dx - r, fy + dy - r, fx + 2 + dx + r,
                            fy + dy + r], fill=GOLD_LT)
        else:
            third = bh / 3
            dr.rectangle([fx + 2, fy, fx + 2 + bw, fy + third], fill=WHITE)
            dr.rectangle([fx + 2, fy + third, fx + 2 + bw, fy + 2 * third],
                         fill=rgb("2c4f9e"))
            dr.rectangle([fx + 2, fy + 2 * third, fx + 2 + bw, fy + bh],
                         fill=RED)
    text(dr, x0 + w * 0.60, y0 + 8, "SHENZHEN", font(SANS_B, 9), fill=NAVY)
    text(dr, x0 + w * 0.60, y0 + 20, "APEC OPENS", font(SANS_B, 9),
         fill=NAVY)
    data_chip(dr, x0, y1, "FIRST TRILATERAL · THURSDAY")


def scene_voyager(dr, box):
    """Deep space: Earth, the probe, a signal that takes a day."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    dr.rectangle(box, fill=rgb("101623"))
    for i in range(46):
        sx = x0 + (i * 37) % int(w)
        sy = y0 + (i * 23) % int(h)
        r = 1 if i % 4 else 1.6
        dr.ellipse([sx - r, sy - r, sx + r, sy + r], fill=rgb("cdd8e4"))
    ex, ey, er = x0 + w * 0.10, y0 + h * 0.68, h * 0.17
    dr.ellipse([ex - er, ey - er, ex + er, ey + er], fill=rgb("4a7fb5"))
    dr.pieslice([ex - er, ey - er, ex + er, ey + er], start=200, end=320,
                fill=rgb("58a05c"))
    text(dr, ex, ey + er + 3, "EARTH", font(SANS_B, 7), fill=rgb("cdd8e4"),
         anchor="ma")
    px, py = x0 + w * 0.80, y0 + h * 0.34
    # a faint straight signal line, drawn under the artwork's text
    dr.line([ex, ey, px, py], fill=NAVY_SOFT, width=1)
    dr.ellipse([px - 11, py - 11, px + 11, py + 11], outline=WHITE, width=2)
    dr.ellipse([px - 3, py - 3, px + 3, py + 3], fill=WHITE)
    dr.rectangle([px + 8, py + 6, px + 20, py + 10], fill=GOLD_LT)
    dr.line([px - 8, py + 8, px - 20, py + 18], fill=WHITE, width=2)
    text(dr, px, py + 15, "VOYAGER 1 · 1977", font(SANS_B, 8),
         fill=WHITE, anchor="ma")
    text(dr, x0 + w * 0.40, y0 + h * 0.10, "1 LIGHT-DAY",
         font(SERIF_BLK, 21), fill=WHITE, anchor="ma")
    text(dr, x0 + w * 0.40, y0 + h * 0.10 + 27,
         "25.9 BILLION KM FROM EARTH", font(SANS_B, 8), fill=GOLD_LT,
         anchor="ma")
    data_chip(dr, x0, y1, "SIGNAL: 24 HOURS EACH WAY")


def scene_strikes(dr, box):
    """Night over Odesa: drone specks, bursts, a lit skyline."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    dr.rectangle(box, fill=rgb("232c3d"))
    base = y1 - 13
    for fx, fh in ((0.03, 0.34), (0.15, 0.5), (0.28, 0.38), (0.55, 0.44),
                   (0.68, 0.58), (0.82, 0.4), (0.92, 0.3)):
        tx = x0 + fx * w
        dr.rectangle([tx, base - fh * h, tx + w * 0.09, base],
                     fill=rgb("12161f"))
        for wy in range(int(base - fh * h) + 3, base - 3, 6):
            for wx in range(int(tx) + 2, int(tx + w * 0.09) - 2, 5):
                if (wx * 11 + wy * 7) % 4 == 0:
                    dr.rectangle([wx, wy, wx + 2, wy + 2], fill=GOLD_LT)
    for i, (fx, fy) in enumerate(((0.2, 0.2), (0.38, 0.13), (0.55, 0.24),
                                  (0.72, 0.15), (0.86, 0.26))):
        cx, cy = x0 + fx * w, y0 + fy * h
        dr.ellipse([cx - 1.6, cy - 1.6, cx + 1.6, cy + 1.6], fill=WHITE)
        if i % 2 == 0:
            for ang in range(0, 360, 40):
                dr.line([cx + 3 * math.cos(math.radians(ang)),
                         cy + 3 * math.sin(math.radians(ang)),
                         cx + 7 * math.cos(math.radians(ang)),
                         cy + 7 * math.sin(math.radians(ang))],
                        fill=rgb("f0a13c"), width=1)
            dr.ellipse([cx - 2.4, cy - 2.4, cx + 2.4, cy + 2.4],
                       fill=rgb("f0a13c"))
    text(dr, x0 + w * 0.06, y0 + 5, "ODESA", font(SANS_B, 8),
         fill=rgb("cdd8e4"))
    data_chip(dr, x0, y1, "141 DRONES COUNTED OVERNIGHT")


def scene_gaza(dr, box):
    """Central Gaza: blocks, the Yellow Line, a tank nosing across."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    dr.rectangle(box, fill=rgb("d9cdb2"))
    base = y1 - 13
    dr.rectangle([x0, base, x1, y1], fill=rgb("b3a37f"))
    for fx, fh, fw in ((0.04, 0.52, 0.13), (0.20, 0.38, 0.10),
                       (0.62, 0.46, 0.12), (0.78, 0.34, 0.10),
                       (0.90, 0.5, 0.09)):
        tx = x0 + fx * w
        dr.rectangle([tx, base - fh * h, tx + fw * w, base],
                     fill=rgb("8f8672"))
        for wy in range(int(base - fh * h) + 3, base - 4, 6):
            for wx in range(int(tx) + 2, int(tx + fw * w) - 2, 6):
                if (wx + wy) % 3:
                    dr.rectangle([wx, wy, wx + 2, wy + 3],
                                 fill=rgb("e8dfc2"))
    lx = x0 + w * 0.52
    for yy in range(int(y0) + 2, int(base), 7):
        dr.line([lx, yy, lx, yy + 4], fill=RED, width=2)
    text(dr, lx - 4, y0 + 3, "YELLOW LINE", font(SANS_B, 7), fill=RED,
         anchor="ra")
    tx, ty = x0 + w * 0.30, base - h * 0.16
    dr.rectangle([tx, ty, tx + w * 0.17, ty + h * 0.10], fill=rgb("4c5548"))
    dr.rectangle([tx + w * 0.05, ty - h * 0.07, tx + w * 0.11, ty],
                 fill=rgb("4c5548"))
    dr.line([tx + w * 0.11, ty - h * 0.04, tx + w * 0.24, ty - h * 0.04],
            fill=rgb("4c5548"), width=3)
    for i in range(4):
        cx = tx + w * 0.02 + i * w * 0.04
        dr.ellipse([cx, ty + h * 0.10, cx + w * 0.03, ty + h * 0.16],
                   fill=rgb("39412f"))
    text(dr, x0 + w * 0.63, y0 + h * 0.82, "NUSEIRAT", font(SANS_B, 7),
         fill=rgb("6d6350"))
    data_chip(dr, x0, y1, "FIRST PUSH SINCE THE TRUCE")


def scene_horn(dr, box):
    """Horn of Africa sketch: two territories, a dotted border."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    dr.rectangle(box, fill=rgb("cfe0d8"))
    dr.polygon([(x0 + w * 0.30, y0 + h * 0.06), (x0 + w * 0.62, y0 + h * 0.04),
                (x0 + w * 0.70, y0 + h * 0.30), (x0 + w * 0.52, y0 + h * 0.44),
                (x0 + w * 0.34, y0 + h * 0.36)], fill=rgb("e8d9a8"))
    dr.polygon([(x0 + w * 0.22, y0 + h * 0.42), (x0 + w * 0.52, y0 + h * 0.46),
                (x0 + w * 0.66, y0 + h * 0.62), (x0 + w * 0.58, y0 + h * 0.92),
                (x0 + w * 0.30, y0 + h * 0.94), (x0 + w * 0.16, y0 + h * 0.66)],
               fill=rgb("cfe3b8"))
    for i in range(9):
        t = i / 8
        px = x0 + w * (0.33 + 0.20 * t)
        py = y0 + h * (0.38 + 0.07 * t)
        dr.ellipse([px - 1.4, py - 1.4, px + 1.4, py + 1.4], fill=INK)
    for fx, fy in ((0.36, 0.30), (0.44, 0.33), (0.40, 0.52), (0.50, 0.55)):
        cx, cy = x0 + fx * w, y0 + fy * h
        dr.polygon([(cx, cy - 4), (cx + 4, cy + 3), (cx - 4, cy + 3)],
                   fill=RED)
    lab = font(SANS_B, 8)
    text(dr, x0 + w * 0.40, y0 + h * 0.12, "ERITREA", lab, fill=rgb("7a6428"))
    text(dr, x0 + w * 0.30, y0 + h * 0.72, "ETHIOPIA", lab,
         fill=rgb("3f6428"))
    text(dr, x0 + w * 0.76, y0 + h * 0.10, "RED SEA", font(SANS_I, 8),
         fill=rgb("4a7396"))
    data_chip(dr, x0, y1, "TROOPS MASS BOTH SIDES")


def scene_speaker(dr, box):
    """Capitol dome with the vote count baked in big."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    dr.rectangle(box, fill=rgb("e9e2cf"))
    base = y1 - 13
    cx = x0 + w * 0.24
    # dome
    dr.pieslice([cx - w * 0.15, base - h * 0.78, cx + w * 0.15,
                 base - h * 0.18], start=180, end=360, fill=NAVY)
    dr.rectangle([cx - w * 0.17, base - h * 0.20, cx + w * 0.17,
                  base - h * 0.14], fill=NAVY)
    dr.line([cx, base - h * 0.78, cx, base - h * 0.92], fill=NAVY, width=2)
    dr.rectangle([cx - w * 0.20, base - h * 0.14, cx + w * 0.20, base],
                 fill=rgb("fbf7ea"), outline=NAVY, width=1)
    for i in range(5):
        cxx = cx - w * 0.15 + i * w * 0.075
        dr.rectangle([cxx, base - h * 0.11, cxx + w * 0.03, base - 2],
                     fill=NAVY)
    # the count, set into the art, clear of the certainty stamp
    ny = y0 + h * 0.14
    text(dr, x0 + w * 0.40, ny, "251–11", font(SERIF_BLK, 20), fill=RED)
    data_chip(dr, x0, y1, "FULL HOUSE VOTES 3 JAN")


def scene_garment(dr, box):
    """Factory blocks with shutters down and a crowd line."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    dr.rectangle(box, fill=rgb("dfe4e6"))
    base = y1 - 13
    for i, (fx, fh) in enumerate(((0.04, 0.62), (0.30, 0.78), (0.56, 0.55),
                                  (0.80, 0.70))):
        tx = x0 + fx * w
        dr.rectangle([tx, base - fh * h, tx + w * 0.17, base],
                     fill=rgb("9aa5ab"))
        for wy in range(int(base - fh * h) + 3, base - 10, 6):
            dr.line([tx + 2, wy, tx + w * 0.17 - 2, wy],
                    fill=rgb("6e7a80"), width=1)
        if i in (1, 3):
            dr.rectangle([tx, base - fh * h * 0.45, tx + w * 0.17,
                          base - fh * h * 0.45 + 6], fill=RED)
    # crowd: heads along the street
    for i in range(11):
        hx = x0 + w * (0.05 + i * 0.088)
        hy = base - 8
        dr.ellipse([hx - 2.4, hy - 2.4, hx + 2.4, hy + 2.4],
                   fill=rgb("33475e"))
    data_chip(dr, x0, y1, "55 FACTORIES SHUT · ~300 ARRESTS")


def scene_ipo(dr, box):
    """Navy board: a step chart climbing to the ANT listing."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    dr.rectangle(box, fill=NAVY)
    pts = [(0.05, 0.80), (0.20, 0.80), (0.20, 0.62), (0.36, 0.62),
           (0.36, 0.45), (0.50, 0.45), (0.50, 0.28), (0.62, 0.28)]
    xy = [(x0 + fx * w, y0 + fy * h) for fx, fy in pts]
    dr.line(xy, fill=GOLD_LT, width=3)
    ex, ey = xy[-1]
    dr.polygon([(ex, ey), (ex - 10, ey - 1), (ex - 3, ey + 8)],
               fill=GOLD_LT)
    for gx in (0.20, 0.36, 0.50):
        gx0 = x0 + gx * w
        dr.line([gx0, y0 + 5, gx0, y1 - 16], fill=NAVY_SOFT, width=1)
    text_r(dr, x0 + w * 0.70, y0 + 5, "ANT", font(SERIF_BLK, 22),
           fill=WHITE)
    data_chip(dr, x0, y1, "BIGGEST IPO EVER · $81.3BN")


def scene_cop(dr, box):
    """A globe and two rival draft clauses, split by a red tear."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    dr.rectangle(box, fill=rgb("dcebe4"))
    cx, cy, r = x0 + w * 0.20, y0 + h * 0.44, h * 0.30
    dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=rgb("7fb2d9"),
               outline=NAVY, width=1)
    dr.pieslice([cx - r, cy - r, cx + r, cy + r], start=100, end=210,
                fill=rgb("58a05c"))
    dr.pieslice([cx - r, cy - r, cx + r, cy + r], start=305, end=55,
                fill=rgb("58a05c"))
    dr.line([cx - r, cy, cx + r, cy], fill=NAVY, width=1)
    bx = x0 + w * 0.42
    for off in (0.0, 0.26):
        dr.rectangle([bx + off * w, y0 + 7, bx + (off + 0.22) * w,
                      y0 + h * 0.52], fill=rgb("fbf7ea"), outline=INK,
                     width=1)
        for i in range(3):
            dr.line([bx + off * w + 4, y0 + 14 + i * 7,
                     bx + (off + 0.22) * w - 4, y0 + 14 + i * 7],
                    fill=GREY, width=2)
    dr.line([bx + w * 0.245, y0 + 5, bx + w * 0.235, y0 + h * 0.32],
            fill=RED, width=2)
    dr.line([bx + w * 0.235, y0 + h * 0.32, bx + w * 0.25, y0 + h * 0.54],
            fill=RED, width=2)
    data_chip(dr, x0, y1, "ANTALYA · DEADLINE FRIDAY")


def scene_cyclone(dr, box):
    """Akvan's spiral over the Bay of Bengal, track to the coast."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    dr.rectangle(box, fill=rgb("7fa3bd"))
    coast = [(x0, y1), (x0, y0 + h * 0.26), (x0 + w * 0.15, y0 + h * 0.42),
             (x0 + w * 0.25, y0 + h * 0.60), (x0 + w * 0.38, y0 + h * 0.78),
             (x0 + w * 0.50, y1)]
    dr.polygon(coast, fill=rgb("e5d29a"))
    dr.line(coast[1:], fill=rgb("b89b57"), width=2)
    text(dr, x0 + 7, y0 + h * 0.33, "ODISHA", font(SANS_B, 8),
         fill=rgb("7a6428"))
    cx, cy = x0 + w * 0.72, y0 + h * 0.44
    for rad, start in ((25, 20), (18, 150), (11, 280)):
        dr.arc([cx - rad, cy - rad * 0.72, cx + rad, cy + rad * 0.72],
               start=start, end=start + 235, fill=WHITE, width=3)
    dr.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=NAVY)
    for i in range(6):
        rx = x0 + w * (0.56 + 0.07 * i)
        dr.line([rx, y0 + h * 0.76, rx - 5, y0 + h * 0.90],
                fill=rgb("d7e6f0"), width=2)
    for t in (0.3, 0.6, 0.9):
        px = cx + (x0 + w * 0.33 - cx) * t
        py = cy + (y0 + h * 0.64 - cy) * t
        dr.ellipse([px - 2, py - 2, px + 2, py + 2], fill=RED)
    data_chip(dr, x0, y1, "~50,000 MOVED · LANDFALL FRI")


# ---------------------------------------------------------------------------
# Dot-matrix world map. Coastline outlines (lon/lat polygons, the house
# data set shared by the sibling editions) are rasterised into a dot
# grid by point-in-polygon tests; numbered pins mark the panels.
# ---------------------------------------------------------------------------

def _poly(raw):
    pts = []
    for pair in raw.split(";"):
        lon_s, lat_s = pair.split(",")
        pts.append((int(lon_s), int(lat_s)))
    return pts


_COASTS = [
    "-168,65;-158,71;-140,70;-130,71;-120,71;-110,68;-100,69;-95,69;-90,69;-85,66;-82,66;-79,62;-76,60;-70,62;-65,60;-60,55;-55,52;-56,50;-60,46;-65,44;-68,44;-70,42;-74,39;-76,35;-79,33;-80,31;-80,27;-81,25;-82,27;-84,29;-87,30;-89,29;-94,29;-97,28;-97,25;-97,22;-94,17;-90,14;-87,13;-83,9;-79,9;-81,12;-85,15;-90,14;-94,16;-97,16;-102,19;-105,23;-108,25;-111,29;-114,31;-117,33;-120,34;-122,37;-123,40;-124,45;-124,48;-128,52;-132,55;-137,58;-145,60;-152,59;-156,58;-161,59;-165,60;-168,63",
    "-46,59;-40,63;-32,68;-22,70;-20,73;-25,78;-32,80;-45,80;-55,78;-58,75;-57,70;-55,65;-53,61",
    "-78,7;-75,10;-72,12;-68,11;-64,10;-61,9;-57,7;-54,6;-51,4;-50,1;-46,-1;-42,-3;-38,-5;-35,-8;-36,-10;-38,-13;-39,-18;-40,-21;-42,-23;-45,-24;-48,-26;-50,-29;-52,-32;-54,-34;-57,-37;-58,-39;-61,-39;-62,-41;-63,-43;-65,-45;-66,-47;-67,-49;-68,-51;-68,-53;-70,-54;-72,-54;-73,-51;-74,-48;-74,-44;-73,-40;-73,-36;-72,-31;-71,-27;-70,-22;-70,-18;-72,-16;-75,-14;-77,-11;-79,-8;-80,-5;-81,-3;-80,0;-79,2;-78,4",
    "-9,37;-9,43;-8,44;-4,44;-1,45;-2,47;-4,48;-1,50;1,51;3,52;5,53;7,54;8,55;7,57;8,58;10,59;7,59;5,60;5,62;8,63;11,65;14,67;17,69;21,70;26,71;31,71;38,69;44,68;48,66;50,64;48,62;44,60;42,58;40,56;38,55;35,55;33,54;31,52;30,51;28,50;27,48;29,46;28,45;29,43;28,41;27,40;26,39;27,38;26,37;24,37;23,36;22,37;21,38;20,39;19,40;16,39;15,38;12,38;13,41;12,43;10,44;7,44;3,43;0,40;-1,38;-2,37",
    "8,44;10,44;11,43;13,41;14,40;16,38;18,40;16,40;14,41;12,42;10,43;8,44",
    "-5,50;-3,50;-2,52;-3,55;-4,57;-3,58;-4,59;-6,58;-8,55;-6,54;-5,52",
    "-10,52;-8,52;-6,52;-6,54;-8,55;-10,54",
    "-6,35;-2,35;3,37;9,37;11,34;15,32;20,32;25,32;30,31;32,31;33,28;35,24;37,22;39,20;40,18;42,15;43,12;45,11;48,11;51,11;48,9;46,6;43,3;41,-1;40,-5;40,-9;39,-13;38,-17;37,-20;36,-23;35,-26;33,-28;31,-30;29,-32;27,-34;25,-34;22,-35;20,-35;19,-33;18,-31;17,-28;16,-24;15,-21;14,-18;13,-14;12,-11;11,-7;10,-4;9,-1;9,2;8,4;6,4;3,6;-1,5;-4,5;-7,4;-9,4;-12,7;-14,9;-16,12;-17,15;-17,18;-16,21;-16,24;-15,27;-14,29;-11,31;-8,33",
    "44,-12;47,-13;49,-15;50,-17;48,-20;46,-23;45,-25;44,-23;43,-20;43,-16",
    "26,41;28,41;30,42;31,44;30,46;31,48;30,50;32,52;34,54;36,55;39,55;42,57;44,59;46,62;48,64;50,66;55,68;62,69;68,70;73,71;78,72;84,73;90,74;96,76;102,77;108,77;113,74;118,73;124,72;130,71;136,71;142,72;148,71;154,70;160,69;166,67;172,66;178,65;173,62;168,61;163,60;159,57;157,53;156,51;153,49;150,46;145,45;142,43;141,41;139,39;137,36;134,35;131,34;129,33;126,31;123,30;121,28;120,26;119,24;116,23;112,22;109,20;108,17;107,14;106,10;104,7;102,6;100,7;99,10;98,13;97,15;95,16;93,17;91,16;90,19;89,21;88,22;86,20;84,19;82,16;80,14;78,9;77,8;76,10;75,13;73,16;72,19;70,21;68,23;66,25;63,25;60,25;57,26;55,25;53,26;51,28;50,29;49,30;48,29;50,27;52,25;54,24;56,24;58,23;59,22;57,21;55,20;53,18;51,16;49,14;47,13;45,12;43,13;42,15;41,17;40,20;39,22;37,24;35,28;34,31;34,34;36,36;35,37;33,36;31,36;29,36;27,37;26,38",
    "140,36;141,38;141,40;142,42;143,43;142,45;141,44;140,41;139,38;138,36",
    "131,32;132,33;134,34;135,35;133,34;131,33",
    "109,1;113,3;117,5;119,2;118,-1;115,-3;111,-3;109,-1",
    "95,5;99,3;103,-1;105,-4;106,-6;103,-4;99,0;96,3",
    "106,-6;110,-7;113,-7;114,-8;110,-8;106,-7",
    "119,0;121,1;123,0;121,-2;120,-4;119,-2",
    "131,-1;136,-2;141,-3;146,-4;149,-6;150,-8;147,-9;143,-7;138,-5;133,-3",
    "120,18;121,16;122,14;121,13;120,14;120,16",
    "113,-22;112,-25;114,-29;115,-32;115,-34;117,-35;120,-34;124,-33;127,-32;130,-32;132,-32;134,-33;135,-35;137,-36;139,-37;140,-38;143,-38;145,-38;147,-39;149,-38;150,-37;151,-34;153,-31;153,-28;153,-25;152,-23;150,-21;148,-19;146,-18;144,-15;143,-13;142,-11;141,-15;141,-17;140,-19;139,-18;137,-16;136,-15;135,-12;132,-11;130,-12;128,-13;126,-14;124,-16;122,-17;120,-19;118,-20;116,-21",
    "167,-45;169,-44;171,-43;172,-42;173,-40;174,-39;175,-37;176,-38;175,-40;173,-41;171,-42;169,-44;167,-46",
]

COASTS = [_poly(raw) for raw in _COASTS]


def _inside(lon, lat, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > lat) != (y2 > lat):
            xin = x1 + (lat - y1) * (x2 - x1) / (y2 - y1)
            if lon < xin:
                inside = not inside
    return inside


# (number, lon, lat, dx, dy, region) -- panel 3 is in deep space.
MAP_PINS = [
    (1, 47.5, 29.3, 8, 0, "mideast"),
    (2, 114.05, 22.55, 12, -8, "asia"),
    (4, 30.7, 46.5, 0, -4, "europe"),
    (5, 34.3, 31.4, -10, 8, "mideast"),
    (6, 39.5, 15.0, 2, 0, "africa"),
    (7, -77.0, 38.9, 0, 0, "americas"),
    (8, 90.4, 23.8, 10, -6, "asia"),
    (9, -74.0, 40.7, 0, -6, "americas"),
    (10, 30.7, 36.9, -14, 4, "global"),
    (11, 85.8, 19.8, -2, 10, "asia"),
]


def paint_map(dr, box):
    x0, y0, x1, y1 = box
    dr.rectangle(box, fill=SEA)
    w, h = x1 - x0, y1 - y0

    def project(lon, lat):
        return (x0 + (lon + 168) / 360.0 * w, y0 + (84 - lat) / 144.0 * h)

    lat = 82.5
    while lat > -58:
        lon = -166.5
        while lon < 190:
            for poly in COASTS:
                if _inside(lon, lat, poly):
                    px, py = project(lon, lat)
                    dr.ellipse([px - 1.6, py - 1.6, px + 1.6, py + 1.6],
                               fill=LAND_DOT)
                    break
            lon += 3.0
        lat -= 3.0
    for num, lon, lat_, dx, dy, region in MAP_PINS:
        px, py = project(lon, lat_)
        pin_disc(dr, px + dx, py + dy, 9, num, REGION_INK[region])
    # panel 3 sits off the map's top-right corner: deep space
    sx, sy = x1 - 34, y0 + 12
    pin_disc(dr, sx, sy, 9, 3, REGION_INK["global"])
    text(dr, sx, sy + 13, "DEEP SPACE", font(SANS_B, 6), fill=GREY,
         anchor="ma")
    dr.rectangle(box, outline=RULE, width=1)


# ---------------------------------------------------------------------------
# Page content. Panels: (number, region, field, kicker, source, tag,
# scene, headline, deck). Also: (number, region, field, text).
# ---------------------------------------------------------------------------

FIELD_NAME = {
    "diplomacy": "DIPLOMACY",
    "war": "WAR & SECURITY",
    "business": "BUSINESS & TECH",
    "climate": "CLIMATE & WEATHER",
    "politics": "POLITICS & COURTS",
    "science": "HEALTH & SCIENCE",
    "culture": "CULTURE & SPORT",
    "society": "SOCIETY",
}
FIELD_INK = {
    "diplomacy": rgb("2563b3"),
    "war": RED,
    "business": rgb("1e8449"),
    "climate": rgb("148f7a"),
    "politics": rgb("7d3c98"),
    "science": rgb("bc5f16"),
    "culture": rgb("b03a4b"),
    "society": rgb("5d6d7e"),
}

LEAD = [
    (1, "mideast", "war", "MIDDLE EAST · IRAN WAR", "REUTERS", "CLAIM",
     scene_gulf, "Iran fires on a US base in Kuwait; Bahrain stops new attacks",
     "Kuwait says its defences engaged hostile drones over Ali Al Salem; "
     "Bahrain says it intercepted attacks for the third time in a week, "
     "a day after the US strike on Qeshm."),
    (2, "asia", "diplomacy", "ASIA · APEC SUMMIT", "AP · AFP", "CONFIRMED",
     scene_summit, "Xi greets Trump in Shenzhen as APEC opens",
     "A rare airport welcome, talks with Putin the same day, and a "
     "first Trump–Xi–Putin summit set for Thursday."),
    (3, "global", "science", "GLOBAL · SPACE", "NASA", "CONFIRMED",
     scene_voyager, "Voyager 1 is one light-day from Earth, a first",
     "At 10:16 UTC the probe launched in 1977 passed 25.9 billion km; "
     "its radio signal now takes a full day to arrive."),
]

MINI_A = [
    (4, "europe", "war", "EUROPE · UKRAINE WAR", "REUTERS", "CONFIRMED",
     scene_strikes, "Russian strikes kill five; EU offers Kyiv a €45bn loan",
     "Four die in Odesa's historic centre as Kyiv counts 141 drones "
     "overnight; the loan is repaid only once Russia pays reparations."),
    (5, "mideast", "war", "MIDDLE EAST · GAZA", "AL JAZEERA · BBC",
     "CONFIRMED", scene_gaza,
     "Israel makes first ground push in central Gaza since truce",
     "Tanks cross the Yellow Line near Nuseirat; hospitals count "
     "three dead and the army cites a threat."),
    (6, "africa", "war", "AFRICA · HORN", "REUTERS", "CONFIRMED",
     scene_horn, "Ethiopia and Eritrea mass troops on their border",
     "Both sides move forces within striking distance, monitors say; "
     "Eritrea calls the reports propaganda."),
    (7, "americas", "politics", "AMERICAS · US POLITICS", "AL JAZEERA",
     "CONFIRMED", scene_speaker,
     "House Democrats pick Jeffries for Speaker, 251–11",
     "The first Black nominee for the job; the full House votes "
     "on 3 January."),
]

MINI_B = [
    (8, "asia", "society", "ASIA · LABOUR", "DAILY STAR", "CONFIRMED",
     scene_garment, "Bangladesh wage protests shut 55 garment factories",
     "Workers block a highway in Gazipur; police report about "
     "300 arrests."),
    (9, "americas", "business", "AMERICAS · BUSINESS", "AL JAZEERA",
     "CONFIRMED", scene_ipo, "Anthropic prices the biggest IPO ever: $81.3bn",
     "At $83 a share, above its range; trading in ANT starts "
     "on Thursday."),
    (10, "global", "climate", "GLOBAL · CLIMATE", "AFP · AGENCIES",
     "CONFIRMED", scene_cop, "COP31 still split over a fossil-fuel phase-out",
     "Arab states and Russia reject the draft text in Antalya; "
     "ministers face a Friday deadline."),
    (11, "asia", "climate", "ASIA · WEATHER", "PTI", "FORECAST",
     scene_cyclone, "Cyclone Akvan turns towards India's Odisha coast",
     "Nearly 50,000 people are moved to safety; landfall is "
     "forecast near Puri on Friday."),
]

ALSO = [
    (12, "americas", "business", "Fed minutes point to more rate rises; Dow drops 561"),
    (13, "africa", "science", "WHO keeps Congo Ebola outbreak a global emergency; 11,000+ cases"),
    (14, "europe", "war", "Crimea: Kerch Bridge road span falls after a second day of strikes"),
    (15, "europe", "business", "UK: inflation rises to 3.6%, diesel at a record high"),
    (16, "europe", "diplomacy", "Russia and Ukraine agree their largest prisoner swap yet"),
    (17, "mideast", "war", "Third US carrier reaches the Middle East; tankers hit near Hormuz"),
    (18, "mideast", "war", "Saudi Arabia says it intercepted a Houthi cruise missile"),
    (19, "mideast", "politics", "UK and Australia sanction settler leader Daniella Weiss"),
    (20, "americas", "diplomacy", "US and Venezuela announce a defence partnership"),
    (21, "americas", "war", "Haiti: Salvadoran troops raid a gang chief's home in Canaan"),
    (22, "asia", "diplomacy", "Trump announces Philippines trade deal; Manila: an understanding"),
    (23, "asia", "politics", "Myanmar: the ICJ sets its Rohingya genocide ruling"),
    (24, "americas", "business", "Waymo halts driverless freeway rides amid safety concerns"),
    (25, "americas", "society", "Brazil: rare contact reported with an isolated Amazon group"),
    (26, "mideast", "war", "Tanker attacked near Hormuz: one crew missing, 11 hurt"),
    (27, "europe", "war", "Russian military plane crashes; all 19 aboard are killed"),
    (28, "europe", "politics", "Slovakia: thousands protest the Fico government in Bratislava"),
    (29, "asia", "war", "Kashmir: Indian forces kill a militant commander"),
    (30, "asia", "diplomacy", "Japan: PM Takaichi meets Putin, a first since 2022"),
    (31, "asia", "business", "Seoul: Kospi jumps 2% as chip shares rally"),
    (32, "europe", "politics", "Germany: coalition agrees a power-tax cut for all"),
    (33, "europe", "diplomacy", "UK: Lammy urges Burnham to back rejoining the EU"),
    (34, "europe", "war", "Ukraine hits two Krasnodar oil refineries"),
    (35, "europe", "war", "Zaporizhzhia: 85 children ordered out of Balabyne"),
    (36, "global", "politics", "UN rights chief voices concern over the EU–Rwanda transfer plan"),
    (37, "africa", "society", "Senegal: migrant boat capsizes; at least one dead"),
    (38, "africa", "business", "Uganda agrees with Tanzania to speed up an oil pipeline"),
    (39, "global", "business", "Gold falls to a 14-month low, below $3,750 an ounce"),
    (40, "global", "business", "Oil: Brent settles 1.3% lower at $91.95"),
    (41, "europe", "culture", "Football: Chelsea women beat PSG 1–0 in Europe"),
    (42, "europe", "culture", "Turin: Alcaraz beats Medvedev at the ATP Finals"),
    (43, "global", "society", "Pew: Islam is set to be the largest religion by 2035"),
    (44, "oceania", "culture", "GTA VI's midnight launch begins in New Zealand"),
]

STATS = [
    ("€45bn", "EU loan offered to Kyiv"),
    ("141", "drones counted over Ukraine"),
    ("11,000+", "Ebola cases in DR Congo"),
    ("561", "points the Dow lost on the day"),
]


# ---------------------------------------------------------------------------
# Panel and page composition
# ---------------------------------------------------------------------------

def render_panel(dr, box, spec, big):
    num, region, _field, kicker, source, tag, scene, head, deck = spec
    x0, y0, x1, y1 = box
    dr.rectangle(box, fill=CARD, outline=RULE, width=1)
    art_h = 68 if big else 54
    scene(dr, (x0 + 1, y0 + 1, x1 - 1, y0 + art_h))
    cert_stamp(dr, x1 - 6, y0 + 11, tag)
    dr.line([x0, y0 + art_h, x1, y0 + art_h], fill=RULE, width=1)
    inner_w = (x1 - x0) - 16
    tx = x0 + 8
    ty = y0 + art_h + 5
    chip = 20 if big else 17
    number_box(dr, tx + chip // 2, ty + chip // 2, num, chip, GOLD,
               glyph=NAVY)
    text(dr, tx + chip + 6, ty + (3 if big else 2), kicker,
         font(SANS_B, 11 if big else 9), fill=REGION_INK[region])
    text_r(dr, x1 - 8, ty + (3 if big else 2), source, font(SANS_B, 8),
           fill=GREY)
    ty += chip + 4
    hfont = shrink_to_fit(dr, head, SERIF_B, inner_w, 2,
                          18 if big else 15, 11)
    ty = stack(dr, tx, ty, wrap_text(dr, head, hfont, inner_w), hfont,
               int(hfont.size * 1.16))
    dfont = shrink_to_fit(dr, deck, SANS, inner_w, 3,
                          10.5 if big else 10, 8.5)
    stack(dr, tx, ty + 2, wrap_text(dr, deck, dfont, inner_w), dfont,
          int(dfont.size * 1.32), fill=BODY)


def masthead(dr):
    dr.rectangle([0, 0, PAGE, 98], fill=NAVY)
    dr.rectangle([MARGIN, 11, MARGIN + 60, 87], fill=RED)
    text(dr, MARGIN + 30, 17, "NOV", font(SANS_B, 11), fill=WHITE,
         anchor="ma")
    text(dr, MARGIN + 30, 28, "18", font(SERIF_BLK, 32), fill=WHITE,
         anchor="ma")
    text(dr, MARGIN + 30, 68, "WED · 2026", font(SANS_B, 8), fill=WHITE,
         anchor="ma")
    tracked(dr, 88, 10, "THE WORLD IN A DAY", font(SANS_B, 13), GOLD_LT,
            gap=3)
    text(dr, 88, 26, "Wednesday 18 November 2026", font(SERIF_BLK, 36),
         fill=WHITE)
    text(dr, 88, 72,
         "Everything on this page happened, or was first reported, on "
         "Wednesday 18 November 2026.", font(SERIF_I, 12), fill=CREAM)
    text_r(dr, PAGE - MARGIN, 12, "44 STORIES", font(SERIF_B, 17),
           fill=WHITE)
    text_r(dr, PAGE - MARGIN, 36, "7 REGIONS · ONE PAGE",
           font(SANS_B, 10), fill=GOLD_LT)
    text_r(dr, PAGE - MARGIN - 196, 66, "HOW SURE:", font(SANS_B, 8),
           fill=CREAM)
    x = PAGE - MARGIN
    for tag in ("FORECAST", "CLAIM", "CONFIRMED"):
        w = cert_stamp(dr, x, 66, tag)
        x -= w + 6


def taxonomy(dr):
    counts = {}
    for spec in LEAD + MINI_A + MINI_B:
        counts[spec[2]] = counts.get(spec[2], 0) + 1
    for _n, _r, field, _t in ALSO:
        counts[field] = counts.get(field, 0) + 1
    short = {"diplomacy": "DIPLOMACY", "war": "WAR", "business": "BUSINESS",
             "climate": "CLIMATE", "politics": "POLITICS",
             "science": "SCIENCE", "culture": "CULTURE",
             "society": "SOCIETY"}
    total = sum(counts.values())
    x = MARGIN
    y0, y1 = 102, 122
    for field, count in sorted(counts.items(), key=lambda kv: -kv[1]):
        w = WIDTH * count / total
        dr.rectangle([x, y0, x + w - 2, y1], fill=FIELD_INK[field])
        label = f"{short[field]} {count}"
        fnt = shrink_to_fit(dr, label, SANS_B, w - 8, 1, 9, 7)
        text(dr, x + (w - 2) / 2, y0 + 10, label, fnt, fill=WHITE,
             anchor="mm")
        x += w


def timeline(dr):
    y = 130
    text(dr, MARGIN, y, "THE DAY IN UTC", font(SANS_B, 10), fill=NAVY)
    items = ["OVERNIGHT Iran fires on Kuwait",
             "07:00 UK inflation: 3.6%",
             "MORNING Xi greets Trump in Shenzhen",
             "10:16 Voyager 1: one light-day",
             "19:00 Fed minutes: more hikes",
             "CLOSE Dow down 561"]
    line = "   ·   ".join(items)
    fnt = shrink_to_fit(dr, line, SANS, WIDTH - 118, 1, 10.5, 8)
    text(dr, MARGIN + 118, y, line, fnt, fill=BODY)
    dr.line([MARGIN, y + 17, PAGE - MARGIN, y + 17], fill=RULE, width=1)


def bottom_left(dr):
    tracked(dr, MARGIN, 678, "WHERE IT HAPPENED", font(SANS_B, 13), NAVY,
            gap=1)
    dr.line([MARGIN, 696, MARGIN + 342, 696], fill=INK, width=2)
    paint_map(dr, (MARGIN, 704, MARGIN + 342, 856))
    legend = [("Europe", "europe"), ("Asia", "asia"),
              ("Americas", "americas"), ("Middle East", "mideast"),
              ("Africa", "africa"), ("Global", "global")]
    lx = MARGIN
    for name, key in legend:
        dr.ellipse([lx, 864, lx + 8, 872], fill=REGION_INK[key])
        text(dr, lx + 12, 862, name, font(SANS, 9.5))
        lx += 16 + text_w(dr, name, font(SANS, 9.5)) + 10
    text(dr, MARGIN, 878,
         "Numbered pins are stories 1–11; pin 3 (Voyager 1) is in "
         "deep space.", font(SANS, 9), fill=GREY)
    sy = 896
    for i, (big, cap) in enumerate(STATS):
        cx = MARGIN + (i % 2) * 174
        cy = sy + (i // 2) * 33
        text(dr, cx, cy, big, font(SERIF_B, 16), fill=NAVY)
        capf = shrink_to_fit(dr, cap, SANS, 168, 1, 8.5, 7)
        text(dr, cx, cy + 20, cap, capf, fill=GREY)


def bottom_right(dr):
    x0 = MARGIN + 356
    tracked(dr, x0, 678, "ALSO ON WEDNESDAY 18 NOVEMBER",
            font(SANS_B, 13), NAVY, gap=1)
    text_r(dr, PAGE - MARGIN, 678, "33 MORE STORIES", font(SANS_B, 10),
           fill=GREY)
    dr.line([x0, 696, PAGE - MARGIN, 696], fill=INK, width=2)
    col_w = (PAGE - MARGIN - x0 - 16) // 2
    halves = [ALSO[:17], ALSO[17:]]
    for ci, items in enumerate(halves):
        cx = x0 + ci * (col_w + 16)
        iy = 706
        for num, region, _field, line in items:
            pin_disc(dr, cx + 8, iy + 6, 7, num, REGION_INK[region])
            fnt = shrink_to_fit(dr, line, SANS, col_w - 22, 1, 11, 9)
            text(dr, cx + 21, iy, line, fnt)
            iy += 14.8


def date_check(dr):
    y0, y1 = 960, 992
    dr.rectangle([MARGIN, y0, PAGE - MARGIN, y1], fill=rgb("f3e0da"),
                 outline=RED, width=1)
    title = ("DATE CHECK — LEFT OUT ON PURPOSE, FIRST REPORTED BEFORE "
             "WEDNESDAY:  ")
    body = ("Peltola's Alaska Senate win, the PAHO measles ruling, "
            "Nvidia's results, the Board of Peace's Gaza warning, the "
            "US strike on Qeshm and the Knesset speaker vote (all Tue "
            "17 Nov). Not yet: Thursday's trilateral summit and "
            "Anthropic's first trading day.")
    fnt = font(SANS, 9.5)
    lines = wrap_text(dr, title + body, fnt, WIDTH - 20)
    ty = y0 + 6
    for line in lines[:2]:
        text(dr, MARGIN + 10, ty, line, fnt, fill=BODY)
        ty += 13


def footer(dr):
    dr.line([MARGIN, 996, PAGE - MARGIN, 996], fill=INK, width=1)
    text(dr, MARGIN, 1003,
         "Every story happened, or was first reported, on Wednesday "
         "18 November 2026; contested claims are marked as claims. "
         "Original drawings.", font(SANS, 9.5), fill=GREY)
    text_r(dr, PAGE - MARGIN, 1003,
           "Sources: Reuters · AP · AFP · BBC · Al Jazeera · NASA · "
           "WHO · PTI", font(SANS, 9.5), fill=GREY)


def compose():
    img = Image.new("RGB", (PAGE, PAGE), PAPER)
    dr = ImageDraw.Draw(img)
    masthead(dr)
    taxonomy(dr)
    timeline(dr)
    edges = [MARGIN + round(i * WIDTH / 3) for i in range(4)]
    for i, spec in enumerate(LEAD):
        render_panel(dr, (edges[i] + (5 if i else 0), 154,
                          edges[i + 1] - (5 if i < 2 else 0), 344),
                     spec, big=True)
    edges = [MARGIN + round(i * WIDTH / 4) for i in range(5)]
    for specs, (ry0, ry1) in ((MINI_A, (350, 508)), (MINI_B, (514, 672))):
        for c, spec in enumerate(specs):
            render_panel(dr, (edges[c] + (5 if c else 0), ry0,
                              edges[c + 1] - (5 if c < 3 else 0), ry1),
                         spec, big=False)
    bottom_left(dr)
    bottom_right(dr)
    date_check(dr)
    footer(dr)
    return img


def main():
    import hashlib
    img = compose()
    img.save(OUT, format="PNG")
    data = open(OUT, "rb").read()
    print("wrote", OUT, len(data), "bytes, sha256",
          hashlib.sha256(data).hexdigest())


if __name__ == "__main__":
    main()
