<p align="center">
  <img src="assets/hero-showcase.png" alt="AI Video Production Studio" width="100%">
</p>

<h1 align="center">🎬 AI Video Forge</h1>
<p align="center"><strong>Open-Source Agentic Video Production — From Concept to MP4</strong></p>

<p align="center">
  <a href="https://github.com/KeshavCracks/video-production-buddy/stargazers">
    <img src="https://img.shields.io/github/stars/KeshavCracks/video-production-buddy?style=flat-square&color=5CC8FF&logo=github" alt="GitHub Stars">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/license-AGPLv3-blue.svg?style=flat-square" alt="License">
  </a>
  <a href="#">
    <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  </a>
  <a href="#">
    <img src="https://img.shields.io/badge/Remotion-React%20Video-61DAFB?style=flat-square&logo=react&logoColor=111" alt="Remotion">
  </a>
  <a href="#">
    <img src="https://img.shields.io/badge/FFmpeg-Required-007808?style=flat-square&logo=ffmpeg&logoColor=white" alt="FFmpeg">
  </a>
</p>

---

## What Is This?

**AI Video Forge** is a fully open-source, agent-driven video production system. Unlike black-box AI video generators that take one prompt and give you a surprise bill, this tool gives you **complete visibility and control** over every stage of production.

Your AI assistant (Claude, Cursor, Copilot, etc.) acts as the **producer** — following structured pipelines, managing assets, routing providers, and asking for your approval before spending money on API calls. You see the plan, approve the script, review the storyboard, and only then trigger generation.

### The Philosophy: Production-First, Not Generation-First

| Black-Box Tools | AI Video Forge |
|-----------------|----------------|
| One prompt → video | Staged pipeline with checkpoints |
| Hidden costs | Budget-aware provider routing |
| No revision history | Full JSON audit trails |
| Locked platforms | Your machine, your keys, your control |
| Vibe-check quality | Structured validation gates |

---

## 🚀 Get Started in 5 Minutes

### Zero-Key Local Demo (No API Keys Needed!)

```bash
# 1. Clone the repo
git clone https://github.com/KeshavCracks/video-production-buddy.git
cd video-production-buddy

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install everything
make setup

# 4. Run the free demo — renders locally using Remotion + FFmpeg
make demo
```

That's it. `make demo` produces MP4 files under `projects/demos/renders/` with **zero API calls**.

### System Requirements

| Tool | Why You Need It | Install Command |
|------|-----------------|-----------------|
| **Python 3.10+** | Tool runtime, provider registry | `brew/apt install python3` |
| **Node.js 22+** | Remotion composition, HyperFrames | `nvm install 22` or download from nodejs.org |
| **FFmpeg** | Video encoding, stitching, post-production | `brew/apt install ffmpeg` |
| **Make** | Build automation | `xcode-select --install` (Mac) / `apt install make` (Linux) |

### One-Click Cloud Setup (No Install Needed)

Open directly in **GitHub Codespaces** — the DevContainer installs everything automatically. Just click `Code → Codespaces → Create codespace on main` and run `make demo`.

---

## 🧠 How the Pipeline Works

```
Your Idea
    ↓
AI Assistant reads pipeline YAML
    ↓
Discovery Chat — audience, tone, constraints
    ↓
Research — trends, references, viral analysis
    ↓
Creative Brief — script, storyboard, emotion curve
    ↓
⏸️ HUMAN APPROVAL GATE
    ↓
Asset Generation — images, video, voice, music
    ↓
Composition — Remotion / FFmpeg / HyperFrames
    ↓
Quality Validation — scene checks, consistency audit
    ↓
Final MP4 + Full Production Log
```

Every stage produces **JSON artifacts** you can inspect, modify, or replay. No hidden magic.

---

## 🛠️ What You Can Build

| Use Case | Pipeline | Tools Used |
|----------|----------|------------|
| **Product Ads** | `ad-video` | Positioning, viral analysis, FLUX/ElevenLabs, Remotion |
| **Explainer Videos** | `explainer` | Script generation, Piper TTS, WhisperX subtitles, animated charts |
| **Social Clips** | `social-short` | FFmpeg chops, platform profiles, auto-captions |
| **AI Dubbing** | `localization` | WhisperX transcription, translation, re-voice |
| **Documentary Montage** | `documentary` | Stock footage, music scoring, scene fidelity checks |

