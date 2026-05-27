"""
Build a 90-second promo companion video for RAX AI.
Layout: vertical 1080x1920, dark neon background, iPhone mockup centered,
each section showing one app screen with title/subtitle overlay matching the script.

Sections (start_sec, dur_sec, screenshot, title, subtitle):
  0   8s   intro/logo                "RAX AI"               "Your AI, Reimagined"
  8   12s  EN_02_home.png            "REAL-TIME CHAT"       "Claude-powered conversations"
  20  12s  generated_image.png       "AI IMAGES"            "Realistic. Anime. Futuristic."
  32  10s  EN_04_voice.png           "PREMIUM VOICE"        "4 cinematic voices"
  42  13s  creator.png               "FILES & CONTENT"      "Analyze. Summarize. Create."
  55  13s  EN_03_studio.png          "RAX STUDIO"           "AR Lens · Journal · Roast · Shopper"
  68  10s  EN_05_premium.png         "PLANS"                "Free · Premium $5.99 · Pro $9.99"
  78  6s   EN_06_profile.png         "ONE APP"              "Everything you need"
  84  6s   final.png                 "COMING SOON"          "to the App Store"
"""

import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = "/app/app_preview"
SHOTS = "/app/appstore_screenshots"
OUT = f"{ROOT}/promo_frames"
os.makedirs(OUT, exist_ok=True)

CANVAS_W, CANVAS_H = 1080, 1920

# iPhone mockup dimensions (proportional, centered horizontally, lower-third anchored)
PHONE_W = 720
PHONE_H = 1480  # 19.5:9 ratio
PHONE_X = (CANVAS_W - PHONE_W) // 2
PHONE_Y = 340  # leave space at top for title, bottom for subtitle

CORNER_R = 100         # outer corner radius (iPhone 16 Pro Max-ish)
BEZEL = 14             # bezel thickness
SCREEN_W = PHONE_W - 2 * BEZEL
SCREEN_H = PHONE_H - 2 * BEZEL
SCREEN_X = PHONE_X + BEZEL
SCREEN_Y = PHONE_Y + BEZEL
SCREEN_R = CORNER_R - BEZEL

# Colors
NEON_GREEN = (57, 255, 20)
NEON_BLUE = (0, 195, 255)
DARK_BG = (5, 8, 14)
PHONE_BODY = (28, 28, 32)        # titanium gray
PHONE_HIGHLIGHT = (60, 60, 70)


def make_bg() -> Image.Image:
    """Dark canvas with subtle neon radial glow."""
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), DARK_BG)
    # Radial glow using a blurred ellipse
    glow = Image.new("RGB", (CANVAS_W, CANVAS_H), DARK_BG)
    g_draw = ImageDraw.Draw(glow)
    # green glow center
    g_draw.ellipse(
        [-200, 600, CANVAS_W + 200, CANVAS_H - 200],
        fill=(15, 60, 35),
    )
    glow = glow.filter(ImageFilter.GaussianBlur(180))
    img = Image.blend(img, glow, 0.7)
    # subtle blue glow top
    glow2 = Image.new("RGB", (CANVAS_W, CANVAS_H), DARK_BG)
    g2 = ImageDraw.Draw(glow2)
    g2.ellipse([-100, -300, CANVAS_W + 100, 700], fill=(10, 40, 70))
    glow2 = glow2.filter(ImageFilter.GaussianBlur(160))
    img = Image.blend(img, glow2, 0.4)
    return img


