"""
agent.py  —  Daily Pun Video Agent
Run this file twice a day (via cron or GitHub Actions) to generate and
post 2 new pun Shorts to your YouTube channel.

Usage:
    python agent.py              # post 2 videos
    python agent.py --dry-run    # generate & render but skip YouTube upload
"""

import argparse
import datetime
import json
import os
import sys

from joke_generator import generate_pun_joke
from video_creator  import create_pun_video
from youtube_uploader import upload_video

# ── Config ────────────────────────────────────────────────────────────────────
VIDEOS_PER_RUN = 1
MUSIC_FILE     = "assets/funny_music.mp3"
OUTPUT_DIR     = "videos"
USED_FILE      = "used_jokes.json"

# Exact hashtag list string required for short optimization
HASHTAGS_STACK = "#shorts #animation #funnyshorts #dadjokes #comedy #jokeoftheday #funny #puns #comedyshorts"
SUBSCRIBE_LINK = "https://www.youtube.com/@Punderfuls?sub_confirmation=1"

# ── Joke memory ───────────────────────────────────────────────────────────────
def load_used() -> list[str]:
    if os.path.exists(USED_FILE):
        with open(USED_FILE) as f:
            return json.load(f)
    return []

def save_used(questions: list[str]):
    trimmed = questions[-200:]          # keep last 200 so file stays small
    with open(USED_FILE, "w") as f:
        json.dump(trimmed, f, indent=2)


# ── One video cycle ───────────────────────────────────────────────────────────
def run_one(index: int, used: list[str], dry_run: bool) -> str | None:
    print(f"\n{'─'*50}")
    print(f"  Video {index + 1} of {VIDEOS_PER_RUN}")
    print(f"{'─'*50}")

    # 1. Generate joke
    print("📝  Generating joke…")
    joke = generate_pun_joke(used)
    print(f"    Q: {joke['question']}")
    print(f"    A: {joke['answer']}  {joke['emojis']}")

    # 2. Render video
    ts         = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    video_path = os.path.join(OUTPUT_DIR, f"pun_{ts}_{index}.mp4")

    print("🎬  Rendering video…")
    # Passes data fields safely to avoid unexpected keyword argument crashes
    create_pun_video(
        question   = joke["question"],
        answer     = joke["answer"],
        emojis     = joke["emojis"],
        music_path = MUSIC_FILE,
        output_path= video_path,
    )

    # 3. Upload (unless dry run)
    video_id = None
    if dry_run:
        print("⏭️  Dry-run: skipping YouTube upload.")
    else:
        print("📤  Uploading to YouTube…")
        
        # --- REQUIREMENT: Title caption shows ONLY the question and hashtags ---
        raw_title = f"{joke['question'].strip()} {HASHTAGS_STACK}"
        
        # Guard against YouTube's 100 character title constraint limit
        if len(raw_title) > 100:
            allowed_q_len = 95 - len(HASHTAGS_STACK)
            title = f"{joke['question'].strip()[:allowed_q_len]}... {HASHTAGS_STACK}"
        else:
            title = raw_title
            
        # --- REQUIREMENT: Include your precise channel subscribe URL in description ---
        description = (
            f"🤣 {joke['question'].strip()}\n\n"
            f"Subscribe to Punderfuls for daily animations & jokes! 👇\n"
            f"👉 {SUBSCRIBE_LINK}\n\n"
            f"{HASHTAGS_STACK}"
        )
        
        video_id = upload_video(video_path, title, description)

    # Clean up local file after upload
    if os.path.exists(video_path) and not dry_run:
        os.remove(video_path)

    return joke["question"]


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Daily Pun Video Agent")
    parser.add_argument("--dry-run", action="store_true",
                        help="Render videos but skip YouTube upload")
    args = parser.parse_args()

    print(f"\n🤖  Pun Video Agent  —  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"    dry_run = {args.dry_run}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    used = load_used()

    posted = []
    for i in range(VIDEOS_PER_RUN):
        try:
            question = run_one(i, used + posted, args.dry_run)
            posted.append(question)
        except Exception as exc:
            print(f"❌  Video {i+1} failed: {exc}", file=sys.stderr)

    # Persist used jokes
    save_used(used + posted)

    print(f"\n✅  Done! {len(posted)}/{VIDEOS_PER_RUN} videos posted today.")


if __name__ == "__main__":
    main()
