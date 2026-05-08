#!/usr/bin/env python3
"""
make-icons.py — generate CG favicon + Windows .ico from PIL drawing primitives.

Doesn't depend on any SVG renderer (cairosvg / Inkscape) — just Pillow. The
mark we draw mirrors the SVG in src/dashboard_static/brand/logo-mark.svg as
closely as a raster engine can: rounded-square stamp, coral orbital ring,
amber satellite, white "CG" monogram, coral accent bar.

Outputs:
  src/dashboard_static/favicon.ico       — multi-size 16/32/48/64/128/256
  src/dashboard_static/favicon-16.png
  src/dashboard_static/favicon-32.png
  src/dashboard_static/apple-touch-icon.png  — 180×180 (iOS home-screen)
  src/dashboard_static/icon-256.png
  src/dashboard_static/icon-512.png

Run:  python scripts/make-icons.py
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src" / "dashboard_static"
BRAND = STATIC / "brand"
BRAND.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------------- colors
COLOR_STAMP_TOP    = (26, 15, 10)     # warm-black gradient top
COLOR_STAMP_BOTTOM = (10, 9, 8)       # base
COLOR_CORAL        = (255, 122, 89)
COLOR_AMBER        = (255, 184, 122)
COLOR_CREAM        = (245, 230, 211)
COLOR_WHITE        = (255, 255, 255)
COLOR_BORDER       = (255, 184, 122, 46)


def find_font(size: int) -> ImageFont.FreeTypeFont:
    """Try to find a heavy sans-serif font on Windows / Linux / macOS."""
    candidates = [
        "C:/Windows/Fonts/Inter-Black.ttf",
        "C:/Windows/Fonts/Inter-Bold.ttf",
        "C:/Windows/Fonts/seguibl.ttf",     # Segoe UI Black
        "C:/Windows/Fonts/segoeuib.ttf",    # Segoe UI Bold
        "C:/Windows/Fonts/arialbd.ttf",     # Arial Bold
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def gradient_fill(im: Image.Image, top: tuple, bottom: tuple) -> None:
    """Vertical gradient over an existing rectangular image."""
    w, h = im.size
    px = im.load()
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(top[0] * (1 - t) + bottom[0] * t)
        g = int(top[1] * (1 - t) + bottom[1] * t)
        b = int(top[2] * (1 - t) + bottom[2] * t)
        for x in range(w):
            px[x, y] = (r, g, b, 255)


def make_mark(size: int) -> Image.Image:
    """Draw the CG mark at `size`×`size` with antialiased edges."""
    # Render at 4x supersampling, then downscale for clean edges
    SS = 4
    W = size * SS
    img = Image.new("RGBA", (W, W), (0, 0, 0, 0))

    # ---- 1. rounded-square stamp w/ vertical gradient ---------------------
    stamp_layer = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    grad = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    gradient_fill(grad, COLOR_STAMP_TOP, COLOR_STAMP_BOTTOM)
    mask = Image.new("L", (W, W), 0)
    md = ImageDraw.Draw(mask)
    radius = int(W * 0.187)  # 12/64 of viewBox, scaled
    md.rounded_rectangle((int(W * 0.031), int(W * 0.031),
                          int(W * 0.969), int(W * 0.969)),
                         radius=radius, fill=255)
    stamp_layer.paste(grad, (0, 0), mask)

    # subtle inner glow
    glow = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx, cy = W // 2, W // 2
    for r in range(int(W * 0.45), 0, -2):
        a = int(35 * (1 - r / (W * 0.45)))
        gd.ellipse((cx - r, cy - r, cx + r, cy + r),
                   fill=(255, 122, 89, max(0, a)))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=W * 0.04))
    stamp_layer = Image.alpha_composite(stamp_layer, glow)

    # hairline border
    bd = ImageDraw.Draw(stamp_layer)
    bd.rounded_rectangle((int(W * 0.039), int(W * 0.039),
                          int(W * 0.961), int(W * 0.961)),
                         radius=radius - 1, outline=COLOR_BORDER, width=max(1, SS // 2))

    img = Image.alpha_composite(img, stamp_layer)

    # ---- 2. orbital ring (gradient stroke, rotated -28°) ------------------
    # Draw straight ring on its own layer, then rotate.
    ring = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    rx, ry = int(W * 0.375), int(W * 0.172)  # 24/64, 11/64
    # Gradient along the major axis: walk segments by angle
    steps = 96
    stroke = max(2, int(W * 0.038))  # 2.4/64
    for i in range(steps):
        a0 = -math.pi + (i / steps) * 2 * math.pi
        a1 = -math.pi + ((i + 1) / steps) * 2 * math.pi
        # Gradient: bottom→middle→top
        t = i / steps
        if t < 0.55:
            s = t / 0.55
            r = int(255 * (1 - s) + 255 * s)
            g = int(122 * (1 - s) + 184 * s)
            b = int(89 * (1 - s) + 122 * s)
        else:
            s = (t - 0.55) / 0.45
            r = int(255 * (1 - s) + 245 * s)
            g = int(184 * (1 - s) + 230 * s)
            b = int(122 * (1 - s) + 211 * s)
        x0 = cx + rx * math.cos(a0); y0 = cy + ry * math.sin(a0)
        x1 = cx + rx * math.cos(a1); y1 = cy + ry * math.sin(a1)
        rd.line([(x0, y0), (x1, y1)], fill=(r, g, b, 255), width=stroke)
    # Rotate the ring -28°
    ring = ring.rotate(-28, resample=Image.BICUBIC, center=(cx, cy))
    img = Image.alpha_composite(img, ring)

    # ---- 3. satellite dot riding the orbit --------------------------------
    sat = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sat)
    # Position 48.5/22 in 64-unit space → fraction 0.758, 0.344
    sx, sy = int(W * 0.758), int(W * 0.344)
    rr = max(2, int(W * 0.0375))
    # halo
    for r in range(rr * 4, rr, -1):
        a = int(120 * (1 - r / (rr * 4)))
        sd.ellipse((sx - r, sy - r, sx + r, sy + r),
                   fill=(255, 122, 89, max(0, a)))
    sat = sat.filter(ImageFilter.GaussianBlur(radius=rr))
    sd = ImageDraw.Draw(sat)
    sd.ellipse((sx - rr, sy - rr, sx + rr, sy + rr), fill=COLOR_AMBER + (255,))
    img = Image.alpha_composite(img, sat)

    # ---- 4. CG monogram ---------------------------------------------------
    # Skip monogram on very small sizes — would render as mush
    if size >= 24:
        text_layer = Image.new("RGBA", (W, W), (0, 0, 0, 0))
        td = ImageDraw.Draw(text_layer)
        # Heavy condensed look — Inter-Black or Segoe UI Black
        font_size = int(W * 0.41)  # 26/64
        font = find_font(font_size)
        text = "CG"
        # tight letterspacing — draw letter-by-letter with manual kerning
        # Compute total width with measured glyphs and a -2/64 nudge per gap
        bboxes = [td.textbbox((0, 0), c, font=font) for c in text]
        widths = [b[2] - b[0] for b in bboxes]
        kern = -int(W * 0.031)  # -2/64
        total_w = sum(widths) + kern * (len(text) - 1)
        x = (W - total_w) // 2
        y = int(W * 0.18)  # baseline tweak
        for i, ch in enumerate(text):
            td.text((x - bboxes[i][0], y), ch, font=font, fill=COLOR_WHITE + (255,))
            x += widths[i] + kern
        img = Image.alpha_composite(img, text_layer)

    # ---- 5. coral accent slash --------------------------------------------
    if size >= 20:
        bar = Image.new("RGBA", (W, W), (0, 0, 0, 0))
        bd2 = ImageDraw.Draw(bar)
        bx0 = int(W * 0.313)
        bx1 = int(W * 0.687)
        by0 = int(W * 0.75)
        by1 = int(W * 0.781)
        bd2.rounded_rectangle((bx0, by0, bx1, by1), radius=2, fill=COLOR_CORAL + (255,))
        img = Image.alpha_composite(img, bar)

    # ---- 6. downscale to target -------------------------------------------
    img = img.resize((size, size), Image.LANCZOS)
    return img


def main():
    print("CG icon generator — Hustler brutal mark")
    print(f"Writing to: {STATIC}")

    # Generate at the canonical sizes
    sizes = [16, 32, 48, 64, 128, 256, 512]
    images = {}
    for s in sizes:
        img = make_mark(s)
        images[s] = img
        out = STATIC / f"icon-{s}.png"
        img.save(out, "PNG", optimize=True)
        print(f"  wrote {out.name} ({s}×{s})")

    # Favicon shortcuts
    images[16].save(STATIC / "favicon-16.png", "PNG", optimize=True)
    images[32].save(STATIC / "favicon-32.png", "PNG", optimize=True)

    # Apple touch icon (iOS home-screen) — 180×180
    apple = make_mark(180)
    apple.save(STATIC / "apple-touch-icon.png", "PNG", optimize=True)
    print("  wrote apple-touch-icon.png (180×180)")

    # Windows .ico — multi-resolution. Pillow needs RGBA + sizes list.
    ico_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    images[256].save(STATIC / "favicon.ico", format="ICO", sizes=ico_sizes)
    print(f"  wrote favicon.ico (multi: {len(ico_sizes)} sizes)")

    # Also drop a desktop-sized icon to BRAND/ for the user to use as
    # Windows shortcut target icon in the launcher .lnk
    images[256].save(BRAND / "cg-icon-256.png", "PNG", optimize=True)
    apple.save(BRAND / "cg-icon-180.png", "PNG", optimize=True)
    images[256].save(BRAND / "cg-icon.ico", format="ICO", sizes=ico_sizes)
    print(f"  wrote brand/cg-icon.ico for desktop shortcut")

    print("done.")


if __name__ == "__main__":
    main()
