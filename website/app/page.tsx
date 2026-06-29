'use client';

import { useState, useEffect } from 'react';
import {
  Play,
  Github,
  Sparkles,
  Layers,
  Shield,
  Zap,
  Monitor,
  ChevronRight,
  Star,
  GitFork,
  Cpu,
  Film,
  Music,
  Image,
  Type,
  Box,
  ArrowRight,
  CheckCircle2,
  Code2,
  Terminal,
  Globe,
  Rocket,
  Wand2,
} from 'lucide-react';

const features = [
  {
    icon: <Sparkles className="w-6 h-6 text-brand-400" />,
    title: 'Agent-First Orchestration',
    desc: 'Your AI assistant is the producer. No hidden orchestrator. Every decision is visible, checkpointed, and reproducible.',
  },
  {
    icon: <Layers className="w-6 h-6 text-purple-400" />,
    title: 'Pipeline-to-Video',
    desc: 'Not prompt-to-video. YAML manifests guide intake, planning, asset generation, composition, and final review.',
  },
  {
    icon: <Shield className="w-6 h-6 text-emerald-400" />,
    title: 'Approve Before You Spend',
    desc: 'Human approval gates before expensive generation. Review the brief, script, and samples before cloud APIs are called.',
  },
  {
    icon: <Zap className="w-6 h-6 text-yellow-400" />,
    title: 'Zero-Key Demo',
    desc: 'Run the entire demo suite locally without a single API key. Remotion + FFmpeg + local TTS = free forever.',
  },
  {
    icon: <Monitor className="w-6 h-6 text-pink-400" />,
    title: 'GenUI Review Gates',
    desc: 'Interactive browser surfaces for media review, side-by-side comparison, and structured revision capture.',
  },
  {
    icon: <Cpu className="w-6 h-6 text-cyan-400" />,
    title: 'Dual Provider Support',
    desc: 'Every capability supports both cloud APIs (paid) and local open-source alternatives (free, GPU).',
  },
];

const useCases = [
  {
    title: 'Product Ads',
    desc: 'Generate polished product ads with positioning, viral analysis, emotion pacing, and brand consistency.',
    tags: ['Ad-Video Pipeline', 'FLUX', 'ElevenLabs', 'Suno'],
  },
  {
    title: 'Explainer Videos',
    desc: 'Turn complex topics into animated explainers with Remotion composition, voiceover, and auto-generated subtitles.',
    tags: ['Remotion', 'Piper TTS', 'WhisperX'],
  },
  {
    title: 'Social Media Clips',
    desc: 'Chop, style, and caption content for TikTok, YouTube Shorts, and Instagram Reels with platform-specific profiles.',
    tags: ['FFmpeg', 'HyperFrames', 'B-roll'],
  },
  {
    title: 'AI Dubbing & Localization',
    desc: 'Transcribe, translate, and re-voice videos into multiple languages with speaker diarization.',
    tags: ['WhisperX', 'Piper', 'Google TTS'],
  },
];

const techStack = [
  { name: 'Remotion', icon: <Film className="w-5 h-5" />, category: 'Composition' },
  { name: 'FFmpeg', icon: <Box className="w-5 h-5" />, category: 'Media Engine' },
  { name: 'Python 3.10+', icon: <Code2 className="w-5 h-5" />, category: 'Runtime' },
  { name: 'React 18', icon: <Globe className="w-5 h-5" />, category: 'UI' },
  { name: 'Node.js 22', icon: <Terminal className="w-5 h-5" />, category: 'Runtime' },
  { name: 'FLUX', icon: <Image className="w-5 h-5" />, category: 'Image Gen' },
  { name: 'WAN 2.1', icon: <Wand2 className="w-5 h-5" />, category: 'Video Gen' },
  { name: 'Piper TTS', icon: <Type className="w-5 h-5" />, category: 'Voice' },
  { name: 'Suno', icon: <Music className="w-5 h-5" />, category: 'Music' },
  { name: 'ElevenLabs', icon: <Zap className="w-5 h-5" />, category: 'Voice' },
];

const pipelineSteps = [
  { step: '01', title: 'Intake & Discovery', desc: 'Chat + GenUI uncover audience, taste, and constraints.' },
  { step: '02', title: 'Trend Intelligence', desc: 'Hot-topic search, viral analysis, and production knowledge.' },
  { step: '03', title: 'Creative Plan', desc: 'Script, emotion curve, storyboard, and concept map.' },
  { step: '04', title: 'Human Approval', desc: 'Review gates before expensive generation starts.' },
  { step: '05', title: 'Asset Generation', desc: 'Images, video, voice, music via best-fit provider.' },
  { step: '06', title: 'Composition & Render', desc: 'Remotion / HyperFrames stitch everything into MP4.' },
  { step: '07', title: 'Verification', desc: 'Scene fidelity, consistency, and quality checks.' },
];

