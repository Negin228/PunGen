import os
import math
import re
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageSequence

try:
    from moviepy.editor import VideoClip, AudioFileClip, CompositeAudioClip
    from moviepy.audio.fx.all import audio_loop
except ImportError:
    raise ImportError("Run: pip install moviepy==1.0.3")

# --- GLOBAL REEL DIMENSIONS ---
W, H      = 720, 1280
FPS       = 30
DURATION  = 12.0

# --- EXACT VIDEO DESIGN PALETTE ---
COLOR_BG          = (255, 255, 255)  
COLOR_HEADER_PILL = (255, 222, 230)  
COLOR_HEADER_TEXT = (215, 38, 93)    
COLOR_CARD_Q      = (0, 0, 0)        
COLOR_TEXT_Q      = (255, 255, 255)  
COLOR_TEXT_A      = (0, 0, 0)        

def get_premium_rounded_font(size):
    """Prioritizes heavy rounded fonts to perfectly replicate the reference style."""
    paths = [
        "assets/Fredoka-Bold.ttf",         # Confirm this exact asset exists here!
        "assets/LilitaOne-Regular.ttf",     
        "C:/Windows/Fonts/ariblk.ttf",       
        "/Library/Fonts/Arial Black.ttf",    
    ]
    for p in paths:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except Exception: continue
    return ImageFont.load_default()

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
    if cur: lines.append(" ".join(cur))
    return lines

def draw_animated_word_pill(img, full_text, font, center_y, t):
    """Animates header words dropping into a perfectly centered container layout."""
    draw = ImageDraw.Draw(img)
    words = full_text.split()
    
    text_w = tw(draw, full_text, font)
    text_h = th(draw, font)
    padding_x, padding_y = 44, 22
    pill_w = text_w + (padding_x * 2)
    pill_h = text_h + (padding_y * 2)
    
    x0 = (W - pill_w) // 2
    y0 = center_y - (pill_h // 2)
    x1 = x0 + pill_w
    y1 = y0 + pill_h
    
    draw.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=COLOR_HEADER_PILL)
    
    space_w = tw(draw, " ", font)
    # Start positioning dynamically relative to the true text block origin
    current_x = x0 + padding_x
    
    for i, word in enumerate(words):
        word_delay = i * 0.22
        if t >= word_delay:
            word_t = t - word_delay
            drop_progress = min(1.0, word_t / 0.18)
            bounce_y = (1.0 - math.sin(drop_progress * (math.pi / 2))) * -40
            draw.text((current_x, y0 + padding_y + bounce_y - 2), word, font=font, fill=COLOR_HEADER_TEXT)
            
        current_x += tw(draw, word, font) + space_w

