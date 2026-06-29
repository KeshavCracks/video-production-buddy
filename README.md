<p align="center">
  <img src="assets/logo.png" alt="Video Production Buddy" width="160">
</p>

<h1 align="center">Video Production Buddy</h1>

<p align="center">
  <strong>🎬 The Open-Source, Agent-First AI Video Production Studio</strong>
</p>

<p align="center">
  Plan → Approve → Generate → Compose → Verify
</p>

<p align="center">
  <a href="https://github.com/KeshavCracks/video-production-buddy/stargazers"><img src="https://img.shields.io/github/stars/KeshavCracks/video-production-buddy?style=flat-square&color=5CC8FF&logo=github" alt="Stars"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPLv3-blue.svg?style=flat-square" alt="License: AGPLv3"></a>
  <a href="https://github.com/KeshavCracks/video-production-buddy/actions"><img src="https://img.shields.io/badge/build-passing-brightgreen?style=flat-square&logo=githubactions" alt="Build"></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Agent--First-Video%20Production-5CC8FF?style=flat-square" alt="Agent-first">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FFmpeg-Post--Production-007808?style=flat-square&logo=ffmpeg&logoColor=white" alt="FFmpeg">
  <img src="https://img.shields.io/badge/Remotion-React%20Video-61DAFB?style=flat-square&logo=react&logoColor=111111" alt="Remotion">
  <img src="https://img.shields.io/badge/Next.js-Website-000000?style=flat-square&logo=next.js&logoColor=white" alt="Next.js">
</p>

<p align="center">
  <a href="https://github.com/KeshavCracks/video-production-buddy#quick-start">⚡ Quick Start</a> &nbsp;·&nbsp;
  <a href="https://github.com/KeshavCracks/video-production-buddy#demos">🎬 Demos</a> &nbsp;·&nbsp;
  <a href="https://github.com/KeshavCracks/video-production-buddy#why-it-is-different">✨ Why Different</a> &nbsp;·&nbsp;
  <a href="HOSTING.md">🚀 Hosting</a> &nbsp;·&nbsp;
  <a href="website/">🌐 Website</a>
</p>

<p align="center">
  <img src="assets/hero-production-assistant.png" alt="Video Production Buddy workflow" width="100%">
</p>

---

> **Video Production Buddy** turns your AI coding assistant into a visible, inspectable video production studio. Instead of typing one prompt and hoping, you review the brief, plan, script, assets, render, and final checks before any major generation spend.
>
> **Agent-first by design:** the AI assistant is the producer and orchestrator. Python tools and YAML skills handle provider routing, media analysis, generation, composition, validation, checkpointing, and cost tracking. Every decision is visible and reproducible.
>
> **Best first try:** run the zero-key demo, confirm your machine can render locally, then open this folder in your AI assistant and start creating. Cloud API keys are optional until you need premium provider-generated images, video, voice, or music.
>
> <p align="center"><strong>⭐ Star this project if you want an open, inspectable alternative to black-box AI video generation.</strong></p>

---

## 🎬 Demos

Watch real videos produced by the pipeline — no post-production tricks, just the output from the agent workflow.

### MacBook Air Ad

> **Prompt:** *"Please help me design an ad video for MacBook Air."*

<div align="center">
  <video src="https://github.com/user-attachments/assets/df481a12-a150-41c6-97fe-24afcbeb85db" width="100%" controls poster="assets/readme/macbook_air.jpg"></video>
</div>

### 织影 Product Ad (Guided Flow)

> A full guided assistant flow: intake → proposal gates → asset generation → composition → final review → delivery.

<div align="center">
  <video src="https://github.com/user-attachments/assets/c240b2d1-5c65-41f1-8d71-454ae1f43f51" width="100%" controls poster="assets/readme/zhiying.jpg"></video>
</div>

---

## ✨ Why It Is Different

