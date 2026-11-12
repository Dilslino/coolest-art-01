#!/usr/bin/env python3
"""ONE THOUSAND FOLDS - coolest-art-01 V2 entry.

A colossal origami paper crane in flat cream flies toward a giant flat
vermilion sun over an indigo sea, above a tiny coastal village with a red
torii gate, tiny fishermen in boats, and Hokusai sine-wave curves.
Ukiyo-e palette, procedural 5x7 bitmap title, hanko seal.
Pure Python 3.13 standard library. Deterministic: same bytes every run.
"""

import math
import os
import random
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- palette
def hx(s):
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))

DEEP      = hx("101D42")
INDIGO_A  = hx("16294F")
INDIGO_B  = hx("1E3566")
INDIGO_C  = hx("2A4480")
HORIZON   = hx("33508C")
SEA_TOP   = hx("0C1836")
SEA_BOT   = hx("081020")
VERMILION = hx("D9381E")
CLOUD_DK  = hx("8A1F14")
CLOUD_MD  = hx("A82618")
CREAM     = hx("FFF6E0")
CREAM_DK  = hx("EAD9A8")
GOLD      = hx("E8C878")
GOLD_FOLD = hx("D9B96A")
WARM_GOLD = hx("FFC46B")
DARK      = hx("0A0F24")
WALL      = hx("F5E6C8")
ROOF      = hx("1A2340")
TEXT_C    = hx("FFF3D6")
WHITE     = (255, 255, 255)
STAR_WM   = hx("FFD9A0")

# canvas: RGB bytearray
px = bytearray(W * H * 3)

# ---------------------------------------------------------------- helpers
def _put(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        px[i] = c[0]
        px[i + 1] = c[1]
        px[i + 2] = c[2]

def fill_rect(x0, y0, x1, y1, c):
    x0 = max(int(x0), 0)
    y0 = max(int(y0), 0)
    x1 = min(int(x1), W - 1)
    y1 = min(int(y1), H - 1)
    if x1 < x0 or y1 < y0:
        return
    row = bytes(c) * (x1 - x0 + 1)
    n = (x1 - x0 + 1) * 3
    for y in range(y0, y1 + 1):
        s = (y * W + x0) * 3
        px[s:s + n] = row

def fill_poly(pts, c):
    n = len(pts)
    if n < 3:
        return
    edges = []
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        if y0 == y1:
            continue
        if y0 < y1:
            edges.append((y0, y1, x0, (x1 - x0) / (y1 - y0)))
        else:
            edges.append((y1, y0, x1, (x0 - x1) / (y0 - y1)))
    if not edges:
        return
    y_lo = int(math.floor(min(e[0] for e in edges)))
    y_hi = int(math.ceil(max(e[1] for e in edges)))
    cb = bytes(c)
    for y in range(max(y_lo, 0), min(y_hi, H - 1) + 1):
        xs = []
        for (ymin, ymax, x_at_min, slope) in edges:
            if ymin <= y < ymax:
                xs.append(x_at_min + slope * (y - ymin))
        if len(xs) < 2:
            continue
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            xa = int(math.ceil(xs[k]))
            xb = int(math.floor(xs[k + 1]))
            if xb < xa:
                continue
            xa = max(xa, 0)
            xb = min(xb, W - 1)
            if xb < xa:
                continue
            s = (y * W + xa) * 3
            px[s:s + (xb - xa + 1) * 3] = cb * (xb - xa + 1)

def fill_disc(cx, cy, r, c):
    cb = bytes(c)
    for y in range(max(cy - r, 0), min(cy + r, H - 1) + 1):
        dy = y - cy
        dx = int(math.sqrt(r * r - dy * dy))
        xa = max(cx - dx, 0)
        xb = min(cx + dx, W - 1)
        s = (y * W + xa) * 3
        px[s:s + (xb - xa + 1) * 3] = cb * (xb - xa + 1)

def fill_ellipse(cx, cy, rx, ry, c):
    cb = bytes(c)
    for y in range(max(cy - ry, 0), min(cy + ry, H - 1) + 1):
        dy = (y - cy) / ry
        dx = int(rx * math.sqrt(max(0.0, 1.0 - dy * dy)))
        xa = max(cx - dx, 0)
        xb = min(cx + dx, W - 1)
        s = (y * W + xa) * 3
        px[s:s + (xb - xa + 1) * 3] = cb * (xb - xa + 1)

def thick_line(x0, y0, x1, y1, w, c):
    dx = x1 - x0
    dy = y1 - y0
    L = math.hypot(dx, dy)
    if L == 0:
        return
    nx = -dy / L * (w / 2.0)
    ny = dx / L * (w / 2.0)
    fill_poly([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny),
               (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)], c)

