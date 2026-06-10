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

# --- GLOBAL REEL DIMENSIONS (9:16 Vertical HD) ---
W, H      = 720, 1280
FPS       = 30
DURATION  = 12.0

# --- DESIGN PALETTE ---
COLOR_BG_TOP      = (255, 255, 255)   # Pure white
COLOR_BG_BOTTOM   = (245, 245, 248)   # Very subtle cool-grey — barely visible
COLOR_HEADER_PILL = (255, 210, 225)   # Pastel pink pill
COLOR_HEADER_TEXT = (200, 30, 80)     # Deep magenta
COLOR_CARD_Q      = (18, 18, 24)      # Near-black
COLOR_CARD_SHADOW = (180, 180, 190)   # Neutral grey shadow — no pink tint
COLOR_TEXT_Q      = (255, 255, 255)
COLOR_TEXT_A      = (18, 18, 24)
COLOR_ANSWER_PILL = (255, 210, 225)   # Answer gets the same pink pill treatment
COLOR_ANSWER_TEXT = (200, 30, 80)     # Same magenta — unifies the design


def get_premium_rounded_font(size):
    """Loads the best available bold rounded font, with a clear warning on fallback."""
    paths = [
        "assets/Fredoka-Bold.ttf",
        "assets/LilitaOne-Regular.ttf",
        "C:/Windows/Fonts/ariblk.ttf",
        "/Library/Fonts/Arial Black.ttf",
        "/System/Library/Fonts/Supplemental/Arial Black.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    print(f"⚠️  WARNING: No custom font found — falling back to default bitmap font. "
          f"Text will look poor. Place Fredoka-Bold.ttf in ./assets/ for best results.")
    return ImageFont.load_default()


def tw(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0]

def th(draw, font):
    bb = draw.textbbox((0, 0), "Ag", font=font)
    return bb[3] - bb[1]

def t_offset(draw, font):
    """Returns the internal top offset (bb[1]) PIL adds above glyphs.
    Subtract this from any y coordinate to make text sit where you intend."""
    return draw.textbbox((0, 0), "Ag", font=font)[1]

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


def ease_out_cubic(x):
    """Snappier, more modern easing than sin-based ease. Feels like a real app."""
    return 1.0 - (1.0 - min(1.0, x)) ** 3


def ease_out_back(x, overshoot=1.4):
    """Overshoots slightly then settles — great for answer reveal 'thud' effect."""
    x = min(1.0, x)
    c1 = overshoot
    c3 = c1 + 1
    return 1 + c3 * ((x - 1) ** 3) + c1 * ((x - 1) ** 2)


def draw_gradient_background(img):
    """Draws a subtle vertical warm gradient instead of flat white."""
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        r = int(COLOR_BG_TOP[0] + (COLOR_BG_BOTTOM[0] - COLOR_BG_TOP[0]) * t)
        g = int(COLOR_BG_TOP[1] + (COLOR_BG_BOTTOM[1] - COLOR_BG_TOP[1]) * t)
        b = int(COLOR_BG_TOP[2] + (COLOR_BG_BOTTOM[2] - COLOR_BG_TOP[2]) * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))



def draw_pill(draw, text, font, center_x, center_y,
              fill_color, text_color,
              padding_x=44, padding_y=20, radius=999):
    """Generic pill renderer — used for both header and answer."""
    w = tw(draw, text, font)
    h = th(draw, font)
    pill_w = w + padding_x * 2
    pill_h = h + padding_y * 2
    x0 = center_x - pill_w // 2
    y0 = center_y - pill_h // 2
    x1 = x0 + pill_w
    y1 = y0 + pill_h
    # Clamp radius so PIL doesn't reject it
    r = min(radius, pill_h // 2)
    draw.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=fill_color)
    draw.text((x0 + padding_x, y0 + padding_y - 2), text, font=font, fill=text_color)
    return pill_w, pill_h