def draw_sequential_question_card(img, lines, center_y, font, max_w, t, padding=44):
    """Draws the question box with every single word landing accurately dead-center."""
    draw = ImageDraw.Draw(img)
    lh = int(th(draw, font) * 1.35)
    card_h = (lh * len(lines)) + (padding * 2) - int(th(draw, font) * 0.35)
    card_w = max_w

    x0 = (W - card_w) // 2
    y0 = center_y - (card_h // 2)
    x1 = x0 + card_w
    y1 = y0 + card_h
    
    draw.rounded_rectangle([x0, y0, x1, y1], radius=28, fill=COLOR_CARD_Q)
    
    start_delay = 0.75
    space_w = tw(draw, " ", font)
    word_counter = 0
    
    curr_y = y0 + padding
    for line in lines:
        words = line.split()
        line_w = tw(draw, line, font)
        
        # FIX: Computes the precise global frame center-point for line alignment
        current_x = ((W - line_w) // 2)
        
        for word in words:
            word_delay = start_delay + (word_counter * 0.07)
            if t >= word_delay:
                w_t = t - word_delay
                fall_progress = min(1.0, w_t / 0.14)
                ease_y = (1.0 - math.sin(fall_progress * (math.pi / 2))) * -30
                draw.text((current_x, curr_y + ease_y), word, font=font, fill=COLOR_TEXT_Q)
                
            current_x += tw(draw, word, font) + space_w
            word_counter += 1
            
        curr_y += lh

def draw_clean_answer(img, lines, center_y, font):
    draw = ImageDraw.Draw(img)
    lh = int(th(draw, font) * 1.35)
    total_h = lh * len(lines)
    curr_y = center_y - (total_h // 2)
    
    for line in lines:
        x_text = (W - tw(draw, line, font)) // 2
        draw.text((x_text, curr_y), line, font=font, fill=COLOR_TEXT_A)
        curr_y += lh


# --- CORE PIPELINE RENDER ENGINE ---
def create_pun_video(question, answer, output_path, music_path=None, **kwargs):
    f_header = get_premium_rounded_font(36)
    f_body = get_premium_rounded_font(52)        
    f_outro_bold = get_premium_rounded_font(42)  
    f_outro_sub = get_premium_rounded_font(28)   
    
    base_img = Image.new("RGB", (W, H))
    base_draw = ImageDraw.Draw(base_img)
    
    clean_q = re.sub(r'[^\x00-\x7F]+', '', question).strip()
    clean_a = re.sub(r'[^\x00-\x7F]+', '', answer).strip()
    
    clean_a = clean_a.rstrip('.!?') + "!!!"
    
    q_lines = get_wrapped_lines(base_draw, clean_q, f_body, W - 140)
    a_lines = get_wrapped_lines(base_draw, clean_a, f_body, W - 140)
    
    y_header = int(H * 0.13)
    y_question = int(H * 0.35)
    y_answer = int(H * 0.65)
    y_emoji = int(H * 0.81)

    gif_path = "assets/joy_emoji.gif"
    outro_image_path = "assets/subscribe.jpg"
    laughter_sound_path = "assets/laughter.mp3"

    gif_frames = []
    gif_duration = 100 
    if os.path.exists(gif_path):
        try:
            with Image.open(gif_path) as im:
                gif_duration = im.info.get('duration', 100) or 100
                for frame in ImageSequence.Iterator(im):
                    gif_frames.append(frame.convert("RGBA").copy())
        except Exception as e:
            print(f"⚠️ GIF Engine bypass: {e}")

    outro_canvas = None
    if os.path.exists(outro_image_path):
        try:
            outro_canvas = Image.new("RGB", (W, H), (255, 255, 255))
            raw_out = Image.open(outro_image_path).convert("RGBA")
            
            scale_w = W / float(raw_out.width)
            new_h = int(raw_out.height * scale_w)
            
            resized_out = raw_out.resize((W, new_h), Image.Resampling.LANCZOS)
            paste_y = (H - new_h) // 2
            outro_canvas.paste(resized_out, (0, paste_y), resized_out)
        except Exception as e:
            print(f"⚠️ Outro framing failed: {e}")

    def make_frame(t):
        if t >= 10.0:
            img = outro_canvas.copy() if outro_canvas else Image.new("RGB", (W, H), (255, 255, 255))
            draw = ImageDraw.Draw(img)
            
            txt_handle = "@Punderfuls"
            x_h = (W - tw(draw, txt_handle, f_outro_bold)) // 2
            draw.text((x_h, int(H * 0.78)), txt_handle, font=f_outro_bold, fill=(30, 30, 30))
            
            txt_cta = "Click Link Below to Subscribe!"
            x_c = (W - tw(draw, txt_cta, f_outro_sub)) // 2
            draw.text((x_c, int(H * 0.84)), txt_cta, font=f_outro_sub, fill=(215, 38, 93))
        else:
            img = Image.new("RGB", (W, H), COLOR_BG)

        if t < 10.0:
            draw_animated_word_pill(img, "Daily pun challenge", f_header, y_header, t)
            draw_sequential_question_card(img, q_lines, y_question, f_body, W - 80, t)
            
            if t >= 6.5:
                draw_clean_answer(img, a_lines, y_answer, f_body)
                
            if t >= 8.0 and gif_frames:
                elapsed_time_ms = int((t - 8.0) * 1000)
                frame_index = int(elapsed_time_ms / gif_duration) % len(gif_frames)
                current_frame = gif_frames[frame_index]
                
                pop_factor = min(1.0, (t - 8.0) * 4.0)
                cur_w = int(145 * (0.8 + 0.2 * pop_factor))
                
                resized_frame = current_frame.resize((cur_w, cur_w))
                img.paste(resized_frame, ((W - cur_w) // 2, y_emoji - (cur_w // 2)), resized_frame)

        return np.array(img).astype('uint8')

    clip = VideoClip(make_frame, duration=DURATION)
    audio_tracks = []

    if music_path and os.path.exists(music_path):
        bg_music = AudioFileClip(music_path)
        bg_music = audio_loop(bg_music, duration=DURATION) if bg_music.duration < DURATION else bg_music.subclip(0, DURATION)
        bg_music = bg_music.audio_fadeout(1.5)
        audio_tracks.append(bg_music)

    if os.path.exists(laughter_sound_path):
        laugh_clip = AudioFileClip(laughter_sound_path)
        laugh_clip = laugh_clip.set_start(8.0)  
        audio_tracks.append(laugh_clip)

    if audio_tracks:
        final_audio = CompositeAudioClip(audio_tracks)
        clip = clip.set_audio(final_audio)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    clip.write_videofile(
        output_path, fps=FPS, codec="libx264", audio_codec="aac",
        threads=4, preset="fast", ffmpeg_params=["-crf", "22"], logger=None,
    )
    clip.close()
    return output_path
