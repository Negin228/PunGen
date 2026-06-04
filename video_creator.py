"""
video_creator.py
Creates an animated 28-second YouTube Short from a pun joke.
Uses PIL + numpy + moviepy — no ImageMagick required.
Windows-compatible fonts and emoji rendering.

Video phases:
  0- 3s  Hook: bouncing emoji + title + teaser
  3-13s  Question types in char-by-char, then thinking dots
 13-18s  Suspense countdown 5 to 1
 18-19s  White flash + ANSWER TIME!
 19-26s  Answer bursts in + emojis + LOL
 26-28s  Subscribe CTA
"""

import os
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    from moviepy.editor import VideoClip, AudioFileClip
    from moviepy.audio.fx.all import audio_loop
except ImportError:
    raise ImportError("Run: pip install moviepy==1.0.3")

# ── Canvas ────────────────────────────────────────────────────────────────────
W, H     = 720, 1280
FPS      = 30
DURATION = 28

# ── Colors ────────────────────────────────────────────────────────────────────
BG1   = ( 12,  12,  35)
BG2   = ( 22,  18,  65)
GOLD  = (255, 200,  50)
WHITE = (255, 255, 255)
PINK  = (255,  80, 170)
CYAN  = ( 80, 210, 255)
BLACK = (  0,   0,   0)