def draw_card_shadow(img, x0, y0, x1, y1, radius=28, blur=18, shadow_color=COLOR_CARD_SHADOW):
    """Paints a blurred shadow behind the question card for depth."""
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    # Offset shadow down and right slightly
    sx0, sy0, sx1, sy1 = x0 + 6, y0 + 10, x1 + 6, y1 + 10
    sd.rounded_rectangle([sx0, sy0, sx1, sy1], radius=radius,
                         fill=(*shadow_color, 120))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=blur))
    img.paste(Image.alpha_composite(img.convert("RGBA"), shadow).convert("RGB"))


def draw_animated_word_pill(img, full_text, font, center_y, t):
    """Header pill — words drop in one by one."""
    draw = ImageDraw.Draw(img)
    words = full_text.split()

    text_w = tw(draw, full_text, font)
    text_h = th(draw, font)
    padding_x, padding_y = 44, 20
    pill_w = text_w + padding_x * 2
    pill_h = text_h + padding_y * 2
    radius = pill_h // 2  # fully rounded ends

    x0 = (W - pill_w) // 2
    y0 = center_y - pill_h // 2
    x1 = x0 + pill_w
    y1 = y0 + pill_h

    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=COLOR_HEADER_PILL)

    space_w = tw(draw, " ", font)
    current_x = x0 + padding_x

    for i, word in enumerate(words):
        word_delay = i * 0.20
        if t >= word_delay:
            word_t = t - word_delay
            progress = ease_out_cubic(word_t / 0.18)
            bounce_y = (1.0 - progress) * -45
            top_off = draw.textbbox((0,0), word, font=font)[1]
            draw.text((current_x, y0 + padding_y + bounce_y - top_off),
                      word, font=font, fill=COLOR_HEADER_TEXT)
        current_x += tw(draw, word, font) + space_w


def draw_sequential_question_card(img, lines, center_y, font, max_w, t, padding=48):
    """Question card with drop shadow and word-by-word animation."""
    draw = ImageDraw.Draw(img)
    lh = int(th(draw, font) * 1.38)
    text_h = th(draw, font)
    # lh*(n-1) + text_h = actual text block height (no extra gap after last line)
    # Equal padding top and bottom gives symmetric margins inside the card.
    text_block_h = lh * (len(lines) - 1) + text_h
    card_h = text_block_h + (padding * 2)

    margin = 44
    x0 = margin
    y0 = center_y - card_h // 2
    x1 = W - margin
    y1 = y0 + card_h

    # Shadow first so card paints on top
    draw_card_shadow(img, x0, y0, x1, y1)

    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([x0, y0, x1, y1], radius=28, fill=COLOR_CARD_Q)

    start_delay = 0.65
    space_w = tw(draw, " ", font)
    word_counter = 0

    top_off = t_offset(draw, font)  # internal PIL leading above glyphs
    curr_y = y0 + padding - top_off  # shift up so glyphs start exactly at padding
    for line in lines:
        words = line.split()
        line_w = tw(draw, line, font)
        current_x = (W - line_w) // 2

        for word in words:
            word_delay = start_delay + word_counter * 0.065
            if t >= word_delay:
                w_t = t - word_delay
                progress = ease_out_cubic(w_t / 0.13)
                fall_y = (1.0 - progress) * -32
                draw.text((current_x, curr_y + fall_y),
                          word, font=font, fill=COLOR_TEXT_Q)
            current_x += tw(draw, word, font) + space_w
            word_counter += 1

        curr_y += lh