| ❌ Typical AI Video Tools | ✅ Video Production Buddy |
|---------------------------|---------------------------|
| One-shot prompt → generation | **Staged pipeline** from brief to verified render |
| You must know exactly what to ask | **Chat + GenUI** discover needs before production |
| Trend and reference work is optional | **Hot topics + viral analysis** add audience context |
| Story quality judged after rendering | **Emotion pacing** reviewed in the cheap text phase |
| Hidden provider and cost choices | **Visible provider routing**, budget checks, and approval gates |
| Segments can drift from each other | **Concept maps** constrain cross-segment consistency |
| Hard to resume or audit | **Checkpointed artifacts** and decision logs |
| Generate first, fix later | **Approve the plan** before expensive generation |
| Output judged by vibe only | **Structured quality checks** after composition |

### Key Principles

- 🎬 **Pipeline-to-Video.** YAML manifests and director skills guide each stage from intake to publish.
- 💬 **Needs are discovered, not guessed.** Chat and GenUI gates uncover audience, taste, emotion, constraints, and ideal video profile.
- 🧠 **Design before asset generation.** Hot-topic search, viral analysis, professional production knowledge retrieval, and emotion-curve checks shape the plan while it is still cheap to revise.
- 🧷 **Consistency before generation.** Concept maps and approved constraints keep products, characters, scenes, and visual logic aligned across segments.
- 🛡️ **Hallucination review.** Review agents catch unsafe, implausible, or story-breaking samples before approval.
- ✅ **Human approval before expensive generation.** Briefs, proposals, scripts, scene plans, samples, and final renders can be reviewed before the next spend.
- 🔀 **Provider-aware execution.** Image, video, voice, music, stock, subtitle, analysis, and composition tools are discovered from the live registry and routed by task fit.
- 🧾 **Checkpointed and reproducible.** JSON artifacts, decision logs, and checkpoints preserve the production trail so work can be reviewed or resumed.
- 🧪 **Verified output.** Scene fidelity, product consistency, provider consistency, render validation, and post-render review keep the final video accountable to the approved brief.

---

## 🧭 How It Works

```text
User request
  -> Chat and GenUI clarify needs, audience, taste, and constraints
  -> AI assistant selects a pipeline manifest
  -> AI assistant reads the stage director skill
  -> Design intelligence gathers trends, references, and production knowledge
  -> Python tools execute concrete media work
  -> JSON artifacts and checkpoints preserve state
  -> Review gates validate creative and technical decisions
  -> Composition runtime renders the final video
  -> Post-render checks verify the output
```

Video Production Buddy has no Python orchestrator. The assistant follows readable contracts in YAML manifests and Markdown skills. The codebase provides tools, schemas, persistence, validation, and render runtimes.

For ads and commercial-style projects, the pipeline adds stronger pre-production: product positioning, professional video production knowledge retrieval, hot-topic search, viral analysis, emotion pacing constraints, concept-map consistency checks, sample approval, scene fidelity checks, product identity validation, hallucination review, and final consistency review.

---

## 🚀 Quick Start

### Before You Start

For a first try, you **do not** need cloud API keys. Render the checked-in zero-key demo first, confirm local rendering works, then add cloud providers only when you need them.

**Requirements:**

