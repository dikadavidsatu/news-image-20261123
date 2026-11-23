#!/usr/bin/env python3
"""Monday 23 November 2026, summed up in one image.

This script turns headlines.json into entry.png, a 1024x1024 broadsheet
front page. The stories, the geometry and the grain seed are all fixed
at authoring time, so running the script twice produces the same PNG
bytes twice. There is no network, no clock and no unseeded randomness
anywhere in this file.
"""

import hashlib
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
SIDE = 1024
EDGE = 32
INNER = SIDE - 2 * EDGE

PAL = {
    "paper": (248, 243, 232),
    "ink": (22, 21, 18),
    "body": (56, 53, 47),
    "grey": (102, 98, 88),
    "rule": (206, 198, 180),
    "red": (178, 34, 34),
    "navy": (24, 42, 68),
    "navy2": (38, 66, 100),
    "gold": (214, 158, 46),
}

LOOK = ("/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/truetype/noto")


def typeface(names, size):
    for name in names:
        for folder in LOOK:
            path = os.path.join(folder, name)
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def title_face(size):
    return typeface(["DejaVuSerif-Bold.ttf"], size)


def serif_face(size):
    return typeface(["DejaVuSerif-Bold.ttf"], size)


def plain_face(size):
    return typeface(["DejaVuSans.ttf"], size)


def bold_face(size):
    return typeface(["DejaVuSans-Bold.ttf"], size)


def italic_face(size):
    return typeface(["DejaVuSans-Oblique.ttf", "DejaVuSans.ttf"], size)


def flow(canvas, text, face, width):
    """Greedy word wrap: lines of `text` that fit `width` in `face`."""
    out, current = [], ""
    for word in text.split():
        trial = (current + " " + word).strip()
        if canvas.textlength(trial, font=face) <= width or not current:
            current = trial
        else:
            out.append(current)
            current = word
    if current:
        out.append(current)
    return out


def letterspaced(text):
    return " ".join(list(text))


def paper_grain(picture, seed=20261123, strength=7, cell=3):
    """Newsprint grain in coarse blocks. Fine per-pixel noise would push
    the PNG past the 1 MiB cap; 3x3 blocks keep the file in the
    few-hundred-KB band while the page still reads as paper."""
    rng = np.random.default_rng(seed)
    tiny = rng.integers(-strength, strength + 1, (SIDE // cell + 1, SIDE // cell + 1, 1))
    field = np.repeat(np.repeat(tiny, cell, axis=0), cell, axis=1)[:SIDE, :SIDE]
    pixels = np.asarray(picture).astype(np.int16)
    return Image.fromarray(np.clip(pixels + field, 0, 255).astype(np.uint8))


def dot_field(canvas, left, top, right, bottom, colour, step=11):
    """Halftone dots that grow from left to right."""
    row = 0
    y = top + step // 2
    while y < bottom:
        x = left + step // 2
        while x < right:
            frac = (x - left) / max(1, right - left)
            rad = 1.0 + frac * 4.2 * (0.8 + 0.2 * ((row % 3) / 2))
            canvas.ellipse([x - rad, y - rad, x + rad, y + rad], fill=colour)
            x += step
        y += step
        row += 1


def cracked_globe(canvas, cx, cy, radius):
    """Navy disc, gold ring and chords, split by a red zigzag crack."""
    canvas.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=PAL["navy"])
    canvas.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                   outline=PAL["gold"], width=3)
    for k in (-2, -1, 0, 1, 2):
        shift = k * radius / 3.0
        half = math.sqrt(max(0.0, radius * radius - shift * shift))
        canvas.arc([cx - radius + abs(shift) * 0.55, cy - half,
                    cx + radius - abs(shift) * 0.55, cy + half],
                   270, 90, fill=PAL["gold"], width=2)
        canvas.arc([cx - radius + abs(shift) * 0.55, cy - half,
                    cx + radius - abs(shift) * 0.55, cy + half],
                   90, 270, fill=PAL["gold"], width=2)
    canvas.line([cx - radius, cy, cx + radius, cy], fill=PAL["gold"], width=2)
    crack = [(cx - radius * 0.85, cy - radius * 0.28), (cx - radius * 0.4, cy - radius * 0.05),
             (cx - radius * 0.1, cy + radius * 0.22), (cx + radius * 0.25, cy + radius * 0.02),
             (cx + radius * 0.6, cy + radius * 0.3), (cx + radius * 0.85, cy + radius * 0.12)]
    canvas.line(crack, fill=PAL["red"], width=5, joint="curve")
    for px, py in crack[1:-1]:
        canvas.ellipse([px - 3, py - 3, px + 3, py + 3], fill=PAL["red"])


