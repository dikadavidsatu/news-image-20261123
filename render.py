#!/usr/bin/env python3
"""Draw entry.png: Monday 23 November 2026's world news as one front page.

Reads headlines.json (stories gathered this morning from live wire
reports) and paints a dense 1024x1024 broadsheet with PIL. Also writes
image_manifest.json recording exactly what was drawn, so main.ts can
verify the artifact against its data.

Deterministic: the grain uses a fixed seed, there is no clock, no
network and no unseeded randomness, so re-running this file reproduces
the same PNG byte for byte.
"""

import hashlib
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W = H = 1024
M = 32                      # page margin
CW = W - 2 * M              # content width

PAPER = (248, 243, 232)
CARD = (255, 253, 246)
INK = (22, 21, 18)
BODY = (56, 53, 47)
GREY = (102, 98, 88)
RULE = (206, 198, 180)
RED = (178, 34, 34)
RED_DK = (140, 24, 24)
NAVY = (24, 42, 68)
NAVY_LT = (38, 66, 100)
GOLD = (214, 158, 46)
TEAL = (16, 92, 96)

FONT_DIRS = ["/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/truetype/noto"]


def font(names, size):
    for name in names:
        for d in FONT_DIRS:
            p = os.path.join(d, name)
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def f_title(s):
    return font(["DejaVuSerif-Bold.ttf"], s)


def f_serif(s):
    return font(["DejaVuSerif-Bold.ttf"], s)


def f_sans(s):
    return font(["DejaVuSans.ttf"], s)


def f_bold(s):
    return font(["DejaVuSans-Bold.ttf"], s)


def f_ital(s):
    return font(["DejaVuSans-Oblique.ttf", "DejaVuSans.ttf"], s)


def wrap(draw, text, fnt, width):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=fnt) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def tracked(text):
    return " ".join(list(text))


def grain(img, seed=20261123, amp=7, block=3):
    """Blocky newsprint grain. Per-pixel noise would bloat the PNG past
    the 1 MiB cap; 3x3 blocks keep the file in the few-hundred-KB band
    while the page still reads as paper."""
    rng = np.random.default_rng(seed)
    small = rng.integers(-amp, amp + 1, (H // block + 1, W // block + 1, 1))
    noise = np.repeat(np.repeat(small, block, axis=0), block, axis=1)[:H, :W]
    arr = np.asarray(img).astype(np.int16)
    return Image.fromarray(np.clip(arr + noise, 0, 255).astype(np.uint8))


def dots(draw, x0, y0, x1, y1, color, gap=11, r0=1.0, r1=4.2):
    """Halftone dots that swell left to right, for the illustration panel."""
    row = 0
    y = y0 + gap // 2
    while y < y1:
        x = x0 + gap // 2
        while x < x1:
            t = (x - x0) / max(1, x1 - x0)
            r = r0 + t * r1 * (0.8 + 0.2 * ((row % 3) / 2))
            draw.ellipse([x - r, y - r, x + r, y + r], fill=color)
            x += gap
        y += gap
        row += 1


def draw_globe(draw, cx, cy, r):
    """A cracked-earth globe: navy disc, gold meridians, a red fissure."""
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=NAVY)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=GOLD, width=3)
    for k in range(-2, 3):
        off = k * r / 3.0
        h = math.sqrt(max(0.0, r * r - off * off))
        draw.arc([cx - r + abs(off) * 0.55, cy - h, cx + r - abs(off) * 0.55, cy + h],
                 270, 90, fill=GOLD, width=2)
        draw.arc([cx - r + abs(off) * 0.55, cy - h, cx + r - abs(off) * 0.55, cy + h],
                 90, 270, fill=GOLD, width=2)
    draw.line([cx - r, cy, cx + r, cy], fill=GOLD, width=2)
    # the crack: a jagged red line across the disc
    pts = [(cx - r * 0.85, cy - r * 0.28), (cx - r * 0.4, cy - r * 0.05),
           (cx - r * 0.1, cy + r * 0.22), (cx + r * 0.25, cy + r * 0.02),
           (cx + r * 0.6, cy + r * 0.3), (cx + r * 0.85, cy + r * 0.12)]
    draw.line(pts, fill=RED, width=5, joint="curve")
    for (px, py) in pts[1:-1]:
        draw.ellipse([px - 3, py - 3, px + 3, py + 3], fill=RED)


def headline_block(draw, x, y, width, story, hsize=13.5, dsize=11, max_h=2, max_d=2):
    for ln in wrap(draw, story["h"], f_bold(hsize), width)[:max_h]:
        draw.text((x, y), ln, font=f_bold(hsize), fill=INK)
        y += hsize + 3
    for ln in wrap(draw, story["d"], f_sans(dsize), width)[:max_d]:
        draw.text((x, y), ln, font=f_sans(dsize), fill=BODY)
        y += dsize + 2.5
    draw.text((x, y), story["s"].upper(), font=f_bold(8.5), fill=GREY)
    return y + 11