# ── Font loaders ──────────────────────────────────────────────────────────────
def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load a readable text font — works on Windows, Mac, and Linux."""
    paths = [
        # Windows
        f"C:/Windows/Fonts/{'arialbd' if bold else 'arial'}.ttf",
        f"C:/Windows/Fonts/{'verdanab' if bold else 'verdana'}.ttf",
        "C:/Windows/Fonts/impact.ttf",
        # Custom (optional — download Bangers from Google Fonts)
        "assets/Bangers-Regular.ttf",
        # macOS
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
        # Linux
        f"/usr/share/fonts/truetype/liberation/LiberationSans-{'Bold' if bold else 'Regular'}.ttf",
        f"/usr/share/fonts/truetype/ubuntu/Ubuntu-{'B' if bold else 'R'}.ttf",
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'Bold' if bold else ''}.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def get_emoji_font(size: int) -> ImageFont.FreeTypeFont:
    """Load a font that renders emojis correctly on Windows."""
    paths = [
        "C:/Windows/Fonts/seguiemj.ttf",    # Windows Segoe UI Emoji
        "C:/Windows/Fonts/seguisym.ttf",    # Windows Segoe UI Symbol
        "assets/NotoEmoji-Regular.ttf",     # cross-platform fallback
        "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
        "/Library/Fonts/Apple Color Emoji.ttc",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return get_font(size)


# ── Drawing helpers ───────────────────────────────────────────────────────────
def lerp(a, b, t):
    return a + (b - a) * max(0.0, min(1.0, t))

def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3

def tw(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0]

def th(draw, font):
    bb = draw.textbbox((0, 0), "Ag", font=font)
    return bb[3] - bb[1]

def draw_centered(draw, text, y, font, color, shadow=True):
    x = (W - tw(draw, text, font)) // 2
    if shadow:
        draw.text((x + 3, y + 3), text, font=font, fill=BLACK)
    draw.text((x, y), text, font=font, fill=color)

def draw_wrapped(draw, text, center_y, font, color, max_w, line_spacing=1.35):
    words = text.split()
    lines, cur = [], []
    for word in words:
        test = cur + [word]
        if tw(draw, " ".join(test), font) > max_w and cur:
            lines.append(" ".join(cur))
            cur = [word]
        else:
            cur = test
    if cur:
        lines.append(" ".join(cur))

    lh = int(th(draw, font) * line_spacing)
    y  = center_y - (lh * len(lines)) // 2
    for line in lines:
        x = (W - tw(draw, line, font)) // 2
        draw.text((x + 3, y + 3), line, font=font, fill=BLACK)
        draw.text((x, y), line, font=font, fill=color)
        y += lh

def gradient_bg(img, t):
    draw = ImageDraw.Draw(img)
    wave = math.sin(t * 0.4) * 12
    for i in range(H):
        p = i / H
        r = int(lerp(BG1[0], BG2[0] + wave, p))
        g = int(lerp(BG1[1], BG2[1] + wave * 0.5, p))
        b = int(lerp(BG1[2], BG2[2] + wave, p))
        draw.line([(0, i), (W, i)],
                  fill=(max(0, min(255, r)),
                        max(0, min(255, g)),
                        max(0, min(255, b))))

def draw_floating_marks(draw, t, font):
    spots = [(80,200),(620,280),(130,580),(580,650),(60,920),(640,980)]
    for i, (bx, by) in enumerate(spots):
        x = int(bx + math.sin(t * 0.7 + i * 1.3) * 18)
        y = int(by + math.cos(t * 0.5 + i * 1.0) * 14)
        draw.text((x, y), "?", font=font, fill=(255, 255, 255, 40))


# ── Main video builder ────────────────────────────────────────────────────────
def create_pun_video(question: str, answer: str, emojis: str,
                     music_path: str, output_path: str) -> str:

    # Regular text fonts
    fxl = get_font(90, bold=True)
    flg = get_font(70, bold=True)
    fmd = get_font(52, bold=True)
    fsm = get_font(38)
    fxs = get_font(30)
    fqm = get_font(44)

    # Emoji fonts
    exl = get_emoji_font(90)
    emd = get_emoji_font(52)

    def make_frame(t: float) -> np.ndarray:
        img  = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        draw = ImageDraw.Draw(img)
        gradient_bg(img, t)
        draw_floating_marks(draw, t, fqm)

        # ── Phase 1: Hook (0–3 s) ─────────────────────────────────────────
        if t < 3:
            bounce_y = int(H * 0.35 - abs(math.sin(t * 3.2)) * 55)
            draw_centered(draw, "🤔", bounce_y, exl, WHITE)

            alpha = min(1.0, t / 1.2)
            col   = tuple(int(c * alpha) for c in GOLD)
            draw_centered(draw, "CAN YOU GUESS", int(H * 0.60), flg, col)
            draw_centered(draw, "THE PUN?",      int(H * 0.70), flg, col)
            draw_centered(draw, "Stay tuned...", int(H * 0.82), fxs,
                          (160, 160, 230))

        # ── Phase 2: Question types in (3–13 s) ──────────────────────────
        elif t < 13:
            pt = t - 3.0
            draw_centered(draw, "— THE QUESTION —", 190, fxs, CYAN)

            speed = len(question) / 2.8
            chars = min(len(question), int(pt * speed))
            caret = "█" if chars < len(question) else ""
            draw_wrapped(draw, question[:chars] + caret,
                         int(H * 0.47), flg, WHITE, W - 80)

            if pt > 3.5:
                dots = "." * (int((pt - 3.5) * 2.2) % 4)
                draw_centered(draw, f"Hmmmm{dots}", int(H * 0.78), fmd, PINK)
            if pt > 5.5:
                draw_centered(draw, "Think carefully!",
                              int(H * 0.88), fxs, (190, 190, 255))

        # ── Phase 3: Countdown (13–18 s) ─────────────────────────────────
        elif t < 18:
            pt    = t - 13.0
            count = max(1, 5 - int(pt))
            pulse = 1.0 + (1.0 - (pt % 1.0)) * 0.25

            draw_centered(draw, "— THE QUESTION —", 190, fxs, CYAN)
            draw_wrapped(draw, question, int(H * 0.38), fsm,
                         (155, 155, 200), W - 100)
            draw_centered(draw, "Answer reveals in...",
                          int(H * 0.60), fsm, WHITE)

            fc  = get_font(int(170 * pulse), bold=True)
            col = GOLD if count > 2 else PINK
            draw_centered(draw, str(count), int(H * 0.73), fc, col)

        # ── Phase 4: Flash (18–19 s) ──────────────────────────────────────
        elif t < 19:
            pt    = t - 18.0
            flash = max(0.0, 1.0 - pt * 2.2)
            bg    = tuple(int(lerp(c, 255, flash)) for c in BG2)
            draw.rectangle([(0, 0), (W, H)], fill=bg)

            if pt > 0.35:
                p2  = ease_out((pt - 0.35) / 0.65)
                col = tuple(int(lerp(255, c, p2)) for c in GOLD)
                draw_centered(draw, "ANSWER TIME!", int(H * 0.47), flg, col)

        # ── Phase 5: Answer reveal (19–26 s) ─────────────────────────────
        elif t < 26:
            pt = t - 19.0

            q_short = question if len(question) <= 38 else question[:35] + "..."
            draw_centered(draw, "Q: " + q_short, 180, fxs, (130, 130, 195))
            draw_centered(draw, "THE ANSWER:", 290, fsm, CYAN)

            fan = get_font(int(lerp(18, 68, ease_out(pt / 0.7))), bold=True) \
                  if pt < 0.7 else fmd
            draw_wrapped(draw, answer, int(H * 0.52), fan, WHITE, W - 80)

            if pt > 1.1:
                ep = ease_out(min(1.0, (pt - 1.1) / 0.5))
                ey = int(lerp(H * 0.82, H * 0.72, ep))
                draw_centered(draw, emojis, ey, exl, WHITE)

            if pt > 2.8:
                bob = int(math.sin(t * 5) * 7)
                draw_centered(draw, "LOL!", int(H * 0.88) + bob, fmd, GOLD)

        # ── Phase 6: Subscribe CTA (26–28 s) ─────────────────────────────
        else:
            glo = 0.85 + 0.15 * math.sin(t * 3.5)
            col = tuple(int(c * glo) for c in GOLD)
            draw_centered(draw, "SUBSCRIBE",
                          int(H * 0.38), flg, col)
            draw_centered(draw, "for 2 puns daily!",
                          int(H * 0.52), fmd, WHITE)
            draw_centered(draw, "Like if it made you groan!",
                          int(H * 0.63), fsm, PINK)
            draw_centered(draw, "#puns  #dadjokes  #shorts",
                          int(H * 0.74), fxs, (140, 140, 195))

        return np.array(img.convert("RGB"))

    # ── Assemble ──────────────────────────────────────────────────────────────
    clip = VideoClip(make_frame, duration=DURATION)

    if music_path and os.path.exists(music_path):
        audio = AudioFileClip(music_path)
        audio = audio_loop(audio, duration=DURATION) \
                if audio.duration < DURATION \
                else audio.subclip(0, DURATION)
        audio = audio.audio_fadeout(3)
        clip  = clip.set_audio(audio)
    else:
        print(f"Warning: Music not found at '{music_path}' — video will be silent.")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    clip.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="medium",
        ffmpeg_params=["-crf", "23"],
        logger=None,
    )
    clip.close()
    print(f"✅  Video saved → {output_path}")
    return output_path
