import os
import math
import re
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

try:
    from moviepy.editor import VideoClip, AudioFileClip
    from moviepy.audio.fx.all import audio_loop
except ImportError:
    raise ImportError("Run: pip install moviepy==1.0.3")

W, H      = 720, 1280
FPS       = 30
DURATION  = 10.0

# Premium Content Palette
COLOR_BG       = (244, 246, 249)  # Light studio gray
COLOR_CARD_Q   = (18, 22, 36)     # Deep obsidian navy
COLOR_TEXT_Q   = (255, 255, 255)  
COLOR_CARD_A   = (255, 59, 59)    # Vibrant high-energy red
COLOR_TEXT_A   = (255, 255, 255)  
COLOR_TEXT_MIN = (90, 100, 115)   # Slate gray for UI accents
COLOR_SHADOW   = (0, 0, 0, 20)    # Soft alpha drop shadow


def get_modern_font(size):
    paths = [
        "C:/Windows/Fonts/ariblk.ttf",
        "C:/Windows/Fonts/trebucbd.ttf",
        "/Library/Fonts/Arial Black.ttf",
        "/Library/Fonts/Trebuchet MS Bold.ttf",
        f"/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except Exception: continue
    return ImageFont.load_default()

def clean_emojis(text):
    return re.sub(r'[^\x00-\x7F]+', '', text).strip()

def tw(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0]

def th(draw, font):
    bb = draw.textbbox((0, 0), "Ag", font=font)
    return bb[3] - bb[1]

def get_wrapped_lines(draw, text, font, max_w):
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
    return lines

def draw_polished_card(img, lines, visible_word_count, center_y, font, text_color, card_color, max_w, padding=44):
    """Draws a rounded container with clean line-height spacing, smooth dropshadows, and word-by-word reveals."""
    draw = ImageDraw.Draw(img)
    
    # Increased line-height multiplier from 1.3 to 1.45 for breathable, professional typography
    lh = int(th(draw, font) * 1.45)
    card_h = (lh * len(lines)) + (padding * 2) - int(th(draw, font) * 0.45)
    card_w = max_w
    
    x0 = (W - card_w) // 2
    y0 = center_y - (card_h // 2)
    x1 = x0 + card_w
    y1 = y0 + card_h
    
    # 1. Generate a modern blurred drop-shadow layer underneath
    shadow_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_img)
    s_draw.rounded_rectangle([x0 + 2, y0 + 6, x1 + 2, y1 + 6], radius=28, fill=COLOR_SHADOW)
    shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(radius=8))
    img.paste(shadow_img, (0, 0), shadow_img)
    
    # 2. Base Solid UI Card Container
    draw.rounded_rectangle([x0, y0, x1, y1], radius=28, fill=card_color)
    
    # 3. Render strings without layout popping
    words_passed = 0
    curr_y = y0 + padding
    
    for line in lines:
        line_words = line.split()
        words_to_render_in_line = []
        
        for word in line_words:
            if words_passed < visible_word_count:
                words_to_render_in_line.append(word)
                words_passed += 1
                
        render_text = " ".join(words_to_render_in_line)
        
        if render_text:
            x_text = x0 + (card_w - tw(draw, render_text, font)) // 2
            draw.text((x_text, curr_y), render_text, font=font, fill=text_color)
            
        curr_y += lh


def create_pun_video(question, answer, emojis, music_path, output_path):
    clean_q = clean_emojis(question)
    clean_a = clean_emojis(answer)

    f_large = get_modern_font(44)  
    f_mid   = get_modern_font(40)
    f_small = get_modern_font(26)

    # Static pre-calculation structural blueprints
    base_img = Image.new("RGB", (W, H))
    base_draw = ImageDraw.Draw(base_img)
    q_lines = get_wrapped_lines(base_draw, clean_q, f_large, W - 120)
    a_lines = get_wrapped_lines(base_draw, clean_a, f_large, W - 120)
    
    total_q_words = len(clean_q.split())
    total_a_words = len(clean_a.split())

    def make_frame(t):
        img = Image.new("RGB", (W, H), COLOR_BG)
        draw = ImageDraw.Draw(img)

        # Upper Minimal Top-Bar
        x_hdr = (W - tw(draw, "DAILY PUN CHALLENGE", f_small)) // 2
        draw.text((x_hdr, int(H * 0.12)), "DAILY PUN CHALLENGE", font=f_small, fill=COLOR_TEXT_MIN)
        draw.line([(W//2 - 35, int(H * 0.16)), (W//2 + 35, int(H * 0.16))], fill=COLOR_CARD_A, width=4)

        # --- PHASE 1 & 2: Setup Phase (0.0s - 7.2s) ---
        if t < 7.2:
            # Word reveal timeline scaling
            reveal_duration = 4.2
            progress = min(1.0, t / reveal_duration)
            visible_q_words = max(1, int(progress * total_q_words))
            
            # Draw Question Card completely stationary at center
            draw_polished_card(
                img, q_lines, visible_q_words, int(H * 0.38), 
                f_large, COLOR_TEXT_Q, COLOR_CARD_Q, W - 110
            )

            # Circular Snappy Timer Tag
            if t >= 4.8:
                pt = t - 4.8
                count = 2 - int(pt / 1.2)
                count = max(1, count)
                
                cx, cy = W // 2, int(H * 0.64)
                r = 52
                draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=COLOR_TEXT_MIN)
                
                pulse = 1.0 + (1.0 - ((pt * 1.2) % 1.0)) * 0.12
                f_count = get_modern_font(int(46 * pulse))
                
                x_cnt = cx - (tw(draw, str(count), f_count) // 2)
                y_cnt = cy - (th(draw, f_count) // 2) - 4
                draw.text((x_cnt, y_cnt), str(count), font=f_count, fill=(255, 255, 255))

        # --- PHASE 3: Clean Punchline Reveal & Outro ---
        else:
            pt = t - 7.2
            
            # Question smoothly shifts upwards slightly to optimize phone screen spaces
            draw_polished_card(
                img, q_lines, total_q_words, int(H * 0.30), 
                f_mid, COLOR_TEXT_Q, COLOR_CARD_Q, W - 110
            )
            
            # Smooth ease-out animation curve calculation for punchline reveal card
            scale = min(1.0, pt * 6.0) 
            bounce_w = int((W - 110) * (0.85 + 0.15 * math.sin(scale * math.pi / 2)))
            
            if bounce_w > 50:
                draw_polished_card(
                    img, a_lines, total_a_words, int(H * 0.64), 
                    f_large, COLOR_TEXT_A, COLOR_CARD_A, bounce_w
                )
            
            # Bottom call to action display
            if pt > 0.4:
                x_cta = (W - tw(draw, "LIKE & SUBSCRIBE FOR MORE", f_small)) // 2
                draw.text((x_cta, int(H * 0.88)), "LIKE & SUBSCRIBE FOR MORE", font=f_small, fill=COLOR_TEXT_MIN)

        return np.array(img)

    clip = VideoClip(make_frame, duration=DURATION)

    if music_path and os.path.exists(music_path):
        audio = AudioFileClip(music_path)
        audio = audio_loop(audio, duration=DURATION) if audio.duration < DURATION else audio.subclip(0, DURATION)
        audio = audio.audio_fadeout(1.0)
        clip  = clip.set_audio(audio)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    clip.write_videofile(
        output_path, fps=FPS, codec="libx264", audio_codec="aac",
        threads=4, preset="fast", ffmpeg_params=["-crf", "22"], logger=None,
    )
    clip.close()
    return output_path