def make_phone_frame() -> Image.Image:
    """Returns a transparent PNG containing the iPhone body (no screen content)."""
    frame = Image.new("RGBA", (PHONE_W + 80, PHONE_H + 80), (0, 0, 0, 0))
    d = ImageDraw.Draw(frame)
    pad = 40

    # Outer phone shadow (soft)
    shadow = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle(
        [pad - 6, pad - 6, pad + PHONE_W + 6, pad + PHONE_H + 6],
        radius=CORNER_R + 6, fill=(0, 0, 0, 180),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(25))
    frame.alpha_composite(shadow)

    # Phone body
    d.rounded_rectangle(
        [pad, pad, pad + PHONE_W, pad + PHONE_H],
        radius=CORNER_R, fill=PHONE_BODY,
    )
    # Inner border highlight (titanium edge)
    d.rounded_rectangle(
        [pad, pad, pad + PHONE_W, pad + PHONE_H],
        radius=CORNER_R, outline=PHONE_HIGHLIGHT, width=3,
    )
    # Screen "well" (black inside before content)
    d.rounded_rectangle(
        [pad + BEZEL, pad + BEZEL, pad + PHONE_W - BEZEL, pad + PHONE_H - BEZEL],
        radius=SCREEN_R, fill=(0, 0, 0, 255),
    )

    # Dynamic Island
    di_w, di_h = 240, 50
    di_x = pad + (PHONE_W - di_w) // 2
    di_y = pad + 28
    d.rounded_rectangle(
        [di_x, di_y, di_x + di_w, di_y + di_h],
        radius=25, fill=(0, 0, 0, 255),
    )

    # Side buttons (left: volume up/down + action, right: power)
    btn_color = (50, 50, 56)
    # Left side
    d.rounded_rectangle([pad - 4, pad + 220, pad + 4, pad + 268], radius=3, fill=btn_color)  # action
    d.rounded_rectangle([pad - 4, pad + 320, pad + 4, pad + 408], radius=3, fill=btn_color)  # vol up
    d.rounded_rectangle([pad - 4, pad + 430, pad + 4, pad + 518], radius=3, fill=btn_color)  # vol dn
    # Right side
    d.rounded_rectangle([pad + PHONE_W - 4, pad + 320, pad + PHONE_W + 4, pad + 460], radius=3, fill=btn_color)

    return frame


def fit_screenshot(path: str) -> Image.Image:
    """Open screenshot, scale to fit the screen area, return RGBA."""
    img = Image.open(path).convert("RGB")
    # source is 1290x2796 (~0.461 ratio), our screen is SCREEN_W:SCREEN_H (~0.475 ratio)
    target_ratio = SCREEN_W / SCREEN_H
    src_ratio = img.size[0] / img.size[1]
    if src_ratio > target_ratio:
        # too wide, crop sides
        new_w = int(img.size[1] * target_ratio)
        left = (img.size[0] - new_w) // 2
        img = img.crop((left, 0, left + new_w, img.size[1]))
    else:
        # too tall, crop top/bottom (keep center)
        new_h = int(img.size[0] / target_ratio)
        top = (img.size[1] - new_h) // 2
        img = img.crop((0, top, img.size[0], top + new_h))
    img = img.resize((SCREEN_W, SCREEN_H), Image.LANCZOS)
    # Round corners via mask
    mask = Image.new("L", (SCREEN_W, SCREEN_H), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0, 0, SCREEN_W, SCREEN_H], radius=SCREEN_R, fill=255)
    out = Image.new("RGBA", (SCREEN_W, SCREEN_H), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask=mask)
    return out


