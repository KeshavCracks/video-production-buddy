# Hosting & Deployment Guide

This document covers how to run, host, and deploy Video Production Buddy across different environments.

> **Video Production Buddy is an agent-first desktop toolkit**, not a traditional SaaS. The primary way to use it is locally with an AI coding assistant. However, we provide several options for teams and onboarding.

---

## Quick Local Run (Recommended)

### Prerequisites
- Git
- Python 3.10+
- Node.js 22+
- FFmpeg
- Make

### One-Command Setup
```bash
git clone https://github.com/KeshavCracks/video-production-buddy.git
cd video-production-buddy
python3 -m venv .venv
source .venv/bin/activate
make setup
make demo
```

---

## GitHub Codespaces (Zero-Install)

The easiest way to try Video Production Buddy without installing anything on your machine.

1. Click **"Code" > "Codespaces" > "Create codespace on main"** on the GitHub repo page.
2. The DevContainer will automatically install Python, Node.js, FFmpeg, and all dependencies.
3. Run `make demo` inside the terminal.
4. No API keys required for the zero-key demo.

**Cost:** Free tier includes 120 core-hours/month.

---

## Docker (Self-Hosted)

Build and run the entire stack locally with Docker.

```bash
# Build the studio image
docker-compose build

# Run the interactive studio container
docker-compose run --rm vpb-studio

# Inside the container
make preflight
make demo
```

The `docker-compose.yml` also includes a `vpb-website` service for local development of the showcase site.

---

## Vercel (Showcase Website Only)

The **showcase website** in the `website/` directory is optimized for Vercel deployment.

### Deploy in 30 seconds
1. Fork or clone this repository.
2. Import the `website/` directory into [Vercel](https://vercel.com).
3. Vercel will auto-detect Next.js and deploy.
4. Optional: configure a custom domain.

### Vercel Environment Variables
| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_GITHUB_REPO` | URL to this GitHub repo (for CTA buttons) |
| `NEXT_PUBLIC_DOCS_URL` | URL to docs or README |

---

## VPS / Cloud Server (Production Studio)

If you need a persistent cloud instance for heavier rendering or team collaboration:

### Recommended Specs
| Tier | Use Case | CPU | RAM | GPU | Storage |
|------|----------|-----|-----|-----|---------|
| **Lite** | Demo + Remotion rendering | 4 vCPU | 8 GB | - | 50 GB |
| **Pro** | Local AI video generation | 8 vCPU | 32 GB | NVIDIA A10G / RTX 4090 | 100 GB |
| **Team** | Concurrent pipelines + review | 16 vCPU | 64 GB | NVIDIA A100 / H100 | 200 GB |

### Providers with Free Tiers
- **Google Colab**: Great for GPU experiments (not persistent)
- **Kaggle**: Free GPU notebooks for testing
- **RunPod / Vast.ai**: Cheap GPU rentals by the hour
- **AWS / GCP / Azure**: Reliable persistent instances (paid)

> **Note:** The zero-key demo works on CPU-only machines. GPU is only needed for local diffusion models (WAN 2.1, Hunyuan, CogVideo).

---

## License Considerations (AGPLv3)

Video Production Buddy is licensed under **GNU AGPLv3**.

- If you **host a modified version** as a public service, you must share your source code.
- If you **use it internally**, no source-sharing is required.
- Always preserve the original license and attribution when distributing.

---

## Community Hosting

We do not currently offer an official managed cloud. The open-source community is welcome to:
- Publish Docker images to Docker Hub.
- Create one-click deploy buttons for DigitalOcean, Railway, or Render.
- Share hosting templates and Terraform configs.

Open a PR to add your hosting recipe to this document!
