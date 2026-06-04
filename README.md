# Daily Pun Video Agent

Automatically generates and posts 2 punny YouTube Shorts every day.

```
Scheduler → Claude API (joke) → PIL+moviepy (video) → YouTube Data API (post)
```

---

## Quick-start (local machine)

### 1. Install dependencies

```bash
pip install -r requirements.txt
# macOS/Linux also need ffmpeg:
brew install ffmpeg          # macOS
sudo apt install ffmpeg      # Ubuntu/Debian
```

### 2. Get your API keys

**Anthropic API key**
- Sign up at https://console.anthropic.com and copy your key.

**YouTube OAuth credentials**
1. Go to https://console.cloud.google.com
2. Create a project → Enable **YouTube Data API v3**
3. Credentials → Create OAuth 2.0 Client ID (type: Desktop App)
4. Download JSON → rename to **`client_secrets.json`** → place in project root

### 3. Add funny music

Download a royalty-free MP3 from one of these (all free for YouTube):
- https://incompetech.filmmusic.io (search "quirky" or "comedy")
  - Suggested: "Quirky Dog" or "Sneaky Snitch" by Kevin MacLeod
- https://pixabay.com/music (filter: Funny / Comedy)

Save the file as `assets/funny_music.mp3`.

### 4. (Optional) Better font

Download **Bangers** from Google Fonts:
https://fonts.google.com/specimen/Bangers → Download family → extract
→ place `Bangers-Regular.ttf` inside the `assets/` folder.

Without it the agent uses whatever bold system font it finds — still looks fine.

### 5. Test with dry run

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python agent.py --dry-run
```

This renders both videos (into the `videos/` folder) without uploading.
Check them to make sure they look good.

### 6. Authenticate YouTube (first time only)

```bash
python agent.py
```

A browser window opens asking you to sign in to Google and allow access.
After clicking Allow, a `token.pickle` file is saved — future runs skip the browser step.

---

## Schedule it (pick one)

### Option A — cron on your Mac/Linux machine

```bash
crontab -e
```

Add these two lines:
```
0 9  * * * cd /path/to/pun_agent && ANTHROPIC_API_KEY=sk-ant-... python agent.py >> logs/agent.log 2>&1
0 17 * * * cd /path/to/pun_agent && ANTHROPIC_API_KEY=sk-ant-... python agent.py >> logs/agent.log 2>&1
```

### Option B — GitHub Actions (free cloud, no computer needed)

1. Push the project to a private GitHub repo.
2. Add these repository secrets (Settings → Secrets → Actions):
   - `ANTHROPIC_API_KEY` — your Anthropic key
   - `YOUTUBE_CLIENT_SECRETS` — contents of `client_secrets.json`
   - `YOUTUBE_TOKEN` — base64-encoded `token.pickle`:
     ```bash
     base64 token.pickle | tr -d '\n'   # copy the output
     ```
   - `MUSIC_B64` — base64-encoded MP3:
     ```bash
     base64 assets/funny_music.mp3 | tr -d '\n'
     ```
3. The workflow in `.github/workflows/schedule.yml` runs automatically at
   9 AM ET and 5 PM ET every day. You can also trigger it manually.

---

## Project layout

```
pun_agent/
├── agent.py               ← main runner
├── joke_generator.py      ← Claude API → pun Q&A
├── video_creator.py       ← PIL + moviepy → animated Short
├── youtube_uploader.py    ← YouTube Data API → upload
├── requirements.txt
├── assets/
│   ├── funny_music.mp3    ← you provide this
│   └── Bangers-Regular.ttf  ← optional
├── videos/                ← temp render folder (auto-created)
├── used_jokes.json        ← joke memory (auto-created)
├── client_secrets.json    ← you provide (from Google Cloud Console)
├── token.pickle           ← auto-created on first auth
└── .github/workflows/
    └── schedule.yml
```

---

## Customising the video

All timing and style lives in `video_creator.py`:

| What to change | Where |
|---|---|
| Video duration | `DURATION = 28` |
| Resolution | `W, H = 720, 1280` |
| Colors | `GOLD`, `PINK`, `CYAN`, `BG1/BG2` |
| Font sizes | `fxl`, `flg`, `fmd`, `fsm`, `fxs` |
| Phase timing | the `if t < …` branches in `make_frame()` |
| Subscribe text | Phase 6 block at the bottom |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: moviepy` | `pip install moviepy==1.0.3` |
| `ffmpeg not found` | Install ffmpeg for your OS (see step 1) |
| `FileNotFoundError: client_secrets.json` | Follow step 2 above |
| Videos render but are silent | Check `assets/funny_music.mp3` exists |
| YouTube says "quota exceeded" | API free tier = 10 000 units/day; uploads cost ~1600 units each — you have plenty for 2/day |