def try_font(size: int, bold: bool = False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def draw_centered_text(canvas, text, y, font, fill=(255, 255, 255), shadow=True, glow_color=None):
    d = ImageDraw.Draw(canvas)
    bbox = d.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (CANVAS_W - tw) // 2 - bbox[0]
    if glow_color:
        # Render glow on a separate layer
        glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.text((x, y), text, font=font, fill=glow_color + (210,))
        glow = glow.filter(ImageFilter.GaussianBlur(14))
        canvas.alpha_composite(glow)
    if shadow:
        d.text((x + 3, y + 3), text, font=font, fill=(0, 0, 0, 180))
    d.text((x, y), text, font=font, fill=fill)
    return th


def build_section_image(screenshot_path, title, subtitle, accent=NEON_GREEN, out_path=None):
    bg = make_bg().convert("RGBA")
    # title (top)
    font_title = try_font(72, bold=True)
    font_sub = try_font(36, bold=False)

    draw_centered_text(bg, title, 130, font_title, fill=(255, 255, 255, 255), glow_color=accent)
    draw_centered_text(bg, subtitle, 230, font_sub, fill=(220, 240, 255, 255))

    # phone frame composited
    frame = make_phone_frame()
    fx = (CANVAS_W - frame.size[0]) // 2
    fy = PHONE_Y - 40  # frame has 40px padding
    bg.alpha_composite(frame, (fx, fy))

    # screenshot inside the screen
    if screenshot_path and os.path.exists(screenshot_path):
        shot = fit_screenshot(screenshot_path)
        bg.alpha_composite(shot, (SCREEN_X, SCREEN_Y))

    # bottom logo/brand bar
    font_brand = try_font(40, bold=True)
    draw_centered_text(bg, "RAX AI", PHONE_Y + PHONE_H + 60, font_brand, fill=(255, 255, 255, 255), glow_color=NEON_BLUE)
    font_brand_sub = try_font(22, bold=False)
    draw_centered_text(bg, "Powered by Claude · Gemini · OpenAI", PHONE_Y + PHONE_H + 120, font_brand_sub, fill=(170, 200, 230, 255))

    if out_path:
        bg.convert("RGB").save(out_path, quality=92)
    return bg


def build_logo_intro():
    """Pure logo splash, big RAX AI text, neon glow."""
    bg = make_bg().convert("RGBA")
    # Massive logo
    font_huge = try_font(220, bold=True)
    font_tag = try_font(46, bold=False)
    # vertically center
    cy = CANVAS_H // 2 - 180
    draw_centered_text(bg, "RAX AI", cy, font_huge, fill=(255, 255, 255, 255), glow_color=NEON_GREEN)
    draw_centered_text(bg, "Your AI. Reimagined.", cy + 240, font_tag, fill=(200, 230, 255, 255))
    # subtitle
    font_small = try_font(28, bold=False)
    draw_centered_text(bg, "Chat · Images · Voice · Studio", cy + 320, font_small, fill=(160, 200, 230, 255))
    return bg


def build_coming_soon():
    bg = make_bg().convert("RGBA")
    font_huge = try_font(160, bold=True)
    font_brand = try_font(130, bold=True)
    font_tag = try_font(50, bold=False)
    font_app = try_font(38, bold=True)
    cy = CANVAS_H // 2 - 360
    draw_centered_text(bg, "COMING SOON", cy, font_huge, fill=(255, 255, 255, 255), glow_color=NEON_GREEN)
    draw_centered_text(bg, "RAX AI", cy + 250, font_brand, fill=(255, 255, 255, 255), glow_color=NEON_BLUE)
    draw_centered_text(bg, "to the App Store", cy + 430, font_tag, fill=(200, 230, 255, 255))
    # Apple badge text
    draw_centered_text(bg, "🍎  Download on the App Store", cy + 620, font_app, fill=(255, 255, 255, 255), glow_color=(120, 120, 120))
    return bg


def main():
    # Create the placeholder for "AI IMAGES" since we don't have a real screenshot
    # We'll reuse the studio one but with a different title -- or actually we have
    # screenshots only for: login, home, studio, voice, premium, profile.
    # Map images:
    sections = [
        # (out_name, screenshot_path, title, subtitle, accent_rgb)
        ("01_intro",   None,                                "RAX AI",            "Your AI. Reimagined.", NEON_GREEN),
        ("02_chat",    f"{SHOTS}/EN_02_home.png",           "REAL-TIME CHAT",    "Claude-powered conversations", NEON_GREEN),
        ("03_images",  f"{SHOTS}/EN_02_home.png",           "AI IMAGES",         "Realistic. Anime. Futuristic.", (255, 80, 220)),
        ("04_voice",   f"{SHOTS}/EN_04_voice.png",          "PREMIUM VOICE",     "4 cinematic voices · Speech-to-Text", NEON_BLUE),
        ("05_creator", f"{SHOTS}/EN_03_studio.png",         "FILES & CREATOR",   "Analyze · Summarize · Generate", (255, 180, 0)),
        ("06_studio",  f"{SHOTS}/EN_03_studio.png",         "RAX STUDIO",        "AR Lens · Journal · Roast · Shopper", NEON_GREEN),
        ("07_premium", f"{SHOTS}/EN_05_premium.png",        "PLANS",             "Free · Premium $5.99 · Pro $9.99", (255, 215, 0)),
        ("08_profile", f"{SHOTS}/EN_06_profile.png",        "ONE APP",           "Everything you need", NEON_BLUE),
        ("09_coming",  None,                                "COMING SOON",       "to the App Store", NEON_GREEN),
    ]
    for name, path, title, sub, accent in sections:
        out_path = f"{OUT}/{name}.png"
        if name == "01_intro":
            img = build_logo_intro()
        elif name == "09_coming":
            img = build_coming_soon()
        else:
            img = build_section_image(path, title, sub, accent=accent)
        img.convert("RGB").save(out_path, quality=92)
        print(f"✅ {out_path}")
    print("\n=== All frames generated ===")


if __name__ == "__main__":
    main()
