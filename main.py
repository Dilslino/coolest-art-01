#!/usr/bin/env python3
"""THE SKY IS AN OCEAN -- coolest-art-01 entry.

A colossal whale in pure dark silhouette swims across a giant low sun at
dusk, over a tiny city skyline, above a dark sea. 1024x1024 RGB PNG,
drawn procedurally with the Python standard library only. Deterministic:
the same bytes on every run (no clock, no network, no unseeded random).
"""

import os
import random
import struct
import zlib
from math import sqrt

W = 1024
H = 1024


def hx(s):
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


SKY_STOPS = [
    (0, hx("0E0E2A")),
    (200, hx("1E1C4A")),
    (380, hx("4A2A58")),
    (560, hx("A34A3C")),
    (720, hx("E07B39")),
    (820, hx("F5A83D")),
    (880, hx("3A1F3D")),
    (1024, hx("0A0A18")),
]

SUN_OUTER = hx("FFB347")
SUN_CORE = hx("FFD27A")
GLOW_INNER = hx("FFC46B")
WHALE = hx("10182E")
CLOUD_A = hx("3A2050")
CLOUD_B = hx("8A4030")
BIRD = hx("14142A")
CITY = hx("0C0C1E")
WINDOW = hx("FFC46B")
SEA = hx("08081A")
SPOUT = hx("FFD9A0")
TITLE = hx("FFF3D6")
STAR_WARM = hx("FFD9A0")
ANTENNA_DOT = hx("FF4D4D")
WHITE = (255, 255, 255)

# ------------------------------------------------------------------ canvas

img = [bytearray(W * 3) for _ in range(H)]


def fill_row(y, color):
    img[y][:] = bytes(color) * W


def span(y, x0, x1, color):
    if y < 0 or y >= H:
        return
    x0 = max(0, x0)
    x1 = min(W, x1)
    if x0 >= x1:
        return
    img[y][x0 * 3:x1 * 3] = bytes(color) * (x1 - x0)


def rect(x0, y0, x1, y1, color):
    for y in range(max(0, y0), min(H, y1)):
        span(y, x0, x1, color)


def disc(cx, cy, r, color):
    r2 = r * r
    y0 = max(0, cy - r)
    y1 = min(H - 1, cy + r)
    for y in range(y0, y1 + 1):
        dy = y - cy
        dx = int(sqrt(r2 - dy * dy))
        span(y, cx - dx, cx + dx + 1, color)


def ellipse(cx, cy, rx, ry, color):
    y0 = max(0, cy - ry)
    y1 = min(H - 1, cy + ry)
    for y in range(y0, y1 + 1):
        dy = (y - cy) / ry
        dx = int(rx * sqrt(max(0.0, 1.0 - dy * dy)))
        span(y, cx - dx, cx + dx + 1, color)


def triangle(p1, p2, p3, color):
    pts = sorted((p1, p2, p3), key=lambda p: p[1])
    (x1, y1), (x2, y2), (x3, y3) = pts

    def ix(xa, ya, xb, yb, y):
        if yb == ya:
            return float(xa)
        return xa + (xb - xa) * (y - ya) / (yb - ya)

    for y in range(max(0, y1), min(H - 1, y3) + 1):
        if y < y2:
            xa = ix(x1, y1, x2, y2, y)
            xb = ix(x1, y1, x3, y3, y)
        else:
            xa = ix(x2, y2, x3, y3, y)
            xb = ix(x1, y1, x3, y3, y)
        span(y, int(min(xa, xb)), int(max(xa, xb)) + 1, color)


def thick_line(x0, y0, x1, y1, color, w):
    steps = max(abs(x1 - x0), abs(y1 - y0), 1) + 1
    half = w // 2
    for i in range(steps + 1):
        t = i / steps
        x = int(round(x0 + (x1 - x0) * t))
        y = int(round(y0 + (y1 - y0) * t))
        for yy in range(y - half, y + half + 1):
            span(yy, x - half, x + half + 1, color)


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def sky_at(y):
    for i in range(len(SKY_STOPS) - 1):
        y0, c0 = SKY_STOPS[i]
        y1, c1 = SKY_STOPS[i + 1]
        if y0 <= y <= y1:
            t = 0.0 if y1 == y0 else (y - y0) / (y1 - y0)
            return lerp(c0, c1, t)
    return SKY_STOPS[-1][1]


# ------------------------------------------------------------------ font

FONT = {
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
}


def draw_text(text, y0, color):
    cell = 4
    adv = 24
    total = len(text) * adv - 4
    x = 512 - total // 2
    for ch in text:
        if ch == " ":
            x += adv
            continue
        glyph = FONT[ch]
        for r in range(7):
            row = glyph[r]
            for c in range(5):
                if row[c] == "1":
                    rect(x + c * cell, y0 + r * cell,
                         x + c * cell + cell, y0 + r * cell + cell, color)
        x += adv


# ------------------------------------------------------------------ scene