def lerp_c(c0, c1, t):
    return (round(c0[0] + (c1[0] - c0[0]) * t),
            round(c0[1] + (c1[1] - c0[1]) * t),
            round(c0[2] + (c1[2] - c0[2]) * t))

def grad_color(stops, y):
    for i in range(len(stops) - 1):
        y0, c0 = stops[i]
        y1, c1 = stops[i + 1]
        if y0 <= y <= y1:
            t = 0.0 if y1 == y0 else (y - y0) / (y1 - y0)
            return lerp_c(c0, c1, t)
    return stops[-1][1]

# ---------------------------------------------------------------- bitmap font (5x7, cell 4px)
FONT = {
    'O': ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    'N': ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    'E': ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    'T': ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    'H': ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    'U': ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    'S': ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    'A': ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    'D': ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    'F': ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    'L': ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
}

def draw_text(s, x0, y0, c):
    for i, ch in enumerate(s):
        if ch == ' ':
            continue
        g = FONT[ch]
        cx = x0 + i * 24
        for r in range(7):
            row = g[r]
            for col in range(5):
                if row[col] == '1':
                    fill_rect(cx + col * 4, y0 + r * 4,
                              cx + col * 4 + 3, y0 + r * 4 + 3, c)

# ---------------------------------------------------------------- PNG encoder
def png_chunk(typ, data):
    return (struct.pack(">I", len(data)) + typ + data +
            struct.pack(">I", zlib.crc32(typ + data) & 0xffffffff))

def write_png(path):
    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter: none
        raw += px[y * W * 3:(y + 1) * W * 3]
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    out = b"\x89PNG\r\n\x1a\n"
    out += png_chunk(b"IHDR", ihdr)
    out += png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    out += png_chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(out)

