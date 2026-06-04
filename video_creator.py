"""
video_creator.py
White background, clean transitions, no emoji rendering issues.

Phases:
  0- 3s  Hook: bouncing "?" + title
  3-13s  Question types in with blinking cursor
 13-18s  Suspense countdown 5 to 1
 18-19s  Orange flash + ANSWER TIME!
 19-26s  Answer bursts in + LOL
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

W, H     = 720, 1280
FPS      = 30
DURATION = 28

BG      = (255, 255, 255)
NAVY    = ( 20,  25,  70)
ORANGE  = (220,  80,  20)
MAGENTA = (160,   0, 120)
TEAL    = (  0, 130, 170)
MUTED   = (170, 170, 195)
SHADOW  = (210, 210, 220)


def get_font(size, bold=False):
    paths = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/verdanab.ttf" if bold else "C:/Windows/Fonts/verdana.ttf",
        "C:/Windows/Fonts/impact.ttf",
        "assets/Bangers-Regular.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
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
        draw.text((x + 2, y + 2), text, font=font, fill=SHADOW)
    draw.text((x, y), text, font=font, fill=color)

def draw_wrapped(draw, text, center_y, font, color, max_w,
                 line_spacing=1.4, shadow=True):
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
        if shadow:
            draw.text((x + 2, y + 2), line, font=font, fill=SHADOW)
        draw.text((x, y), line, font=font, fill=color)
        y += lh

def draw_floating_marks(draw, t, font):
    spots = [(70,200),(630,300),(110,560),(600,640),(55,910),(650,990)]
    for i, (bx, by) in enumerate(spots):
        x = int(bx + math.sin(t * 0.7 + i * 1.3) * 15)
        y = int(by + math.cos(t * 0.5 + i * 1.0) * 12)
        draw.text((x, y), "?", font=font, fill=(220, 220, 230))

def draw_divider(draw, y, color=MUTED, width=400):
    x0 = (W - width) // 2
    draw.line([(x0, y), (x0 + width, y)], fill=color, width=2)


def create_pun_video(question, answer, emojis, music_path, output_path):

    fxl = get_font(90, bold=True)
    flg = get_font(70, bold=True)
    fmd = get_font(52, bold=True)
    fsm = get_font(38)
    fxs = get_font(30)
    fqm = get_font(40)

    def make_frame(t):
        img  = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)
        draw_floating_marks(draw, t, fqm)

        if t < 3:
            bounce_y = int(H * 0.22 - abs(math.sin(t * 3.2)) * 60)
            pulse    = 1.0 + math.sin(t * 6) * 0.06
            fq       = get_font(int(200 * pulse), bold=True)
            draw_centered(draw, "?", bounce_y, fq, ORANGE)
            fade = min(1.0, t / 1.0)
            col  = tuple(int(lerp(240, c, fade)) for c in NAVY)
            draw_centered(draw, "CAN YOU GUESS", int(H * 0.60), flg, col)
            draw_centered(draw, "THE PUN?",      int(H * 0.70), flg, col)
            draw_centered(draw, "Stay tuned...", int(H * 0.82), fxs, TEAL, shadow=False)

        elif t < 13:
            pt    = t - 3.0
            speed = len(question) / 2.5
            chars = min(len(question), int(pt * speed))
            cursor = "|" if (chars < len(question) and int(t * 2) % 2 == 0) else ""
            draw_wrapped(draw, question[:chars] + cursor,
                         int(H * 0.44), flg, NAVY, W - 80)
            if pt > 3.5:
                dots = "." * (int((pt - 3.5) * 2.0) % 4)
                draw_centered(draw, f"Hmmmm{dots}", int(H * 0.77), fmd, MAGENTA)
            if pt > 5.5:
                draw_centered(draw, "Think carefully!",
                              int(H * 0.88), fxs, TEAL, shadow=False)

        elif t < 18:
            pt    = t - 13.0
            count = max(1, 5 - int(pt))
            pulse = 1.0 + (1.0 - (pt % 1.0)) * 0.22
            draw_wrapped(draw, question, int(H * 0.30), fsm, MUTED, W - 120, shadow=False)
            draw_divider(draw, int(H * 0.44))
            draw_centered(draw, "Answer reveals in...",
                          int(H * 0.56), fsm, NAVY, shadow=False)
            fc  = get_font(int(165 * pulse), bold=True)
            col = ORANGE if count > 2 else MAGENTA
            draw_centered(draw, str(count), int(H * 0.72), fc, col)

        elif t < 19:
            pt    = t - 18.0
            flash = max(0.0, 1.0 - pt * 3.0)
            bg_r  = 255
            bg_g  = int(lerp(255, 100, flash))
            bg_b  = int(lerp(255,  20, flash))
            draw.rectangle([(0, 0), (W, H)], fill=(bg_r, bg_g, bg_b))
            draw_floating_marks(draw, t, fqm)
            if pt > 0.25:
                p2  = ease_out((pt - 0.25) / 0.75)
                col = tuple(int(lerp(bg_c, nc, p2))
                            for bg_c, nc in zip((bg_r, bg_g, bg_b), NAVY))
                draw_centered(draw, "ANSWER TIME!", int(H * 0.46), flg, col)

        elif t < 26:
            pt  = t - 19.0
            fan = get_font(int(lerp(20, 68, ease_out(pt / 0.6))), bold=True) \
                  if pt < 0.6 else fmd
            draw_wrapped(draw, answer, int(H * 0.46), fan, NAVY, W - 80)
            if pt > 1.2:
                ep = ease_out(min(1.0, (pt - 1.2) / 0.5))
                ey = int(lerp(H * 0.80, H * 0.70, ep))
                draw_centered(draw, "HA  HA  HA !", ey, fmd, MAGENTA)
            if pt > 3.0:
                bob = int(math.sin(t * 5) * 6)
                draw_centered(draw, "LOL !", int(H * 0.87) + bob, flg, ORANGE)

        else:
            glo = 0.85 + 0.15 * math.sin(t * 3.5)
            col = tuple(int(c * glo) for c in ORANGE)
            draw_divider(draw, int(H * 0.30), color=(220, 220, 230), width=500)
            draw_centered(draw, "SUBSCRIBE",                  int(H * 0.38), flg, col)
            draw_centered(draw, "for 2 puns daily!",          int(H * 0.52), fmd, NAVY)
            draw_divider(draw, int(H * 0.62), color=(220, 220, 230), width=500)
            draw_centered(draw, "Like if it made you groan!", int(H * 0.67), fsm,
                          MAGENTA, shadow=False)
            draw_centered(draw, "#puns  #dadjokes  #shorts",  int(H * 0.76), fxs,
                          MUTED, shadow=False)

        return np.array(img)

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
        output_path, fps=FPS, codec="libx264", audio_codec="aac",
        threads=4, preset="medium", ffmpeg_params=["-crf", "23"], logger=None,
    )
    clip.close()
    print(f"Video saved -> {output_path}")
    return output_path
