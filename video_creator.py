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

# Re-engineered "Creator Premium" Color Palette
COLOR_BG        = (242, 245, 250)  # Bright, clean studio white
COLOR_CARD_Q    = (25, 28, 50)     # Deep royal obsidian navy
COLOR_TEXT_Q    = (255, 255, 255)  
COLOR_CARD_A    = (255, 60, 75)    # High-intensity coral red
COLOR_TEXT_A    = (255, 255, 255)  
COLOR_HIGHLIGHT = (255, 235, 75)   # Punchy electric yellow for the key punchline words
COLOR_TEXT_MIN  = (100, 112, 135)  # Soft slate gray
COLOR_SHADOW    = (15, 20, 45, 30) # Richer, deep soft shadow overlay


def get_modern_font(size):
    """Prioritizes high-retention geometric video fonts."""
    paths = [
        "assets/LilitaOne-Regular.ttf",      # Highly recommended to download for shorts!
        "assets/Montserrat-Black.ttf",
        "C:/Windows/Fonts/ariblk.ttf",       # Arial Black (Solid fallback)
        "C:/Windows/Fonts/trebucbd.ttf",     
        "/Library/Fonts/Arial Black.ttf",
        f"/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except Exception: continue
    return ImageFont.load_default()

def clean_emojis(text):
    return re.sub(r'[^\x00-\x7F]+', '', text).strip()

def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

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

def draw_polished_card(img, lines, visible_word_count, center_y, font, text_color, card_color, max_w, padding=44, is_punchline=False):
    draw = ImageDraw.Draw(img)
    
    lh = int(th(draw, font) * 1.45)
    card_h = (lh * len(lines)) + (padding * 2) - int(th(draw, font) * 0.45)
    card_w = max_w

    x0 = (W - card_w) // 2
    y0 = center_y - (card_h // 2)
    x1 = x0 + card_w
    y1 = y0 + card_h
    
    # 1. Soft Ambient Blur Shadow Layer
    shadow_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_img)
    s_draw.rounded_rectangle([x0 + 2, y0 + 8, x1 + 2, y1 + 8], radius=32, fill=COLOR_SHADOW)
    shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(radius=10))
    img.paste(shadow_img, (0, 0), shadow_img)
    
    # 2. Base Solid Rounded Card Frame
    draw.rounded_rectangle([x0, y0, x1, y1], radius=32, fill=card_color)
    
    # 3. Dynamic Word-by-Word Mapping
    words_passed = 0
    curr_y = y0 + padding
    
    for line in lines:
        line_words = line.split()
        words_to_render = []
        
        for word in line_words:
            if words_passed < visible_word_count:
                words_to_render.append(word)
                words_passed += 1
                
        if not words_to_render:
            curr_y += lh
            continue

        # Advanced Typography Treatment: Highlight the last 2 words of the punchline
        if is_punchline and words_passed >= visible_word_count:
            # Render lines with mixed highlight colors seamlessly
            full_line_text = " ".join(words_to_render)
            start_x = x0 + (card_w - tw(draw, full_line_text, font)) // 2
            
            for idx, word in enumerate(words_to_render):
                # If it's one of the final two words of the joke, make it Pop!
                use_color = COLOR_HIGHLIGHT if (len(words_to_render) - idx <= 2) else text_color
                draw.text((start_x, curr_y), word, font=font, fill=use_color)
                start_x += tw(draw, word + " ", font)
        else:
            # Standard smooth monochrome text block
            render_text = " ".join(words_to_render)
            x_text = x0 + (card_w - tw(draw, render_text, font)) // 2
            draw.text((x_text, curr_y), render_text, font=font, fill=text_color)
            
        curr_y += lh


def create_pun_video(question, answer, emojis, music_path, output_path):
    clean_q = clean_emojis(question)
    clean_a = clean_emojis(answer)

    # Bumped font size slightly for higher visual scale weight
    f_large = get_modern_font(46)  
    f_small = get_modern_font(26)

    base_img = Image.new("RGB", (W, H))
    base_draw = ImageDraw.Draw(base_img)
    q_lines = get_wrapped_lines(base_draw, clean_q, f_large, W - 120)
    a_lines = get_wrapped_lines(base_draw, clean_a, f_large, W - 120)
    
    total_q_words = len(clean_q.split())
    total_a_words = len(clean_a.split())

    y_anchor_q = int(H * 0.36)
    y_anchor_a = int(H * 0.66)

    def make_frame(t):
        img = Image.new("RGB", (W, H), COLOR_BG)
        draw = ImageDraw.Draw(img)

        # Upper Minimal Branding Strip
        x_hdr = (W - tw(draw, "DAILY PUN CHALLENGE", f_small)) // 2
        draw.text((x_hdr, int(H * 0.12)), "DAILY PUN CHALLENGE", font=f_small, fill=COLOR_TEXT_MIN)
        draw.line([(W//2 - 35, int(H * 0.16)), (W//2 + 35, int(H * 0.16))], fill=COLOR_CARD_A, width=4)

        # --- PHASE 1 & 2: Main Setup/Countdown ---
        if t < 7.2:
            reveal_duration = 4.2
            progress = min(1.0, t / reveal_duration)
            visible_q_words = max(1, int(progress * total_q_words))
            
            draw_polished_card(img, q_lines, visible_q_words, y_anchor_q, f_large, COLOR_TEXT_Q, COLOR_CARD_Q, W - 110)

            # Circular Countdown Tag Overlay
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

        # --- PHASE 3: Punchline Pop & Dynamic CTA Fade ---
        else:
            pt = t - 7.2
            
            # Draw locked question card base
            draw_polished_card(img, q_lines, total_q_words, y_anchor_q, f_large, COLOR_TEXT_Q, COLOR_CARD_Q, W - 110)
            
            # Elastic Spring-Overshoot Calculation for the Answer Entry
            # It briefly overshoots its target height by 12 pixels before settling cleanly
            slide_speed = 6.0
            if pt * slide_speed < math.pi:
                # Sine-wave ease curve with an expansion bump
                bounce_factor = math.sin(pt * slide_speed) * 15.0
                current_y_a = y_anchor_a + int(45 * (1.0 - (pt * slide_speed / math.pi))) - int(bounce_factor)
            else:
                current_y_a = y_anchor_a
            
            draw_polished_card(
                img, a_lines, total_a_words, current_y_a, 
                f_large, COLOR_TEXT_A, COLOR_CARD_A, W - 110, is_punchline=True
            )
            
            # Call to Action Text Fade-in Smooth Transition
            fade_progress = min(1.0, pt * 3.0)
            cta_curr_color = lerp_color(COLOR_BG, COLOR_TEXT_MIN, fade_progress)
            
            x_cta = (W - tw(draw, "LIKE & SUBSCRIBE FOR MORE", f_small)) // 2
            draw.text((x_cta, int(H * 0.88)), "LIKE & SUBSCRIBE FOR MORE", font=f_small, fill=cta_curr_color)

        return np.array(img)

    # Video Compiler Loop Pipeline
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