# ---------------------------------------------------------------- scene
def main():
    # 1. sky gradient (per row)
    sky_stops = [(0, DEEP), (200, INDIGO_A), (400, INDIGO_B),
                 (550, INDIGO_C), (700, HORIZON)]
    for y in range(0, 700):
        c = grad_color(sky_stops, y)
        s = y * W * 3
        px[s:s + W * 3] = bytes(c) * W
    # sea gradient
    sea_stops = [(700, SEA_TOP), (1024, SEA_BOT)]
    for y in range(700, H):
        c = grad_color(sea_stops, y)
        s = y * W * 3
        px[s:s + W * 3] = bytes(c) * W

    # 2. stars (top region only, fixed seed)
    rng = random.Random(777)
    for _ in range(35):
        x = rng.randrange(0, W)
        y = rng.randrange(0, 251)
        sz = 1 if rng.random() < 0.5 else 2
        c = WHITE if rng.random() < 0.6 else STAR_WM
        fill_rect(x, y, x + sz - 1, y + sz - 1, c)

    # 3. red cloud bands (before the sun)
    for (cx, cy, rx, ry) in [(90, 170, 80, 12), (190, 165, 100, 14),
                              (300, 172, 90, 12), (380, 168, 70, 11)]:
        fill_ellipse(cx, cy, rx, ry, CLOUD_DK)
    for (cx, cy, rx, ry) in [(120, 540, 85, 13), (230, 535, 105, 15),
                              (340, 542, 90, 12), (440, 538, 70, 11)]:
        fill_ellipse(cx, cy, rx, ry, CLOUD_MD)

    # 4. vermilion sun disc (flat)
    fill_disc(720, 290, 150, VERMILION)

    # 5. sea waves: cream sine + parallel gold sine
    for cy in (760, 830, 900, 985):
        for x in range(W):
            ph = 2 * math.pi * x / 150.0
            y = int(round(cy + 12 * math.sin(ph)))
            _put(x, y - 1, CREAM)
            _put(x, y, CREAM)
            _put(x, y + 1, CREAM)
            gy = int(round(cy + 6 + 12 * math.sin(ph)))
            _put(x, gy, GOLD)
            _put(x, gy + 1, GOLD)
    # sun reflection bars (after waves)
    for (y, wdt, c) in [(735, 90, VERMILION), (770, 65, GOLD),
                         (805, 45, VERMILION), (840, 30, GOLD)]:
        x0 = 720 - wdt // 2
        fill_rect(x0, y, x0 + wdt - 1, y + 3, c)

    # 6. island + village + figures + torii
    fill_poly([(0, 700), (340, 700), (300, 665), (180, 655),
               (60, 668), (0, 675)], DARK)
    houses = [
        ((40, 632, 35, 28), (38, 632, 77, 632, 58, 618), [(55, 645)]),
        ((90, 628, 40, 32), (88, 628, 132, 628, 110, 612), [(105, 642)]),
        ((150, 636, 35, 24), (148, 636, 187, 636, 168, 622), []),
        ((200, 630, 40, 30), (198, 630, 242, 630, 220, 614), [(215, 644)]),
        ((255, 640, 30, 20), (253, 640, 287, 640, 270, 628), []),
    ]
    for (wx, wy, ww, wh), (rx0, ry0, rx1, ry1, rtx, rty), wins in houses:
        fill_rect(wx, wy, wx + ww - 1, wy + wh - 1, WALL)
        fill_poly([(rx0, ry0), (rx1, ry1), (rtx, rty)], ROOF)
        for (vx, vy) in wins:
            fill_rect(vx, vy, vx + 1, vy + 2, WARM_GOLD)
    # tiny figures looking up at the crane
    for fx in (100, 160, 220):
        fill_rect(fx, 652, fx + 2, 659, DARK)
    # torii gate (vermilion)
    fill_rect(298, 615, 301, 659, VERMILION)
    fill_rect(318, 615, 321, 659, VERMILION)
    fill_rect(292, 612, 327, 617, VERMILION)
    fill_rect(296, 626, 323, 629, VERMILION)

    # 7. boats
    fill_poly([(680, 820), (720, 820), (714, 832), (686, 832)], DARK)
    fill_rect(699, 795, 700, 820, DARK)          # mast
    fill_poly([(700, 795), (700, 820), (716, 820)], CREAM)  # sail
    fill_rect(698, 813, 700, 819, DARK)          # fisherman 1
    fill_poly([(405, 905), (435, 905), (430, 914), (410, 914)], DARK)
    fill_rect(418, 899, 420, 904, DARK)          # fisherman 2

    # 8. crane far wing (darker cream, behind body)
    fill_poly([(400, 412), (520, 404), (330, 235)], CREAM_DK)
    # 9. body diamond (two triangles)
    fill_poly([(615, 432), (248, 448), (430, 382)], CREAM)
    fill_poly([(615, 432), (430, 478), (248, 448)], CREAM)
    # 10. neck + head + beak (neck base lowered into the body so the
    # neck-body join is solid cream with no sky showing through)
    fill_poly([(548, 425), (578, 438), (714, 308), (698, 292)], CREAM)
    fill_poly([(698, 292), (714, 308), (738, 300)], CREAM)
    fill_poly([(738, 300), (762, 308), (738, 316)], VERMILION)
    # 11. near wing (big triangle, cream)
    fill_poly([(360, 398), (540, 392), (215, 155)], CREAM)
    # 12. tail (flat triangle)
    fill_poly([(255, 435), (145, 510), (275, 468)], CREAM)
    # 13. fold lines (gold, inside their shapes)
    thick_line(400, 394, 265, 225, 3, GOLD_FOLD)
    thick_line(255, 450, 175, 490, 2, GOLD_FOLD)

    # 14. title
    draw_text("ONE THOUSAND FOLDS", 296, 930, TEXT_C)

    # 15. hanko seal (bottom-right)
    fill_rect(940, 940, 965, 965, VERMILION)
    fill_rect(945, 945, 960, 946, WHITE)
    fill_rect(945, 959, 960, 960, WHITE)
    fill_rect(945, 945, 946, 960, WHITE)
    fill_rect(959, 945, 960, 960, WHITE)
    fill_rect(948, 952, 957, 954, WHITE)

    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    write_png(os.path.join(outdir, "entry.png"))

if __name__ == "__main__":
    main()
