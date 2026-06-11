"""
agent.py  —  Daily Pun Video Agent
Run this file twice a day (via cron or GitHub Actions) to generate and
post new pun Shorts to your YouTube channel.

Usage:
    python agent.py              # post videos
    python agent.py --dry-run    # generate & render but skip YouTube upload
"""

import argparse
import datetime
import json
import os
import sys

from joke_generator   import generate_pun_joke
from video_creator    import create_pun_video
from youtube_uploader import upload_video

# ── Config ────────────────────────────────────────────────────────────────────
VIDEOS_PER_RUN = 1
MUSIC_FILE     = "assets/funny_music.mp3"
OUTPUT_DIR     = "videos"
USED_FILE      = "used_jokes.json"

HASHTAGS_STACK = "#shorts #animation #funnyshorts #dadjokes #comedy #jokeoftheday #funny #puns #comedyshorts"
SUBSCRIBE_LINK = "https://www.youtube.com/@Punderfuls?sub_confirmation=1"


# ── Joke memory ───────────────────────────────────────────────────────────────
def load_used() -> list:
    if os.path.exists(USED_FILE):
        with open(USED_FILE) as f:
            return json.load(f)
    return []


def save_used(questions: list[str]):
    trimmed = questions[-200:]
    with open(USED_FILE, "w") as f:
        json.dump(trimmed, f, indent=2)


# ── One video cycle ───────────────────────────────────────────────────────────
def run_one(index: int, used_questions: list[str], dry_run: bool) -> str:
    print(f"\n{'─'*50}")
    print(f"  Video {index + 1} of {VIDEOS_PER_RUN}")
    print(f"{'─'*50}")

    # 1. Generate joke
    print("📝  Generating joke…")
    joke = generate_pun_joke(used_questions)
    print(f"    Q: {joke['question']}")
    print(f"    A: {joke['answer']}  {joke['emojis']}")

    # 2. Render video
    ts         = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    video_path = os.path.join(OUTPUT_DIR, f"pun_{ts}_{index}.mp4")

    print("🎬  Rendering video…")
    create_pun_video(
        question    = joke["question"],
        answer      = joke["answer"],
        emojis      = joke["emojis"],
        music_path  = MUSIC_FILE,
        output_path = video_path,
    )

    # 3. Upload (unless dry run)
    if dry_run:
        print("⏭️   Dry-run: skipping YouTube upload.")
    else:
        print("📤  Uploading to YouTube…")

        title_question = joke["question"].strip()
        title = f"{title_question} #shorts"
        if len(title) > 100:
            title = f"{title_question[:90]}... #shorts"

        description = (
            f"🤣 {joke['question'].strip()}\n\n"
            f"Subscribe to Punderfuls for daily animations & jokes! 👇\n"
            f"👉 {SUBSCRIBE_LINK}\n\n"
            f"{HASHTAGS_STACK}"
        )

        upload_video(video_path, title, description)

        # Clean up local file only after successful upload
        if os.path.exists(video_path):
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

    # Load history and normalize to plain strings
    used = load_used()
    used_questions = [
        j.get("question", j) if isinstance(j, dict) else j
        for j in used
    ]

    posted = []
    for i in range(VIDEOS_PER_RUN):
        try:
            question = run_one(i, used_questions + posted, args.dry_run)
            posted.append(question)
        except Exception as exc:
            print(f"❌  Video {i + 1} failed: {exc}", file=sys.stderr)

    save_used(used_questions + posted)
    print(f"\n✅  Done! {len(posted)}/{VIDEOS_PER_RUN} videos posted today.")


if __name__ == "__main__":
    main()