export default function Home() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <main className="relative overflow-x-hidden">
      {/* Navigation */}
      <nav
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          scrolled ? 'bg-dark-900/80 backdrop-blur-xl border-b border-white/5' : 'bg-transparent'
        }`}
      >
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-400 to-purple-600 flex items-center justify-center">
              <Film className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-lg tracking-tight">Video Production Buddy</span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm text-gray-400">
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <a href="#pipeline" className="hover:text-white transition-colors">Pipeline</a>
            <a href="#use-cases" className="hover:text-white transition-colors">Use Cases</a>
            <a href="#tech-stack" className="hover:text-white transition-colors">Tech Stack</a>
          </div>
          <div className="flex items-center gap-3">
            <a
              href="https://github.com/KeshavCracks/video-production-buddy"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 transition-all text-sm font-medium"
            >
              <Github className="w-4 h-4" />
              <span className="hidden sm:inline">Star on GitHub</span>
            </a>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center justify-center pt-20 pb-32 overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-brand-900/40 via-dark-900 to-dark-900" />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-brand-500/10 blur-[120px] rounded-full" />
        <div className="absolute bottom-0 right-0 w-[600px] h-[600px] bg-purple-500/10 blur-[120px] rounded-full" />

        <div className="relative z-10 max-w-7xl mx-auto px-6 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 text-sm text-brand-300 mb-8 animate-float">
            <Sparkles className="w-4 h-4" />
            <span>Open-source & Agent-First</span>
          </div>

          <h1 className="text-5xl sm:text-7xl lg:text-8xl font-extrabold tracking-tight mb-6 leading-[1.1]">
            <span className="gradient-text">AI Video Production</span>
            <br />
            <span className="text-white">Built for Humans</span>
          </h1>

          <p className="text-lg sm:text-xl text-gray-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            Plan, approve, generate, compose, and verify videos with a visible, open-source pipeline.
            No black boxes. No surprise bills. Just production-grade video from an AI assistant you control.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <a
              href="https://github.com/KeshavCracks/video-production-buddy#quick-start"
              target="_blank"
              rel="noopener noreferrer"
              className="group flex items-center gap-2 px-8 py-4 rounded-xl bg-gradient-to-r from-brand-500 to-purple-600 hover:from-brand-400 hover:to-purple-500 text-white font-semibold transition-all shadow-lg shadow-brand-500/20 hover:shadow-brand-500/40"
            >
              <Rocket className="w-5 h-5" />
              Get Started Free
              <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </a>
            <a
              href="https://github.com/KeshavCracks/video-production-buddy"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-8 py-4 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white font-semibold transition-all"
            >
              <Github className="w-5 h-5" />
              View on GitHub
            </a>
          </div>

          {/* Stats */}
          <div className="mt-16 grid grid-cols-2 sm:grid-cols-4 gap-6 max-w-3xl mx-auto">
            {[
              { label: 'Stars', value: '150+', icon: <Star className="w-4 h-4 text-yellow-400" /> },
              { label: 'Pipelines', value: '11', icon: <Layers className="w-4 h-4 text-brand-400" /> },
              { label: 'Tools', value: '47', icon: <Wand2 className="w-4 h-4 text-purple-400" /> },
              { label: 'Skills', value: '124', icon: <Sparkles className="w-4 h-4 text-emerald-400" /> },
            ].map((stat) => (
              <div key={stat.label} className="glass-card p-4 flex flex-col items-center gap-2">
                <div className="flex items-center gap-2">
                  {stat.icon}
                  <span className="text-2xl font-bold text-white">{stat.value}</span>
                </div>
                <span className="text-xs text-gray-400 uppercase tracking-wider">{stat.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section id="features" className="py-24 relative">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-5xl font-bold mb-4">
              Why It Is <span className="gradient-text">Different</span>
            </h2>
            <p className="text-gray-400 max-w-2xl mx-auto">
              Most AI video tools are black boxes. Type a prompt, pray, and pay. We built the opposite.
            </p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((f) => (
              <div key={f.title} className="glass-card p-6 hover:bg-white/10 transition-all group glow">
                <div className="mb-4 p-3 rounded-xl bg-white/5 w-fit group-hover:scale-110 transition-transform">
                  {f.icon}
                </div>
                <h3 className="text-lg font-semibold mb-2">{f.title}</h3>
                <p className="text-sm text-gray-400 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pipeline Visualization */}
      <section id="pipeline" className="py-24 relative bg-dark-800/50">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-5xl font-bold mb-4">
              The <span className="gradient-text">Pipeline</span>
            </h2>
            <p className="text-gray-400 max-w-2xl mx-auto">
              A governed, stage-by-stage workflow from idea to verified MP4. No hidden steps.
            </p>
          </div>
          <div className="relative">
            <div className="absolute left-6 sm:left-8 top-0 bottom-0 w-px bg-gradient-to-b from-brand-500/50 via-purple-500/50 to-transparent" />
            <div className="space-y-8">
              {pipelineSteps.map((s, i) => (
                <div key={s.step} className="relative pl-16 sm:pl-20">
                  <div className="absolute left-0 sm:left-2 top-0 w-12 h-12 sm:w-14 sm:h-14 rounded-full bg-dark-800 border border-white/10 flex items-center justify-center text-sm font-bold text-brand-400 shadow-lg shadow-brand-500/10">
                    {s.step}
                  </div>
                  <div className="glass-card p-6 hover:bg-white/10 transition-all">
                    <h3 className="text-xl font-semibold mb-2">{s.title}</h3>
                    <p className="text-gray-400">{s.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Use Cases */}
      <section id="use-cases" className="py-24 relative">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-5xl font-bold mb-4">
              Built for <span className="gradient-text">Every Story</span>
            </h2>
            <p className="text-gray-400 max-w-2xl mx-auto">
              From viral ads to educational explainers, run the right pipeline for your project.
            </p>
          </div>
          <div className="grid sm:grid-cols-2 gap-6">
            {useCases.map((uc) => (
              <div key={uc.title} className="glass-card p-8 hover:bg-white/10 transition-all group">
                <h3 className="text-xl font-semibold mb-3 group-hover:text-brand-400 transition-colors">{uc.title}</h3>
                <p className="text-gray-400 mb-6 leading-relaxed">{uc.desc}</p>
                <div className="flex flex-wrap gap-2">
                  {uc.tags.map((tag) => (
                    <span key={tag} className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs text-gray-300">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Tech Stack */}
      <section id="tech-stack" className="py-24 relative bg-dark-800/50">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-5xl font-bold mb-4">
              Powered by <span className="gradient-text">Best-in-Class</span> Tech
            </h2>
            <p className="text-gray-400 max-w-2xl mx-auto">
              Remotion, FFmpeg, Python, React, and a curated registry of 47+ generation providers.
            </p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            {techStack.map((t) => (
              <div key={t.name} className="glass-card p-4 flex flex-col items-center gap-3 text-center hover:bg-white/10 transition-all">
                <div className="p-3 rounded-xl bg-white/5">{t.icon}</div>
                <div>
                  <div className="font-semibold text-sm">{t.name}</div>
                  <div className="text-xs text-gray-500">{t.category}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Open Source CTA */}
      <section className="py-24 relative">
        <div className="max-w-4xl mx-auto px-6">
          <div className="glass-card p-8 sm:p-12 text-center relative overflow-hidden glow">
            <div className="absolute inset-0 bg-gradient-to-r from-brand-500/10 to-purple-500/10" />
            <div className="relative z-10">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 text-sm text-brand-300 mb-6">
                <GitFork className="w-4 h-4" />
                <span>AGPLv3 — Free Forever</span>
              </div>
              <h2 className="text-3xl sm:text-5xl font-bold mb-4">
                Own Your <span className="gradient-text">Video Pipeline</span>
              </h2>
              <p className="text-gray-400 max-w-xl mx-auto mb-8 leading-relaxed">
                No subscriptions, no black boxes, no vendor lock-in. Clone the repo, run the demo in 5 minutes, and start producing.
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <a
                  href="https://github.com/KeshavCracks/video-production-buddy"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group flex items-center gap-2 px-8 py-4 rounded-xl bg-white text-dark-900 font-bold hover:bg-gray-100 transition-all"
                >
                  <Github className="w-5 h-5" />
                  Fork on GitHub
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </a>
                <a
                  href="https://github.com/KeshavCracks/video-production-buddy/blob/main/HOSTING.md"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 px-8 py-4 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white font-semibold transition-all"
                >
                  <Rocket className="w-5 h-5" />
                  Hosting Guide
                </a>
              </div>
              <div className="mt-8 flex flex-wrap items-center justify-center gap-4 text-sm text-gray-400">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>Zero-Key Demo</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>AGPLv3 Licensed</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>Community Driven</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 py-12 bg-dark-900">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-gradient-to-br from-brand-400 to-purple-600 flex items-center justify-center">
              <Film className="w-3 h-3 text-white" />
            </div>
            <span className="font-semibold text-sm">Video Production Buddy</span>
          </div>
          <div className="flex items-center gap-6 text-sm text-gray-400">
            <a href="https://github.com/KeshavCracks/video-production-buddy" target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors">GitHub</a>
            <a href="https://github.com/KeshavCracks/video-production-buddy/blob/main/HOSTING.md" target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors">Docs</a>
            <a href="https://github.com/KeshavCracks/video-production-buddy/blob/main/LICENSE" target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors">License</a>
          </div>
          <div className="text-xs text-gray-500">
            Built on OpenMontage. Maintained by the community.
          </div>
        </div>
      </footer>
    </main>
  );
}
