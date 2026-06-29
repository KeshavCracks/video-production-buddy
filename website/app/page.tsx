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
  Workflow,
  Lock,
  CreditCard,
  HardDrive,
  Waves,
  Gauge,
} from 'lucide-react';

const features = [
  {
    icon: <Sparkles className="w-6 h-6 text-sky-400" />,
    title: 'Agent-First Orchestration',
    desc: 'Your AI assistant acts as the producer. No hidden orchestrator. Every stage is visible, checkpointed, and reproducible.',
  },
  {
    icon: <Layers className="w-6 h-6 text-violet-400" />,
    title: 'Pipeline-to-Video',
    desc: 'Not prompt-to-video. Structured YAML manifests guide intake, discovery, creative, generation, and review before render.',
  },
  {
    icon: <Shield className="w-6 h-6 text-emerald-400" />,
    title: 'Approve Before You Spend',
    desc: 'Human approval gates before every expensive API call. Review the brief, script, and samples before cloud generation.',
  },
  {
    icon: <Zap className="w-6 h-6 text-amber-400" />,
    title: 'Zero-Key Demo',
    desc: 'Run the entire demo suite locally without a single API key. Remotion + FFmpeg + local TTS = free forever.',
  },
  {
    icon: <Monitor className="w-6 h-6 text-rose-400" />,
    title: 'Interactive Review Gates',
    desc: 'Browser-based review surfaces for side-by-side comparison, structured revision capture, and media sign-off.',
  },
  {
    icon: <Cpu className="w-6 h-6 text-cyan-400" />,
    title: 'Dual Provider Routing',
    desc: 'Every capability supports both cloud APIs (premium) and local open-source alternatives (free, GPU).',
  },
];