- **Git** — [git-scm.com](https://git-scm.com/downloads)
- **Python 3.10+** — [python.org](https://www.python.org/downloads/)
- **FFmpeg** — `brew install ffmpeg` / `sudo apt install ffmpeg` / `winget install --id Gyan.FFmpeg` / `choco install ffmpeg -y`
- **Node.js 22+** — required for Remotion, HyperFrames, and character-animation renders
- **Make** — macOS: `xcode-select --install` | Ubuntu: `sudo apt install make` | Windows: `choco install make -y`
- **An AI coding assistant** — Codex, Claude Code, Cursor, GitHub Copilot, Windsurf, or another assistant that can read files and run shell commands

On Windows, reopen PowerShell after installing Python, Node.js, FFmpeg, or Make so new `PATH` entries are visible.

### One-Command Local Setup

**macOS / Linux:**

```bash
git clone https://github.com/KeshavCracks/video-production-buddy.git
cd video-production-buddy
python3 -m venv .venv
source .venv/bin/activate
make setup
python -m lib.agent_components install --profile default --frozen
make preflight
make demo
```

**Windows PowerShell:**

```powershell
git clone https://github.com/KeshavCracks/video-production-buddy.git
cd video-production-buddy
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
.\.venv\Scripts\Activate.ps1
$env:PYTHON = "python"
make setup
python -m lib.agent_components install --profile default --frozen
make preflight
make demo
```

Success looks like this:
- `make preflight` prints JSON with `composition_runtimes` and provider availability.
- `make demo` renders local demo MP4 files under `projects/demos/renders/`.
- No cloud API key is required for that demo path.

After the demo works, open this repository folder in your AI assistant and start with a prompt.

### 🐳 Docker (Alternative)

```bash
docker-compose build
docker-compose run --rm vpb-studio
# Inside the container:
make preflight
make demo
```

### 💻 GitHub Codespaces (Zero-Install)

Click **Code → Codespaces → Create codespace on main**. The DevContainer will install everything automatically. Then run `make demo`.

### 🔑 Add API Keys (Optional)

All keys are optional. When you need cloud generation, add only the providers you plan to use in `.env` (copy from `.env.example`).

```bash
FAL_KEY=your-key              # Image/video: FLUX, Recraft, Seedance, Kling, Veo, MiniMax video
DASHSCOPE_API_KEY=your-key    # Qwen speech, Wan video, Wanxiang image
ELEVENLABS_API_KEY=your-key   # TTS, music, sound effects
OPENAI_API_KEY=your-key       # OpenAI TTS and image generation
MINIMAX_API_KEY=your-key      # MiniMax music generation
PEXELS_API_KEY=your-key       # Optional: stock media
```

Have an NVIDIA GPU and want local generation?

```bash
make install-gpu
```

Then set in `.env`:
```bash
VIDEO_GEN_LOCAL_ENABLED=true
VIDEO_GEN_LOCAL_MODEL=wan2.1-1.3b
```

Other local models: `wan2.1-14b`, `hunyuan-1.5`, `ltx2-local`, `cogvideo-5b`.

---

## 🧩 Capabilities

| Area | What It Supports |
|------|------------------|
| 🎞️ Generated video | Topic-to-video, explainers, animations, cinematic teasers, product ads, and short-form social videos. |
| 💬 Interactive discovery | Chat and GenUI interfaces clarify the target audience, emotion, constraints, and ideal video profile before generation. |
| 📣 Ad production | Strategy, hot-topic search, viral analysis, professional production knowledge retrieval, product constraints, sample approval, and publish checks. |
| 🎥 Source footage | Talking-head edits, screen demos, podcast repurposing, clip extraction, localization, and hybrid videos. |
| 🧭 Reference-aware planning | Analyze a reference video or user-provided source media before designing the new output. |
| 🎭 Story control | Emotion pacing constraints check suspense, twists, emotional anchors, and story appeal before assets are generated. |
| 🧩 Consistency control | Concept maps and approved design constraints keep product identity, characters, scenes, and visual logic consistent across segments. |
| 🔀 Provider routing | Select among configured image, video, voice, music, stock, subtitle, analysis, and composition tools. |
| 🧱 Composition | FFmpeg post-production, Remotion React video scenes, and HyperFrames HTML/CSS/GSAP motion graphics. |
| ✅ Quality gates | Schema validation, checkpointing, decision logs, provider consistency checks, hallucination review, scene fidelity checks, render validation, and post-render review. |

---

## 🌐 Project Website

We ship a **Next.js showcase website** in the `website/` directory. Deploy it to Vercel in 30 seconds:

1. Import the `website/` folder into [Vercel](https://vercel.com).
2. Vercel auto-detects Next.js and deploys.
3. Customize `NEXT_PUBLIC_GITHUB_REPO` and `NEXT_PUBLIC_DOCS_URL` if needed.

The website includes:
- Hero landing with live stats
- Feature deep-dives
- Interactive pipeline visualization
- Use case cards
- Tech stack grid
- Open-source CTA with GitHub integration

---

## 🏗️ Architecture

| Path | Purpose |
|------|---------|
| `AGENT_GUIDE.md` | Operating contract for production agents. |
| `PROJECT_CONTEXT.md` | Shared architecture and development overview. |
| `docs/PR_REVIEW_GUIDE.md` | Review framework for pull requests. |
| `pipeline_defs/` | Declarative video production pipelines. |
| `skills/` | Stage directors, creative guidance, review protocols. |
| `tools/` | Provider tools, analysis, media processing, composition, validation, cost tracking. |
| `schemas/` | Canonical artifact, checkpoint, pipeline, style, and tool contracts. |
| `project_profile/` | Project-local production conventions. |
| `projects/` | Generated project workspaces; ignored by git. |
| `remotion-composer/` | React/Remotion composition runtime. |
| `website/` | Next.js showcase website for Vercel deployment. |
| `HOSTING.md` | Full hosting, deployment, and Docker guide. |

### Useful Commands

```bash
make preflight          # inspect provider/runtime availability
make demo               # render the zero-key demo suite
make demo-list          # list available demos
make hyperframes-doctor # validate HyperFrames runtime
make test-contracts     # run contract tests
make test-integration   # run opt-in local runtime smoke tests
```

---

## 🤖 Agent Instructions

This repository is meant to be operated by an AI coding assistant. If you are an agent:

1. Read [`AGENT_GUIDE.md`](AGENT_GUIDE.md) for production work.
2. Read [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for development work.
3. Discover the live capability envelope before promising a production path:
   ```bash
   python -c "from tools.tool_registry import registry; import json; registry.discover(); print(json.dumps(registry.provider_menu_summary(), indent=2))"
   ```
4. For actual video production, follow the selected pipeline manifest in `pipeline_defs/` and the stage director skills in `skills/pipelines/`.
5. Do not spend on generation tools until the proposal and required approval gates are clear.

---

## 🧪 Testing

```bash
# Test dependencies
make install-dev

# Fast default suite
make test

# Contract tests only
make test-contracts

# Opt-in local runtime checks (FFmpeg/browser/Node/HyperFrames)
make test-integration

# Manual/media QA alias
make test-qa
```

The default suite excludes `integration`, `qa`, `browser`, `ffmpeg`, `node`, `hyperframes`, `slow`, and `live_provider` markers.

---

## 📜 License

[GNU AGPLv3](LICENSE)

Video Production Buddy is built on the open-source [OpenMontage](https://github.com/calesthio/OpenMontage) project. When citing or building on this repository, please also acknowledge OpenMontage.

---

## 🙏 Acknowledgements

Video Production Buddy is developed by the [AI4GC Lab](https://ai4gc.org/) at Zhejiang University. This fork (`KeshavCracks/video-production-buddy`) is a community-enhanced distribution with added hosting tooling, Docker support, DevContainer configuration, and a Vercel-ready showcase website.

The codebase builds on the excellent [OpenMontage](https://github.com/calesthio/OpenMontage) project; we are grateful for its open-source architecture and implementation foundation.

---

<p align="center">
  <strong>Made with ❤️ by the open-source community.</strong>
  <br>
  <a href="https://github.com/KeshavCracks/video-production-buddy">GitHub</a> ·
  <a href="HOSTING.md">Hosting</a> ·
  <a href="website/">Website</a> ·
  <a href="LICENSE">License</a>
</p>