def short_item(draw, x, y, width, text):
    f = f_bold(11.5)
    draw.text((x, y + 1), "▸", font=f, fill=RED)
    for ln in wrap(draw, text, f, width - 14)[:2]:
        draw.text((x + 14, y), ln, font=f, fill=INK)
        y += 13.5
    return y + 3


def section_block(draw, x, y, width, sec):
    draw.rectangle([x, y, x + width, y + 20], fill=sec["color"])
    draw.text((x + 7, y + 3), sec["name"], font=f_bold(12), fill=(255, 255, 255))
    y += 27
    y = headline_block(draw, x, y, width, sec["stories"][0])
    for st in sec["stories"][1:3]:
        y = short_item(draw, x, y, width, st["h"])
    return y


def main():
    with open(os.path.join(HERE, "headlines.json")) as f:
        data = json.load(f)
    img = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(img)
    rendered = []

    # ---------------- masthead ----------------
    draw.text((M, 12), "ONE IMAGE · THE DAY'S NEWS, WHOLE", font=f_bold(11), fill=RED)
    title = "THE WORLD IN ONE PICTURE"
    tf = f_title(48)
    tw = draw.textlength(title, font=tf)
    draw.text(((W - tw) / 2, 26), title, font=tf, fill=INK)
    draw.rectangle([M, 86, W - M, 90], fill=INK)
    draw.text((M, 97), data["date_line"].upper(), font=f_bold(12), fill=INK)
    mid = "MONDAY EDITION · 23 NOVEMBER 2026"
    mw = draw.textlength(mid, font=f_bold(12))
    draw.text(((W - mw) / 2, 97), mid, font=f_bold(12), fill=INK)
    right = "WIRE REPORTS · 02:00 UTC"
    rw = draw.textlength(right, font=f_sans(10.5))
    draw.text((W - M - rw, 98), right, font=f_sans(10.5), fill=GREY)
    draw.rectangle([M, 114, W - M, 116], fill=INK)

    # ---------------- lead story ----------------
    y = 126
    lead = data["lead"]
    text_w = 600
    draw.text((M, y), tracked(lead["kicker"]), font=f_bold(12), fill=RED)
    y += 21
    for ln in wrap(draw, lead["headline"], f_serif(30), text_w):
        draw.text((M, y), ln, font=f_serif(30), fill=INK)
        y += 35
    y += 3
    for ln in wrap(draw, lead["deck"], f_sans(12.5), text_w):
        draw.text((M, y), ln, font=f_sans(12.5), fill=BODY)
        y += 15.5
    draw.text((M, y + 2), lead["source"].upper(), font=f_bold(9.5), fill=GREY)
    rendered.append(lead["headline"])
    lead_bottom = y + 17

    # illustration panel, right of the lead
    px0, py0, px1 = 668, 126, W - M
    draw.rectangle([px0, py0, px1, py0 + 23], fill=NAVY)
    draw.text((px0 + 9, py0 + 5), "ANTALYA · NO DEAL", font=f_bold(11.5), fill=(255, 255, 255))
    draw_globe(draw, (px0 + px1) // 2, py0 + 82, 52)
    cap_y = py0 + 148
    for ln in wrap(draw, "The longest climate summit on record ends with nothing signed.",
                   f_ital(11), px1 - px0)[:2]:
        draw.text((px0, cap_y), ln, font=f_ital(11), fill=BODY)
        cap_y += 14
    dots(draw, px0, cap_y + 2, px1, cap_y + 30, NAVY_LT)
    panel_bottom = cap_y + 34

    # dateline rail under the panel, two columns of four
    rail_y = max(lead_bottom, panel_bottom) + 6
    draw.rectangle([M, rail_y, W - M, rail_y + 2], fill=INK)
    rail_y += 8
    rail = [("ANTALYA", "Climate talks collapse"),
            ("KYIV", "14 missing in drone strike"),
            ("JAKARTA", "Factory fire, 50 missing"),
            ("SEOUL", "Minister quits over AI cheating"),
            ("WELLINGTON", "India 720 for 9, a record"),
            ("NEW DELHI", "Nepal PM meets Modi"),
            ("LISBON", "Thousands march on prices"),
            ("GENEVA", "UN keeps talking on lethal AI")]
    ry = rail_y
    for row in range(4):
        for col in range(2):
            city, note = rail[row * 2 + col]
            bx = M + col * (CW // 2)
            draw.ellipse([bx + 2, ry + 4, bx + 9, ry + 11], fill=RED)
            draw.text((bx + 16, ry), city, font=f_bold(11.5), fill=INK)
            cw = draw.textlength(city, font=f_bold(11.5))
            draw.text((bx + 21 + cw, ry + 1), "— " + note, font=f_sans(10.5), fill=BODY)
        ry += 18.5
    rail_bottom = ry

    # ---------------- second story ----------------
    y2 = rail_bottom + 10
    draw.rectangle([M, y2 - 8, W - M, y2 - 6], fill=INK)
    s2 = data["second"]
    draw.text((M, y2), tracked(s2["kicker"]), font=f_bold(11.5), fill=RED)
    yy = y2 + 19
    for ln in wrap(draw, s2["headline"], f_serif(24), CW):
        draw.text((M, yy), ln, font=f_serif(24), fill=INK)
        yy += 30
    for ln in wrap(draw, s2["deck"], f_sans(12.5), CW)[:2]:
        draw.text((M, yy), ln, font=f_sans(12.5), fill=BODY)
        yy += 15.5
    draw.text((M, yy + 1), s2["source"].upper(), font=f_bold(9), fill=GREY)
    rendered.append(s2["headline"])
    yy += 10

    # ---------------- numbers ticker ----------------
    ny = yy + 6
    draw.rectangle([M, ny, W - M, ny + 2], fill=INK)
    nums = "  ·  ".join("%s %s" % (a, b) for a, b in data["numbers"])
    ticker = "THE DAY IN NUMBERS — " + nums
    ty = ny + 7
    for ln in wrap(draw, ticker, f_bold(11), CW)[:2]:
        draw.text((M, ty), ln, font=f_bold(11), fill=NAVY)
        ty += 14
    draw.rectangle([M, ty + 2, W - M, ty + 4], fill=INK)

    # ---------------- sections grid, 3 x 2 ----------------
    gy = ty + 16
    col_w = (CW - 28) // 3
    xs = [M, M + col_w + 14, M + 2 * (col_w + 14)]
    rows = [["WORLD", "US & POLITICS", "BUSINESS & TECH"],
            ["ASIA & DIPLOMACY", "SPORT", "CULTURE & ODDS"]]
    secs = {s["name"]: s for s in data["sections"]}
    for r, row in enumerate(rows):
        ends = []
        for i, name in enumerate(row):
            ends.append(section_block(draw, xs[i], gy, col_w, secs[name]))
            rendered.extend(st["h"] for st in secs[name]["stories"][:3])
        gy = max(ends) + (8 if r == 0 else 6)
        if r == 0:
            draw.rectangle([M, gy - 8, W - M, gy - 7], fill=RULE)

    # ---------------- in-brief strip ----------------
    by = gy + 2
    draw.text((M, by), tracked("AROUND THE WORLD IN BRIEF"), font=f_bold(11), fill=RED)
    by += 16
    briefs = data["briefs"][:8]
    bw = (CW - 3 * 12) // 4
    for i, (tag, text) in enumerate(briefs):
        bx = M + (i % 4) * (bw + 12)
        byy = by + (i // 4) * 26
        draw.text((bx, byy), tag, font=f_bold(10), fill=NAVY)
        tw2 = draw.textlength(tag, font=f_bold(10))
        for j, ln in enumerate(wrap(draw, text, f_sans(10), bw - tw2 - 6)):
            draw.text((bx + tw2 + 5, byy + j * 12.5), ln, font=f_sans(10), fill=BODY)
        rendered.append("%s: %s" % (tag, text))
    bottom = by + 2 * 26

    # ---------------- footer ----------------
    fy = max(bottom + 8, 962)
    draw.rectangle([M, fy, W - M, fy + 2], fill=INK)
    for j, ln in enumerate(wrap(draw, "SOURCES: " + data["sources"], f_sans(9.5), CW)[:2]):
        draw.text((M, fy + 7 + j * 12), ln, font=f_sans(9.5), fill=GREY)
    foot2 = ("One image, drawn by an AI agent from the day's wire reports · "
             "Monday 23 November 2026 · Headlines as reported by the outlets named")
    draw.text((M, fy + 33), foot2, font=f_ital(9.5), fill=GREY)

    img = grain(img)
    out = os.path.join(HERE, "entry.png")
    img.save(out, optimize=True)
    digest = hashlib.sha256(open(out, "rb").read()).hexdigest()
    manifest = {
        "file": "entry.png",
        "width": W,
        "height": H,
        "bytes": os.path.getsize(out),
        "sha256": digest,
        "date": "2026-11-23",
        "items_rendered": len(rendered),
        "headlines": rendered,
    }
    with open(os.path.join(HERE, "image_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1, ensure_ascii=False)
    print("wrote", out, manifest["bytes"], "bytes; items:", len(rendered),
          "; briefs bottom:", bottom, "; footer:", fy)


if __name__ == "__main__":
    main()
