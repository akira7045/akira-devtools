#!/usr/bin/env python3
import os
from PIL import Image, ImageDraw, ImageFont

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
BOLD = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")
MONO = os.path.join(FONT_DIR, "DejaVuSansMono.ttf")
MONO_B = os.path.join(FONT_DIR, "DejaVuSansMono-Bold.ttf")

W, H = 1280, 720
BG = (13, 17, 23)
BORDER = (48, 54, 61)
GREY = (139, 148, 158)
WHITE = (240, 246, 252)
BLUE = (88, 166, 255)
GREEN = (63, 185, 80)
RED = (255, 95, 86)
YELLOW = (255, 189, 46)
GREEN2 = (57, 197, 100)

def font(path, size):
    return ImageFont.truetype(path, size)

def make(name, tagline, cmd, comment1, comment2):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([6, 6, W - 7, H - 7], outline=BORDER, width=2)

    d.text((56, 48), "akira-devtools", font=font(MONO, 30), fill=GREY)
    d.text((56, 92), "zero-dependency  \u00b7  single-file  \u00b7  MIT",
           font=font(MONO, 22), fill=GREY)

    d.text((56, 160), name, font=font(BOLD, 88), fill=WHITE)
    d.text((56, 262), tagline, font=font(MONO, 30), fill=BLUE)

    box = [56, 320, W - 56, H - 56]
    d.rounded_rectangle(box, radius=12, outline=BORDER, width=2)
    cy = 340
    d.ellipse([80, cy + 8, 96, cy + 24], fill=RED)
    d.ellipse([108, cy + 8, 124, cy + 24], fill=YELLOW)
    d.ellipse([136, cy + 8, 152, cy + 24], fill=GREEN2)

    fy = 396
    d.text((80, fy), "$ " + cmd, font=font(MONO_B, 30), fill=GREEN)
    d.text((80, fy + 52), "# " + comment1, font=font(MONO, 28), fill=GREY)
    d.text((80, fy + 100), "# " + comment2, font=font(MONO, 28), fill=GREY)
    return img

out = "/data/akira/products/covers"

logsum = make(
    "logsum",
    "Summarize logs into counts. Read-only.",
    "./logsum.py access.log --by status",
    "counts by status / level / field",
    "never writes: pure read-only summary",
)
logsum.save(os.path.join(out, "logsum.png"))

envcheck = make(
    "envcheck",
    "Lint .env files before prod. Never leaks secrets.",
    "./envcheck.py .env --schema schema.txt",
    "missing / empty / typed keys caught",
    "reads only: secret values never printed",
)
envcheck.save(os.path.join(out, "envcheck.png"))

print("written:", os.path.join(out, "logsum.png"), os.path.join(out, "envcheck.png"))