class Sheet:
    """The page and a moving cursor; every block draws, then advances y."""

    def __init__(self):
        self.img = Image.new("RGB", (SIDE, SIDE), PAL["paper"])
        self.c = ImageDraw.Draw(self.img)
        self.y = 0
        self.shown = []

    def rule(self, y=None, weight=2, colour=None):
        yy = self.y if y is None else y
        self.c.rectangle([EDGE, yy, SIDE - EDGE, yy + weight],
                         fill=colour or PAL["ink"])

    def masthead(self, data):
        c = self.c
        c.text((EDGE, 12), "ONE IMAGE · THE DAY'S NEWS, WHOLE",
               font=bold_face(11), fill=PAL["red"])
        name = "THE WORLD IN ONE PICTURE"
        face = title_face(48)
        wide = c.textlength(name, font=face)
        c.text(((SIDE - wide) / 2, 26), name, font=face, fill=PAL["ink"])
        self.rule(86, 4)
        c.text((EDGE, 97), data["date_line"].upper(), font=bold_face(12), fill=PAL["ink"])
        mid = "MONDAY EDITION · 23 NOVEMBER 2026"
        mw = c.textlength(mid, font=bold_face(12))
        c.text(((SIDE - mw) / 2, 97), mid, font=bold_face(12), fill=PAL["ink"])
        right = "WIRE REPORTS · 02:00 UTC"
        rw = c.textlength(right, font=plain_face(10.5))
        c.text((SIDE - EDGE - rw, 98), right, font=plain_face(10.5), fill=PAL["grey"])
        self.rule(114, 2)

    def lead_block(self, lead):
        c = self.c
        y = 126
        c.text((EDGE, y), letterspaced(lead["kicker"]), font=bold_face(12), fill=PAL["red"])
        y += 21
        face = serif_face(30)
        for line in flow(c, lead["headline"], face, 600):
            c.text((EDGE, y), line, font=face, fill=PAL["ink"])
            y += 35
        y += 3
        body = plain_face(12.5)
        for line in flow(c, lead["deck"], body, 600):
            c.text((EDGE, y), line, font=body, fill=PAL["body"])
            y += 15
        c.text((EDGE, y + 2), lead["source"].upper(), font=bold_face(9.5), fill=PAL["grey"])
        self.shown.append(lead["headline"])
        return y + 17

    def panel(self):
        c = self.c
        x0, y0, x1 = 668, 126, SIDE - EDGE
        c.rectangle([x0, y0, x1, y0 + 23], fill=PAL["navy"])
        c.text((x0 + 9, y0 + 5), "ANTALYA · NO DEAL", font=bold_face(11.5),
               fill=(255, 255, 255))
        cracked_globe(c, (x0 + x1) // 2, y0 + 82, 52)
        cy = y0 + 148
        for line in flow(c, "The longest climate summit on record ends with nothing signed.",
                         italic_face(11), x1 - x0)[:2]:
            c.text((x0, cy), line, font=italic_face(11), fill=PAL["body"])
            cy += 14
        dot_field(c, x0, cy + 2, x1, cy + 30, PAL["navy2"])
        return cy + 34

    def rail(self, items):
        c = self.c
        y = max(self._lead_bottom, self._panel_bottom) + 6
        self.rule(y, 2)
        y += 8
        for row in range(4):
            for col in range(2):
                city, note = items[row * 2 + col]
                bx = EDGE + col * (INNER // 2)
                c.ellipse([bx + 2, y + 4, bx + 9, y + 11], fill=PAL["red"])
                c.text((bx + 16, y), city, font=bold_face(11.5), fill=PAL["ink"])
                cw = c.textlength(city, font=bold_face(11.5))
                c.text((bx + 21 + cw, y + 1), "— " + note, font=plain_face(10.5),
                       fill=PAL["body"])
            y += 18
        return y

    def second_block(self, second, y):
        c = self.c
        self.rule(y - 8, 2)
        c.text((EDGE, y), letterspaced(second["kicker"]), font=bold_face(11.5),
               fill=PAL["red"])
        y += 19
        face = serif_face(24)
        for line in flow(c, second["headline"], face, INNER):
            c.text((EDGE, y), line, font=face, fill=PAL["ink"])
            y += 30
        body = plain_face(12.5)
        for line in flow(c, second["deck"], body, INNER)[:2]:
            c.text((EDGE, y), line, font=body, fill=PAL["body"])
            y += 15.5
        c.text((EDGE, y + 1), second["source"].upper(), font=bold_face(9), fill=PAL["grey"])
        self.shown.append(second["headline"])
        return y + 6

    def ticker(self, numbers, y):
        c = self.c
        self.rule(y, 2)
        joined = "  ·  ".join("%s %s" % (a, b) for a, b in numbers)
        text = "THE DAY IN NUMBERS — " + joined
        y += 7
        face = bold_face(11)
        for line in flow(c, text, face, INNER)[:2]:
            c.text((EDGE, y), line, font=face, fill=PAL["navy"])
            y += 14
        self.rule(y + 2, 2)
        return y + 12

    def headline(self, x, y, width, story):
        c = self.c
        face = bold_face(13.5)
        for line in flow(c, story["h"], face, width)[:2]:
            c.text((x, y), line, font=face, fill=PAL["ink"])
            y += 16.5
        body = plain_face(11)
        for line in flow(c, story["d"], body, width)[:2]:
            c.text((x, y), line, font=body, fill=PAL["body"])
            y += 13.5
        c.text((x, y), story["s"].upper(), font=bold_face(8.5), fill=PAL["grey"])
        return y + 11

    def brief_line(self, x, y, width, text):
        c = self.c
        face = bold_face(11.5)
        c.text((x, y + 1), "▸", font=face, fill=PAL["red"])
        for line in flow(c, text, face, width - 14)[:2]:
            c.text((x + 14, y), line, font=face, fill=PAL["ink"])
            y += 13.5
        return y + 3

    def section_card(self, x, y, width, sec):
        c = self.c
        c.rectangle([x, y, x + width, y + 20], fill=sec["color"])
        c.text((x + 7, y + 3), sec["name"], font=bold_face(12), fill=(255, 255, 255))
        y += 27
        y = self.headline(x, y, width, sec["stories"][0])
        for story in sec["stories"][1:3]:
            y = self.brief_line(x, y, width, story["h"])
        return y

    def grid(self, sections, y):
        c = self.c
        col_w = (INNER - 28) // 3
        order = [["WORLD", "US & POLITICS", "BUSINESS & TECH"],
                 ["ASIA & DIPLOMACY", "SPORT", "CULTURE & ODDS"]]
        lookup = {s["name"]: s for s in sections}
        for row_i, row in enumerate(order):
            ends = []
            for col_i, name in enumerate(row):
                x = EDGE + col_i * (col_w + 14)
                ends.append(self.section_card(x, y, col_w, lookup[name]))
                self.shown.extend(st["h"] for st in lookup[name]["stories"][:3])
            y = max(ends) + (6 if row_i == 0 else 4)
            if row_i == 0:
                c.rectangle([EDGE, y - 8, SIDE - EDGE, y - 7], fill=PAL["rule"])
        return y

    def brief_strip(self, briefs, y):
        c = self.c
        c.text((EDGE, y), letterspaced("AROUND THE WORLD IN BRIEF"),
               font=bold_face(11), fill=PAL["red"])
        y += 16
        bw = (INNER - 3 * 12) // 4
        for i, (tag, text) in enumerate(briefs[:8]):
            bx = EDGE + (i % 4) * (bw + 12)
            by = y + (i // 4) * 24
            c.text((bx, by), tag, font=bold_face(10), fill=PAL["navy"])
            tw = c.textlength(tag, font=bold_face(10))
            for j, line in enumerate(flow(c, text, plain_face(10), bw - tw - 6)):
                c.text((bx + tw + 5, by + j * 12.5), line, font=plain_face(10),
                       fill=PAL["body"])
            self.shown.append("%s: %s" % (tag, text))
        return y + 2 * 24

    def footer(self, sources, y):
        c = self.c
        fy = max(y + 8, 962)
        self.rule(fy, 2)
        for j, line in enumerate(flow(c, "SOURCES: " + sources, plain_face(9.5), INNER)[:2]):
            c.text((EDGE, fy + 7 + j * 12), line, font=plain_face(9.5), fill=PAL["grey"])
        tail = ("One image, drawn by an AI agent from the day's wire reports · "
                "Monday 23 November 2026 · Headlines as reported by the outlets named")
        c.text((EDGE, fy + 33), tail, font=italic_face(9.5), fill=PAL["grey"])
        return fy


def build():
    with open(os.path.join(ROOT, "headlines.json")) as f:
        data = json.load(f)
    page = Sheet()
    page.masthead(data)
    page._lead_bottom = page.lead_block(data["lead"])
    page._panel_bottom = page.panel()
    rail_items = [("ANTALYA", "Climate talks collapse"),
                  ("KYIV", "14 missing in drone strike"),
                  ("JAKARTA", "Factory fire, 50 missing"),
                  ("SEOUL", "Minister quits over AI cheating"),
                  ("WELLINGTON", "India 720 for 9, a record"),
                  ("NEW DELHI", "Nepal PM meets Modi"),
                  ("LISBON", "Thousands march on prices"),
                  ("GENEVA", "UN keeps talking on lethal AI")]
    rail_end = page.rail(rail_items)
    after_second = page.second_block(data["second"], rail_end + 10)
    after_ticker = page.ticker(data["numbers"], after_second + 6)
    after_grid = page.grid(data["sections"], after_ticker + 16)
    after_briefs = page.brief_strip(data["briefs"], after_grid + 2)
    foot = page.footer(data["sources"], after_briefs)

    picture = paper_grain(page.img)
    out = os.path.join(ROOT, "entry.png")
    picture.save(out, optimize=True)
    digest = hashlib.sha256(open(out, "rb").read()).hexdigest()
    print("wrote", out, os.path.getsize(out), "bytes; items:", len(page.shown),
          "; briefs bottom:", after_briefs, "; footer:", foot)
    return {"bytes": os.path.getsize(out), "sha256": digest,
            "items": len(page.shown), "headlines": page.shown}


if __name__ == "__main__":
    build()
