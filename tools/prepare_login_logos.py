"""Create login-only transparent assets without changing the original logos.

Run with a Python installation that has Pillow: python3 tools/prepare_login_logos.py
"""
from collections import deque
from pathlib import Path
from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parents[1] / "accounts/static/accounts/images"


def save_trimmed(image, name):
    bounds = image.getchannel("A").getbbox()
    image.crop(bounds).save(ASSETS / name)


save_trimmed(Image.open(ASSETS / "padasig.png").convert("RGBA"), "padasig-login.png")

# Keep the complete circular seal, but remove the square outside its outer ring.
osca = Image.open(ASSETS / "osca.png").convert("RGBA")
scale = 4
mask = Image.new("L", (osca.width * scale, osca.height * scale))
ImageDraw.Draw(mask).ellipse((4, 4, mask.width - 4, mask.height - 4), fill=255)
osca.putalpha(mask.resize(osca.size, Image.Resampling.LANCZOS))
save_trimmed(osca, "osca-login.png")

# Flood-fill only exterior white; enclosed lettering stays white and legible.
pension = Image.open(ASSETS / "pension.png").convert("RGBA")
pixels = pension.load()
queue = deque([(0, 0)])
seen = set()
while queue:
    x, y = queue.popleft()
    if (x, y) in seen or not (0 <= x < pension.width and 0 <= y < pension.height):
        continue
    seen.add((x, y))
    red, green, blue, alpha = pixels[x, y]
    if min(red, green, blue) < 235:
        continue
    pixels[x, y] = (red, green, blue, 0)
    queue.extend([(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)])
save_trimmed(pension, "pension-login.png")