def draw():
    # 1. sky gradient, one colour per row
    for y in range(H):
        fill_row(y, sky_at(y))

    # 2. stars, top region only
    rng = random.Random(12345)
    for _ in range(50):
        x = rng.randrange(0, W)
        y = rng.randrange(0, 321)
        s = 1 if rng.random() < 0.6 else 2
        c = WHITE if rng.random() < 0.7 else STAR_WARM
        rect(x, y, x + s, y + s, c)

    # 3. sun glow: 24 concentric discs, largest first, sky -> warm amber
    base = sky_at(610)
    for i in range(24):
        r = 405 - 5 * i
        disc(512, 610, r, lerp(base, GLOW_INNER, i / 23.0))

    # 4. clouds, behind the sun
    for (cx, cy, rx, ry) in [(120, 400, 90, 14), (220, 395, 110, 16),
                             (330, 402, 100, 13), (430, 398, 80, 12)]:
        ellipse(cx, cy, rx, ry, CLOUD_A)
    for (cx, cy, rx, ry) in [(620, 690, 90, 13), (730, 685, 110, 15),
                             (850, 692, 95, 12), (940, 688, 70, 11)]:
        ellipse(cx, cy, rx, ry, CLOUD_B)

    # 5. sun disc, two-tone
    disc(512, 610, 285, SUN_OUTER)
    disc(512, 610, 210, SUN_CORE)

    # 6. whale: chain of overlapping discs, fins, spout
    spine = [(195, 562, 50), (250, 550, 68), (310, 540, 82),
             (375, 532, 92), (445, 530, 95), (515, 533, 90),
             (580, 542, 78), (640, 552, 62), (695, 558, 45),
             (730, 562, 32)]
    for (cx, cy, r) in spine:
        disc(cx, cy, r, WHALE)
    triangle((730, 562), (830, 478), (812, 548), WHALE)   # tail, upper lobe
    triangle((730, 562), (828, 648), (808, 578), WHALE)   # tail, lower lobe
    triangle((555, 445), (600, 405), (615, 452), WHALE)   # dorsal fin
    triangle((430, 615), (480, 665), (455, 608), WHALE)   # pectoral fin
    thick_line(300, 452, 288, 418, SPOUT, 3)
    thick_line(300, 452, 300, 410, SPOUT, 3)
    thick_line(300, 452, 312, 418, SPOUT, 3)
    for (dx, dy) in [(288, 412), (300, 404), (312, 412)]:
        rect(dx, dy, dx + 2, dy + 2, SPOUT)

    # 7. birds: six small chevrons
    for (bx, by) in [(140, 330), (260, 360), (420, 315),
                     (640, 345), (780, 395), (900, 330)]:
        thick_line(bx, by, bx + 6, by + 6, BIRD, 2)
        thick_line(bx + 6, by + 6, bx + 12, by, BIRD, 2)

    # 8. city skyline
    rng2 = random.Random(777)
    x = 0
    buildings = []
    while x < W:
        w = rng2.randrange(30, 91)
        top = rng2.randrange(790, 861)
        buildings.append((x, top, min(W, x + w)))
        x += w
    for (bx0, top, bx1) in buildings:
        rect(bx0, top, bx1, H, CITY)
    for idx in (2, 7, 12):  # set-back tops
        if idx < len(buildings):
            bx0, top, bx1 = buildings[idx]
            w = bx1 - bx0
            rect(bx0 + w // 4, top - 26, bx1 - w // 4, top, CITY)
    antennas = []
    for idx in (4, 9, 15):  # antenna spires
        if idx < len(buildings):
            bx0, top, bx1 = buildings[idx]
            ax = (bx0 + bx1) // 2
            hgt = rng2.randrange(20, 41)
            antennas.append((ax, top, hgt))
            rect(ax - 1, top - hgt, ax + 1, top, CITY)
    if antennas:  # one red tip light
        ax, top, hgt = antennas[0]
        rect(ax - 1, top - hgt - 2, ax + 2, top - hgt + 1, ANTENNA_DOT)
    rng3 = random.Random(2026)
    for _ in range(12):  # sparse warm windows
        bx0, top, bx1 = buildings[rng3.randrange(len(buildings))]
        wx = rng3.randrange(bx0 + 4, max(bx0 + 5, bx1 - 7))
        wy = rng3.randrange(top + 12, 876)
        rect(wx, wy, wx + 3, wy + 4, WINDOW)

    # 9. foreground sea band + sun-reflection shimmer
    # (bars sit clear of the title zone y 925-965)
    for y in range(880, H):
        fill_row(y, SEA)
    shim = [lerp(hx("C65A35"), hx("F5A83D"), i / 3.0) for i in range(4)]
    for i, (sy, sw) in enumerate([(892, 120), (912, 90), (972, 60), (992, 40)]):
        x0 = 512 - sw // 2
        for y in range(sy, sy + 4):
            span(y, x0, x0 + sw, shim[i])

    # 10. title
    draw_text("THE SKY IS AN OCEAN", 930, TITLE)


# ------------------------------------------------------------------ PNG out

def png_chunk(typ, data):
    out = struct.pack(">I", len(data)) + typ + data
    out += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    return out


def encode_png():
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    raw = bytearray()
    prev = bytearray(W * 3)
    for row in img:
        none_sum = sum(row)
        up = bytes((a - b) & 0xFF for a, b in zip(row, prev))
        up_sum = 0
        for v in up:
            up_sum += v if v < 128 else 256 - v
        if up_sum < none_sum:
            raw.append(2)  # filter type 2 = Up (difference from row above)
            raw += up
        else:
            raw.append(0)
            raw += row
        prev = row
    idat = zlib.compress(bytes(raw), 9)
    return (b"\x89PNG\r\n\x1a\n"
            + png_chunk(b"IHDR", ihdr)
            + png_chunk(b"IDAT", idat)
            + png_chunk(b"IEND", b""))


def main():
    draw()
    png = encode_png()
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "entry.png"), "wb") as f:
        f.write(png)


if __name__ == "__main__":
    main()