---

## 💰 Free vs. Paid — You Control the Bill

### Completely Free (Local Mode)
- ✅ **Piper TTS** — offline text-to-speech
- ✅ **Remotion** — React-based video composition
- ✅ **FFmpeg** — all post-processing
- ✅ **HyperFrames** — HTML/CSS motion graphics
- ✅ **Local Diffusion** — if you have an NVIDIA GPU

### Optional Cloud APIs (Pay-Per-Use)
Bring your own keys only when you need premium quality:

| Provider | What It Unlocks | Free Tier? |
|----------|-----------------|------------|
| **fal.ai** | FLUX images, video generation | Limited credits |
| **ElevenLabs** | Premium voice, music, SFX | Free tier available |
| **OpenAI** | DALL-E, GPT-4o voice | Pay-per-use |
| **Google** | Imagen, 700+ TTS voices | Generous free tier |
| **Suno** | Full song generation | Limited free gens |
| **Pexels/Pixabay** | Stock footage & images | Completely free |

Set keys in `.env` (copy from `.env.example`). The assistant will **always ask before spending**.

---

## 🏗️ Repo Structure

```
video-production-buddy/
├── .devcontainer/          # One-click GitHub Codespaces setup
├── website/                # Next.js showcase site (deploy to Vercel)
├── remotion-composer/      # React video composition engine
├── pipeline_defs/            # YAML pipeline manifests (the "recipes")
├── skills/                 # Stage director instructions for the AI
├── tools/                  # 47+ provider tools (image, video, voice, etc.)
├── schemas/                # JSON contracts for every artifact
├── lib/                    # Core runtime, checkpoints, validation
├── tests/                  # Contract + integration tests
├── Dockerfile              # Docker setup
├── docker-compose.yml      # One-command Docker stack
├── HOSTING.md              # Full deployment guides
└── README.md               # You are here
```

---

## 🌐 Showcase Website

The `website/` folder contains a **Next.js 14 landing page** you can deploy anywhere:

```bash
cd website
npm install
npm run build
# Static export goes to website/dist/
```

**Deploy to Vercel (free):**
1. Import `KeshavCracks/video-production-buddy` into [vercel.com](https://vercel.com)
2. Set **Root Directory** to `website`
3. Set **Framework Preset** to `Next.js`
4. Deploy

Or let the GitHub Action (`.github/workflows/vercel-website.yml`) auto-deploy on every push.

---

## 🤖 Using With Your AI Assistant

This repo is designed to be **operated by an AI coding assistant** (Cursor, Claude Code, Copilot, etc.).

**Starter prompts to try:**

```text
Create a 30-second product ad for a sustainable water bottle.
Target: eco-conscious millennials. Platform: Instagram Reels.
Style: clean, modern, upbeat.
```

```text
Make a 60-second animated explainer about how black holes work.
Audience: curious teenagers. Use simple visuals and calm narration.
```

```text
Turn this blog post into a 45-second LinkedIn video with captions and B-roll.
```

The assistant reads the pipeline manifest, discovers available tools, and walks you through each stage.

---

## 🧪 Testing & Development

```bash
make test              # Fast contract tests (no APIs needed)
make test-integration  # Full runtime tests (needs FFmpeg, Node, browser)
make preflight         # Show all available providers and runtimes
make demo              # Render the zero-key demo suite
```

---

## 📜 License & Attribution

This project is licensed under **GNU AGPLv3**. It is a community fork and enhancement of the original research work.

- **Original research foundation:** [OpenMontage](https://github.com/calesthio/OpenMontage) by Calesthio
- **Academic lineage:** Developed by the AI4GC Lab at Zhejiang University
- **This distribution:** Community-enhanced with Docker, DevContainers, hosting guides, and a showcase website

If you build on this code or host it publicly, you must share your source under AGPLv3.

---

<p align="center">
  <strong>Built for creators who want to own their pipeline.</strong>
  <br><br>
  <a href="https://github.com/KeshavCracks/video-production-buddy">
    <img src="https://img.shields.io/badge/⭐_Star_this_repo-5CC8FF?style=for-the-badge&logo=github&logoColor=white" alt="Star">
  </a>
</p>