const useCases = [
  {
    title: 'Product Launch Ads',
    desc: 'Generate polished commercials with positioning research, viral analysis, emotion pacing, and brand consistency across every scene.',
    tags: ['Ad Pipeline', 'FLUX', 'ElevenLabs', 'Suno'],
  },
  {
    title: 'Animated Explainers',
    desc: 'Turn complex topics into engaging motion videos with React-based composition, synthesized narration, and auto-generated subtitles.',
    tags: ['Remotion', 'Piper TTS', 'WhisperX'],
  },
  {
    title: 'Social Media Shorts',
    desc: 'Rapidly chop, style, and caption content for TikTok, Reels, and Shorts with platform-specific aspect ratios and pacing.',
    tags: ['FFmpeg', 'HyperFrames', 'B-roll'],
  },
  {
    title: 'AI Dubbing & Localization',
    desc: 'Transcribe, translate, and re-voice videos into multiple languages with speaker diarization and lip-sync timing.',
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
  { name: 'ElevenLabs', icon: <Waves className="w-5 h-5" />, category: 'Voice' },
];

const pipelineSteps = [
  { step: '01', title: 'Discovery', desc: 'Chat and interactive UI clarify audience, taste, and constraints.' },
  { step: '02', title: 'Research', desc: 'Hot-topic search, viral analysis, and production knowledge retrieval.' },
  { step: '03', title: 'Creative Plan', desc: 'Script, emotion curve, storyboard, and concept mapping.' },
  { step: '04', title: 'Human Approval', desc: 'Review gates before any expensive generation starts.' },
  { step: '05', title: 'Asset Generation', desc: 'Images, video, voice, and music via best-fit provider.' },
  { step: '06', title: 'Composition & Render', desc: 'Remotion / HyperFrames / FFmpeg stitch into final MP4.' },
  { step: '07', title: 'Verification', desc: 'Scene fidelity, consistency, and quality audit before delivery.' },
];

const pricingCompare = [
  { feature: 'Local rendering', closed: 'Limited', open: 'Unlimited', icon: <HardDrive className="w-4 h-4" /> },
  { feature: 'Pipeline transparency', closed: 'Opaque', open: 'Full YAML manifests', icon: <Workflow className="w-4 h-4" /> },
  { feature: 'Cost control', closed: 'Surprise bills', open: 'Approval gates', icon: <CreditCard className="w-4 h-4" /> },
  { feature: 'Revision history', closed: 'None', open: 'JSON checkpoints', icon: <Lock className="w-4 h-4" /> },
  { feature: 'Provider choice', closed: 'Locked in', open: '47+ tools, auto-routed', icon: <Gauge className="w-4 h-4" /> },
];

export default function Home() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <main className="relative overflow-x-hidden bg-[#0a0a0f]">
      {/* Navigation */}
      <nav
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          scrolled ? 'bg-[#0a0a0f]/90 backdrop-blur-xl border-b border-white/5' : 'bg-transparent'
        }`}
      >
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-sky-400 to-violet-600 flex items-center justify-center">
              <Film className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-lg tracking-tight text-white">AI Video Forge</span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm text-gray-400">
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <a href="#pipeline" className="hover:text-white transition-colors">Pipeline</a>
            <a href="#use-cases" className="hover:text-white transition-colors">Use Cases</a>
            <a href="#tech-stack" className="hover:text-white transition-colors">Stack</a>
          </div>
          <div className="flex items-center gap-3">
            <a
              href="https://github.com/KeshavCracks/video-production-buddy"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 transition-all text-sm font-medium text-white"
            >
              <Github className="w-4 h-4" />
              <span className="hidden sm:inline">Star</span>
            </a>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center justify-center pt-20 pb-32 overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-sky-900/20 via-[#0a0a0f] to-[#0a0a0f]" />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-sky-500/10 blur-[120px] rounded-full" />
        <div className="absolute bottom-0 right-0 w-[600px] h-[600px] bg-violet-500/10 blur-[120px] rounded-full" />

        <div className="relative z-10 max-w-7xl mx-auto px-6 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 text-sm text-sky-300 mb-8">
            <Sparkles className="w-4 h-4" />
            <span>Open-Source & AGPLv3 Licensed</span>
          </div>

          <h1 className="text-5xl sm:text-7xl lg:text-8xl font-extrabold tracking-tight mb-6 leading-[1.1]">
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-sky-400 via-violet-400 to-rose-400">
              Own Your Pipeline
            </span>
            <br />
            <span className="text-white">From Script to MP4</span>
          </h1>

          <p className="text-lg sm:text-xl text-gray-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            The open-source AI video studio where your assistant is the producer.
            No black boxes. No surprise bills. Just production-grade output you control.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <a
              href="https://github.com/KeshavCracks/video-production-buddy#quick-start"
              target="_blank"
              rel="noopener noreferrer"
              className="group flex items-center gap-2 px-8 py-4 rounded-xl bg-gradient-to-r from-sky-500 to-violet-600 hover:from-sky-400 hover:to-violet-500 text-white font-semibold transition-all shadow-lg shadow-sky-500/20 hover:shadow-sky-500/40"
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

          <div className="mt-16 grid grid-cols-2 sm:grid-cols-4 gap-6 max-w-3xl mx-auto">
            {[
              { label: 'Stars', value: '150+', icon: <Star className="w-4 h-4 text-amber-400" /> },
              { label: 'Pipelines', value: '11', icon: <Layers className="w-4 h-4 text-sky-400" /> },
              { label: 'Tools', value: '47', icon: <Wand2 className="w-4 h-4 text-violet-400" /> },
              { label: 'Skills', value: '124', icon: <Sparkles className="w-4 h-4 text-emerald-400" /> },
            ].map((stat) => (
              <div key={stat.label} className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-4 flex flex-col items-center gap-2">
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

      {/* Comparison Section */}
      <section className="py-20 relative">
        <div className="max-w-5xl mx-auto px-6">
          <div className="text-center mb-12">
            <h2 className="text-3xl sm:text-5xl font-bold mb-4 text-white">
              Why Open-Source <span className="bg-clip-text text-transparent bg-gradient-to-r from-sky-400 to-violet-400">Wins</span>
            </h2>
          </div>
          <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden">
            <div className="grid grid-cols-3 gap-4 p-6 border-b border-white/10 text-sm font-semibold text-gray-400">
              <div>Feature</div>
              <div className="text-center">Closed Platforms</div>
              <div className="text-center text-sky-400">AI Video Forge</div>
            </div>
            {pricingCompare.map((item) => (
              <div key={item.feature} className="grid grid-cols-3 gap-4 p-6 border-b border-white/5 hover:bg-white/5 transition-colors items-center">
                <div className="flex items-center gap-2 text-white text-sm">
                  {item.icon}
                  {item.feature}
                </div>
                <div className="text-center text-gray-500 text-sm">{item.closed}</div>
                <div className="text-center text-emerald-400 text-sm font-medium">{item.open}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section id="features" className="py-24 relative">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-5xl font-bold mb-4 text-white">
              Built for <span className="bg-clip-text text-transparent bg-gradient-to-r from-sky-400 to-violet-400">Control</span>
            </h2>
            <p className="text-gray-400 max-w-2xl mx-auto">
              Most AI video tools are black boxes. Type a prompt, pray, and pay. We built the opposite.
            </p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((f) => (
              <div key={f.title} className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6 hover:bg-white/10 transition-all hover:shadow-lg hover:shadow-sky-500/10">
                <div className="mb-4 p-3 rounded-xl bg-white/5 w-fit">
                  {f.icon}
                </div>
                <h3 className="text-lg font-semibold mb-2 text-white">{f.title}</h3>
                <p className="text-sm text-gray-400 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pipeline Visualization */}
      <section id="pipeline" className="py-24 relative bg-[#12121a]/50">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-5xl font-bold mb-4 text-white">
              The <span className="bg-clip-text text-transparent bg-gradient-to-r from-sky-400 to-violet-400">Seven-Stage</span> Pipeline
            </h2>
            <p className="text-gray-400 max-w-2xl mx-auto">
              A governed, stage-by-stage workflow from idea to verified MP4. No hidden steps.
            </p>
          </div>
          <div className="relative">
            <div className="absolute left-6 sm:left-8 top-0 bottom-0 w-px bg-gradient-to-b from-sky-500/50 via-violet-500/50 to-transparent" />
            <div className="space-y-8">
              {pipelineSteps.map((s) => (
                <div key={s.step} className="relative pl-16 sm:pl-20">
                  <div className="absolute left-0 sm:left-2 top-0 w-12 h-12 sm:w-14 sm:h-14 rounded-full bg-[#12121a] border border-white/10 flex items-center justify-center text-sm font-bold text-sky-400 shadow-lg shadow-sky-500/10">
                    {s.step}
                  </div>
                  <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6 hover:bg-white/10 transition-all">
                    <h3 className="text-xl font-semibold mb-2 text-white">{s.title}</h3>
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
            <h2 className="text-3xl sm:text-5xl font-bold mb-4 text-white">
              Built for <span className="bg-clip-text text-transparent bg-gradient-to-r from-sky-400 to-violet-400">Every Story</span>
            </h2>
            <p className="text-gray-400 max-w-2xl mx-auto">
              From viral ads to educational explainers, run the right pipeline for your project.
            </p>
          </div>
          <div className="grid sm:grid-cols-2 gap-6">
            {useCases.map((uc) => (
              <div key={uc.title} className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-8 hover:bg-white/10 transition-all">
                <h3 className="text-xl font-semibold mb-3 text-white hover:text-sky-400 transition-colors">{uc.title}</h3>
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
      <section id="tech-stack" className="py-24 relative bg-[#12121a]/50">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-5xl font-bold mb-4 text-white">
              Powered by <span className="bg-clip-text text-transparent bg-gradient-to-r from-sky-400 to-violet-400">Best-in-Class</span> Tech
            </h2>
            <p className="text-gray-400 max-w-2xl mx-auto">
              Remotion, FFmpeg, Python, React, and a curated registry of 47+ generation providers.
            </p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            {techStack.map((t) => (
              <div key={t.name} className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-4 flex flex-col items-center gap-3 text-center hover:bg-white/10 transition-all">
                <div className="p-3 rounded-xl bg-white/5 text-gray-300">{t.icon}</div>
                <div>
                  <div className="font-semibold text-sm text-white">{t.name}</div>
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
          <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-8 sm:p-12 text-center relative overflow-hidden hover:shadow-lg hover:shadow-sky-500/10 transition-all">
            <div className="absolute inset-0 bg-gradient-to-r from-sky-500/10 to-violet-500/10" />
            <div className="relative z-10">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 text-sm text-sky-300 mb-6">
                <GitFork className="w-4 h-4" />
                <span>AGPLv3 — Free Forever</span>
              </div>
              <h2 className="text-3xl sm:text-5xl font-bold mb-4 text-white">
                Own Your <span className="bg-clip-text text-transparent bg-gradient-to-r from-sky-400 to-violet-400">Video Pipeline</span>
              </h2>
              <p className="text-gray-400 max-w-xl mx-auto mb-8 leading-relaxed">
                No subscriptions, no black boxes, no vendor lock-in. Clone the repo, run the demo in 5 minutes, and start producing.
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <a
                  href="https://github.com/KeshavCracks/video-production-buddy"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group flex items-center gap-2 px-8 py-4 rounded-xl bg-white text-[#0a0a0f] font-bold hover:bg-gray-100 transition-all"
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
      <footer className="border-t border-white/5 py-12 bg-[#0a0a0f]">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-gradient-to-br from-sky-400 to-violet-600 flex items-center justify-center">
              <Film className="w-3 h-3 text-white" />
            </div>
            <span className="font-semibold text-sm text-white">AI Video Forge</span>
          </div>
          <div className="flex items-center gap-6 text-sm text-gray-400">
            <a href="https://github.com/KeshavCracks/video-production-buddy" target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors">GitHub</a>
            <a href="https://github.com/KeshavCracks/video-production-buddy/blob/main/HOSTING.md" target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors">Docs</a>
            <a href="https://github.com/KeshavCracks/video-production-buddy/blob/main/LICENSE" target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors">License</a>
          </div>
          <div className="text-xs text-gray-500">
            Open-source community distribution. AGPLv3.
          </div>
        </div>
      </footer>
    </main>
  );
}