def draw_answer_reveal(img, lines, center_y, font, t, reveal_start=6.5):
    """
    Answer text in pink pills that scale + bounce in.
    Each line is its own pill. Padding is symmetric using cap-height only.
    """
    draw = ImageDraw.Draw(img)
    padding_x, padding_y = 40, 22
    gap_between = 12  # vertical gap between pills

    # pill_h is based on cap-height (th) not line-height, so padding is equal top/bottom
    base_text_h = th(draw, font)
    pill_h_base = base_text_h + padding_y * 2
    total_h = len(lines) * pill_h_base + (len(lines) - 1) * gap_between
    start_y = center_y - total_h // 2

    for i, line in enumerate(lines):
        line_delay = reveal_start + i * 0.18
        pill_slot_y = start_y + i * (pill_h_base + gap_between)
        cy = pill_slot_y + pill_h_base // 2

        if t < line_delay:
            continue

        elapsed = t - line_delay
        scale = ease_out_back(elapsed / 0.22)
        scale = max(0.0, min(1.15, scale))

        text_w = tw(draw, line, font)
        pill_w = int((text_w + padding_x * 2) * scale)
        pill_h = int(pill_h_base * scale)

        cx = W // 2
        x0 = cx - pill_w // 2
        y0 = cy - pill_h // 2
        x1 = cx + pill_w // 2
        y1 = cy + pill_h // 2

        if pill_w > 10 and pill_h > 10:
            radius = min(pill_h // 2, 999)
            draw.rounded_rectangle([x0, y0, x1, y1], radius=radius,
                                   fill=COLOR_ANSWER_PILL)
            if scale > 0.7:
                tx = cx - text_w // 2
                # Centre using actual glyph bbox: subtract bb[1] so the visible
                # glyphs are exactly centred, not the bounding box with its leading.
                bb = draw.textbbox((0, 0), line, font=font)
                glyph_h = bb[3] - bb[1]
                ty = cy - glyph_h // 2 - bb[1]
                draw.text((tx, ty), line, font=font, fill=COLOR_ANSWER_TEXT)


# --- CORE PIPELINE RENDER ENGINE ---
def create_pun_video(question, answer, output_path, music_path=None, **kwargs):
    # Slightly larger fonts — more readable in a mobile feed
    f_header    = get_premium_rounded_font(38)
    f_body      = get_premium_rounded_font(62)   # was 52
    f_answer    = get_premium_rounded_font(66)   # answer is the payoff — make it biggest
    f_outro_bold = get_premium_rounded_font(44)
    f_outro_sub  = get_premium_rounded_font(30)

    base_img  = Image.new("RGB", (W, H))
    base_draw = ImageDraw.Draw(base_img)

    clean_q = re.sub(r'[^\x00-\x7F]+', '', question).strip()
    clean_a = re.sub(r'[^\x00-\x7F]+', '', answer).strip()

    # Single exclamation mark — triple !!! looks amateurish
    clean_a = clean_a.rstrip('.!?') + "!"

    q_lines = get_wrapped_lines(base_draw, clean_q, f_body,   W - 160)
    a_lines = get_wrapped_lines(base_draw, clean_a, f_answer, W - 120)

    y_header   = int(H * 0.12)
    y_question = int(H * 0.36)
    y_answer   = int(H * 0.66)
    y_emoji    = int(H * 0.855)   # pushed down away from answer text

    gif_path         = "assets/joy_emoji.gif"
    outro_image_path = "assets/subscribe.jpg"
    laughter_sound_path = "assets/laughter.mp3"

    # Pre-load GIF frames with correct transparency handling.
    # GIFs store transparency as a palette index, not a real alpha channel.
    # PIL's convert("RGBA") often maps this incorrectly (transparency index may
    # point to a color that is used for BOTH the background AND internal pixels
    # like teeth). The only reliable fix is to read the raw palette index array,
    # find which index is the actual background, zero those pixels' alpha, and
    # keep all other white-ish pixels (teeth, etc.) fully opaque.
    gif_frames   = []
    gif_duration = 100
    def _remove_white_background(rgba_img, threshold=30):
        """BFS flood-fill from corners — removes connected white background,
        leaves internal white pixels (teeth) untouched."""
        from collections import deque
        arr = np.array(rgba_img).copy()
        H2, W2 = arr.shape[:2]

        def is_near_white(y, x):
            r, g, b = int(arr[y,x,0]), int(arr[y,x,1]), int(arr[y,x,2])
            return r > (255-threshold) and g > (255-threshold) and b > (255-threshold)

        visited = np.zeros((H2, W2), dtype=bool)
        queue = deque()
        for cy, cx in [(0,0),(0,W2-1),(H2-1,0),(H2-1,W2-1)]:
            if is_near_white(cy, cx) and not visited[cy, cx]:
                visited[cy, cx] = True
                queue.append((cy, cx))

        while queue:
            y, x = queue.popleft()
            arr[y, x, 3] = 0
            for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
                ny, nx = y+dy, x+dx
                if 0 <= ny < H2 and 0 <= nx < W2 and not visited[ny,nx] and is_near_white(ny,nx):
                    visited[ny, nx] = True
                    queue.append((ny, nx))

        return Image.fromarray(arr, 'RGBA')

    if os.path.exists(gif_path):
        try:
            with Image.open(gif_path) as im:
                gif_duration = im.info.get('duration', 100) or 100
                for frame in ImageSequence.Iterator(im):
                    rgba = frame.convert("RGBA")
                    rgba = _remove_white_background(rgba)
                    gif_frames.append(rgba)
        except Exception as e:
            print(f"⚠️ GIF load failed: {e}")

    # Pre-build outro canvas
    outro_canvas = None
    if os.path.exists(outro_image_path):
        try:
            outro_canvas = Image.new("RGB", (W, H), (255, 248, 250))
            raw_out = Image.open(outro_image_path).convert("RGBA")
            scale_w = W / float(raw_out.width)
            new_h   = int(raw_out.height * scale_w)
            resized_out = raw_out.resize((W, new_h), Image.Resampling.LANCZOS)
            paste_y = (H - new_h) // 2
            outro_canvas.paste(resized_out, (0, paste_y), resized_out)
        except Exception as e:
            print(f"⚠️ Outro image load failed: {e}")

    def make_frame(t):
        # ── OUTRO (last 2 s) ────────────────────────────────────────────
        if t >= 10.0:
            img = outro_canvas.copy() if outro_canvas \
                  else Image.new("RGB", (W, H), (255, 248, 250))
            draw = ImageDraw.Draw(img)

            handle = "@Punderfuls"
            draw.text(((W - tw(draw, handle, f_outro_bold)) // 2, int(H * 0.78)),
                      handle, font=f_outro_bold, fill=(25, 25, 35))

            cta = "\u2193  Subscribe Below  \u2193"   # ↓ unicode arrows look clean
            draw.text(((W - tw(draw, cta, f_outro_sub)) // 2, int(H * 0.845)),
                      cta, font=f_outro_sub, fill=COLOR_HEADER_TEXT)
            return np.array(img).astype('uint8')

        # ── MAIN FRAME ──────────────────────────────────────────────────
        img = Image.new("RGB", (W, H))
        draw_gradient_background(img)

        draw_animated_word_pill(img, "Daily Pun Challenge", f_header, y_header, t)
        draw_sequential_question_card(img, q_lines, y_question, f_body, W - 80, t)

        if t >= 6.5:
            draw_answer_reveal(img, a_lines, y_answer, f_answer, t, reveal_start=6.5)

        if t >= 8.0 and gif_frames:
            elapsed_ms  = int((t - 8.0) * 1000)
            frame_index = int(elapsed_ms / gif_duration) % len(gif_frames)
            frame       = gif_frames[frame_index]  # already RGBA with correct alpha

            pop = min(1.0, (t - 8.0) * 4.0)
            cur_w = int(150 * ease_out_back(pop, overshoot=0.6))
            cur_w = max(10, cur_w)

            resized = frame.resize((cur_w, cur_w), Image.Resampling.LANCZOS)
            # Paste using the alpha channel as the mask — no square background
            img.paste(resized, ((W - cur_w) // 2, y_emoji - cur_w // 2),
                      mask=resized.split()[3])

        return np.array(img).astype('uint8')

    clip = VideoClip(make_frame, duration=DURATION)

    # ── AUDIO ────────────────────────────────────────────────────────────
    audio_tracks = []
    if music_path and os.path.exists(music_path):
        bg = AudioFileClip(music_path)
        bg = audio_loop(bg, duration=DURATION) if bg.duration < DURATION \
             else bg.subclip(0, DURATION)
        bg = bg.audio_fadeout(1.5)
        audio_tracks.append(bg)

    if os.path.exists(laughter_sound_path):
        laugh = AudioFileClip(laughter_sound_path).set_start(8.0)
        audio_tracks.append(laugh)

    if audio_tracks:
        clip = clip.set_audio(CompositeAudioClip(audio_tracks))

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    clip.write_videofile(
        output_path, fps=FPS, codec="libx264", audio_codec="aac",
        threads=4, preset="fast", ffmpeg_params=["-crf", "22"], logger=None,
    )
    clip.close()
    return output_path
