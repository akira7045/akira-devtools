#!/usr/bin/env python3
import os
from PIL import Image, ImageDraw, ImageFont

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
BOLD = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")
MONO = os.path.join(FONT_DIR, "DejaVuSansMono.ttf")
MONO_B = os.path.join(FONT_DIR, "DejaVuSansMono-Bold.ttf")
BG = (13, 17, 23)
BORDER = (48, 54, 61)
GREY = (139, 148, 158)
WHITE = (240, 246, 252)
BLUE = (88, 166, 255)
GREEN = (63, 185, 80)

def font(p, s):
    return ImageFont.truetype(p, s)

def make_profile(size=1024):
    img = Image.new("RGB", (size, size), BG)
    d = ImageDraw.Draw(img)
    m = int(size * 0.035)
    d.rounded_rectangle([m, m, size - m, size - m], radius=int(size * 0.05),
                        outline=BORDER, width=int(size * 0.004))
    cx = size // 2
    d.text((cx, int(size * 0.34)), "Araki", font=font(BOLD, int(size * 0.17)),
           fill=WHITE, anchor="mm")
    d.text((cx, int(size * 0.50)), "Akira", font=font(BOLD, int(size * 0.17)),
           fill=WHITE, anchor="mm")
    d.text((cx, int(size * 0.63)), "Python / Automation", font=font(MONO, int(size * 0.052)),
           fill=BLUE, anchor="mm")
    d.text((cx, int(size * 0.72)), "zero-dep tools \u00b7 reliable delivery",
           font=font(MONO, int(size * 0.036)), fill=GREY, anchor="mm")
    lw = int(size * 0.16)
    y = int(size * 0.80)
    d.text((cx, y), "$ deploy --safe", font=font(MONO_B, int(size * 0.042)),
           fill=GREEN, anchor="mm")
    return img

out = "/data/akira/products/covers"
img = make_profile()
img.save(os.path.join(out, "profile-1024.png"))
img.resize((512, 512)).save(os.path.join(out, "profile-512.png"))
print("written")
