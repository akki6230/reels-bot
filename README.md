# 🎬 Instagram Reels Bot — Complete Setup Guide

Fully automated educational Reels posted daily on Space, History, Geography & Science.
**Cost: $0/month** · Powered by GitHub Actions + Claude AI

---

## How It Works

```
Every day at 9AM / 1PM / 6PM IST:
  GitHub Actions wakes up (free)
      ↓
  Claude API generates a fact (< $0.01)
      ↓
  Unsplash fetches a background image (free)
      ↓
  MoviePy renders a 1080×1920 Reel (free)
      ↓
  Freesound adds background music (free)
      ↓
  Instagrapi posts it to Instagram (free)
      ↓
  Dashboard updates on GitHub Pages (free)
```

---

## Step 1 — Fork & Clone This Repo

```bash
# Fork on GitHub first, then:
git clone https://github.com/YOUR_USERNAME/reels-bot.git
cd reels-bot
```

---

## Step 2 — Get Your API Keys

### A) Anthropic (Claude) — REQUIRED
1. Go to https://console.anthropic.com/
2. Create an account → API Keys → Create Key
3. Copy the key (starts with `sk-ant-…`)

### B) Instagram — REQUIRED
- Use a **dedicated Instagram account** (not your personal one)
- Just your username and password — no Meta API needed
- Tip: create a fresh account like `@daily.space.facts`

### C) Pexels — FREE, no attribution required ✅
1. Go to https://www.pexels.com/api/
2. Click "Get Started" → Create free account
3. Go to https://www.pexels.com/api/new/ → Create app
4. Copy your API Key
- Free tier: 200 requests/hour, 20,000/month (way more than enough)
- **No attribution required** — images are free to use in any project

### D) Freesound — FREE, recommended
1. Go to https://freesound.org/apiv2/apply/
2. Create account → Apply for API access → Copy API Key
- Gives royalty-free music for every reel

---

## Step 3 — Add Secrets to GitHub

Go to your repo → **Settings → Secrets and variables → Actions → New repository secret**

Add these secrets:

| Secret Name           | Value                          |
|-----------------------|--------------------------------|
| `ANTHROPIC_API_KEY`   | Your Claude API key            |
| `INSTAGRAM_USERNAME`  | Your Instagram username        |
| `INSTAGRAM_PASSWORD`  | Your Instagram password        |
| `PEXELS_API_KEY`      | Your Pexels API key            |
| `FREESOUND_API_KEY`   | Your Freesound API key         |

> **Note:** `IG_SESSION_DATA` will be auto-populated after the first run.

---

## Step 4 — Enable GitHub Pages (for Dashboard)

1. Go to repo → **Settings → Pages**
2. Source: **GitHub Actions**
3. Save

Your dashboard will be live at:
`https://YOUR_USERNAME.github.io/reels-bot/`

---

## Step 5 — Do a Test Run (IMPORTANT — do this first!)

1. Go to repo → **Actions tab**
2. Click **"🚀 Post Daily Educational Reels"**
3. Click **"Run workflow"**
4. Set `topic` = `space`
5. Set `dry_run` = `true` ← This generates the video but does NOT post to Instagram
6. Click **"Run workflow"** button

Watch the logs. After it succeeds:
- Download the video artifact to see how it looks
- If you're happy, run again with `dry_run = false`

---

## Step 6 — Sit Back, It Runs Automatically

The bot posts **3 times every day**:

| Time (IST) | Topic |
|------------|-------|
| 9:00 AM    | 🚀 Space & Universe |
| 1:00 PM    | 📜 World History |
| 6:00 PM    | 🌍 Geography (Mon/Wed/Fri) or 🔬 Science (Tue/Thu/Sat/Sun) |

---

## Project Structure

```
reels-bot/
├── .github/
│   └── workflows/
│       ├── post_reels.yml        ← Main automation (runs 3x daily)
│       └── deploy_dashboard.yml  ← Deploys dashboard to GitHub Pages
├── src/
│   ├── main.py           ← Pipeline orchestrator
│   ├── config.py         ← Topics, colors, hashtags
│   ├── pick_topic.py     ← Decides topic from schedule
│   ├── fact_gen.py       ← Claude API fact generation
│   ├── video.py          ← MoviePy reel rendering
│   ├── music.py          ← Freesound music fetcher
│   ├── poster.py         ← Instagram uploader
│   └── update_dashboard.py  ← Writes dashboard/data.json
├── dashboard/
│   ├── index.html        ← Live monitoring dashboard (GitHub Pages)
│   └── data.json         ← Auto-updated stats (committed by Actions)
├── fonts/                ← (optional) Add Poppins-Bold.ttf here
├── music/                ← (optional) Add local .mp3 files here
├── output/
│   └── used_facts.json   ← Tracks used topics to avoid repeats
└── requirements.txt
```

---

## Customization

### Change posting times
Edit `.github/workflows/post_reels.yml` — change the `cron:` lines:
```yaml
# Cron format: minute hour * * *  (UTC time)
- cron: "30 3 * * *"    # 3:30 UTC = 9:00 AM IST
- cron: "30 7 * * *"    # 7:30 UTC = 1:00 PM IST
- cron: "30 12 * * *"   # 12:30 UTC = 6:00 PM IST
```

### Add a new topic
In `src/config.py`, add to the `TOPICS` dict:
```python
"mathematics": {
    "name": "Math Facts",
    "emoji": "🔢",
    "music_mood": "electronic upbeat discovery",
    "hashtags": "#math #mathematics #mathtricks ...",
    "image_keywords": ["mathematics", "equations", "numbers"],
    "color_scheme": {
        "bg": (5, 15, 25), "accent": (255, 200, 50), "text": (255, 245, 200)
    },
},
```
Then add a prompt in `src/fact_gen.py` → `TOPIC_PROMPTS`.

### Add custom fonts (better-looking text)
1. Download Poppins from https://fonts.google.com/specimen/Poppins
2. Place `Poppins-Bold.ttf` and `Poppins-Regular.ttf` in the `fonts/` folder
3. Commit and push

### Add your own music
Place `.mp3` files in:
```
music/space/     ← space reels
music/history/   ← history reels
music/geography/ ← geography reels
music/science/   ← science reels
```
These take priority over Freesound.

---

## Troubleshooting

### Instagram challenge / login failure
Instagram sometimes requires verification on new logins from unfamiliar IPs (GitHub's servers).

**Fix:**
1. Log into Instagram on your phone, approve any security prompts
2. Re-run the workflow
3. Once logged in successfully, the session is cached and reused

### "No module named X"
The workflow installs all deps automatically. If running locally:
```bash
pip install -r requirements.txt
sudo apt install ffmpeg   # Linux
brew install ffmpeg       # Mac
```

### Workflow runs but video looks bad
Run a dry-run from the Actions tab, download the artifact video, and inspect it.
Then tweak `src/video.py` — adjust font sizes, text positions, timing.

### Rate limits
- Anthropic: generous free tier, shouldn't hit limits at 3 facts/day
- Unsplash: 50 req/hr free — well within limits
- Instagram: don't post more than 5 reels/day to avoid flags

---

## Cost Summary

| Service | Usage | Cost |
|---------|-------|------|
| GitHub Actions | ~15 min/day | **Free** (2000 min/month free) |
| Claude API | 3 fact generations/day | **~$0.03/month** |
| Unsplash API | 3 images/day | **Free** |
| Freesound API | 3 tracks/day (cached) | **Free** |
| GitHub Pages | Dashboard hosting | **Free** |
| **Total** | | **~$0.03/month** |

---

## License
MIT — use freely, credit appreciated.
