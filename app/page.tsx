'use client';

import { useState, useEffect } from 'react';
import {
  Github, ArrowRight, Layers, Shield, Zap, Monitor, Star, GitFork,
  Cpu, Film, Music, Image, Type, Box, CheckCircle2, Code2, Terminal,
  Globe, Rocket, Wand2, Workflow, Lock, CreditCard, HardDrive, Gauge,
  ChevronRight, Play, Copy, Check, Sparkles, Radio, Eye, FileCheck,
  Palette, Volume2, Clapperboard, ScanLine, BarChart3, Timer,
} from 'lucide-react';

const features = [
  { icon: <Sparkles className="w-5 h-5" />, label: 'ORCHESTRATION', title: 'Agent-First Producer', desc: 'Your AI assistant reads YAML manifests, discovers tools, and orchestrates every stage. No hidden control plane.' },
  { icon: <Layers className="w-5 h-5" />, label: 'PIPELINE', title: 'Staged Production', desc: 'Seven-stage workflow from intake to verified render. YAML manifests define every checkpoint and approval gate.' },
  { icon: <Shield className="w-5 h-5" />, label: 'GOVERNANCE', title: 'Approve Before Spend', desc: 'Human approval gates before every expensive API call. Review the brief, script, and samples before cloud generation.' },
  { icon: <Zap className="w-5 h-5" />, label: 'ZERO-KEY', title: 'Free Local Demo', desc: 'Run the entire demo suite locally with zero API keys. Remotion + FFmpeg + Piper TTS = completely free.' },
  { icon: <Monitor className="w-5 h-5" />, label: 'INTERFACE', title: 'Interactive Review Gates', desc: 'Browser-based review surfaces for side-by-side comparison, structured revision capture, and media sign-off.' },
  { icon: <Cpu className="w-5 h-5" />, label: 'ROUTING', title: 'Dual Provider Switch', desc: 'Every capability supports both cloud APIs (premium) and local open-source alternatives (free, GPU-accelerated).' },
];

const useCases = [
  { title: 'Product Launch Ads', desc: 'Generate polished commercials with positioning research, viral analysis, and brand consistency across every scene.', tags: ['AD-PIPELINE', 'FLUX', 'ELEVENLABS', 'SUNO'], corner: 'COMMERCIAL' },
  { title: 'Animated Explainers', desc: 'Turn complex topics into engaging motion videos with React composition, synthesized narration, and auto-generated subtitles.', tags: ['EXPLAINER', 'REMOTION', 'PIPER', 'WHISPERX'], corner: 'EDUCATION' },
  { title: 'Social Media Shorts', desc: 'Rapidly chop, style, and caption content for TikTok, Reels, and Shorts with platform-specific aspect ratios and pacing.', tags: ['SOCIAL', 'FFMPEG', 'HYPERFRAMES', 'B-ROLL'], corner: 'SHORT-FORM' },
  { title: 'AI Dubbing & Localization', desc: 'Transcribe, translate, and re-voice videos into multiple languages with speaker diarization and lip-sync timing.', tags: ['DUBBING', 'WHISPERX', 'PIPER', 'GOOGLE-TTS'], corner: 'GLOBAL' },
];

const techStack = [
  { name: 'Remotion', icon: <Clapperboard className="w-4 h-4" />, category: 'COMPOSITION' },
  { name: 'FFmpeg', icon: <Box className="w-4 h-4" />, category: 'MEDIA ENGINE' },
  { name: 'Python 3.10+', icon: <Code2 className="w-4 h-4" />, category: 'RUNTIME' },
  { name: 'React 18', icon: <Globe className="w-4 h-4" />, category: 'UI' },
  { name: 'Node.js 22', icon: <Terminal className="w-4 h-4" />, category: 'RUNTIME' },
  { name: 'FLUX', icon: <Image className="w-4 h-4" />, category: 'IMAGE GEN' },
  { name: 'WAN 2.1', icon: <Wand2 className="w-4 h-4" />, category: 'VIDEO GEN' },
  { name: 'Piper TTS', icon: <Type className="w-4 h-4" />, category: 'VOICE' },
  { name: 'Suno', icon: <Music className="w-4 h-4" />, category: 'MUSIC' },
  { name: 'ElevenLabs', icon: <Volume2 className="w-4 h-4" />, category: 'VOICE' },
];

const pipelineSteps = [
  { step: '01', title: 'Discovery', desc: 'Chat and interactive UI clarify audience, taste, and constraints.' },
  { step: '02', title: 'Research', desc: 'Hot-topic search, viral analysis, and production knowledge retrieval.' },
  { step: '03', title: 'Creative Plan', desc: 'Script, emotion curve, storyboard, and concept mapping.' },
  { step: '04', title: 'Human Approval', desc: 'Review gates before any expensive generation starts.' },
  { step: '05', title: 'Asset Generation', desc: 'Images, video, voice, and music via best-fit provider.' },
  { step: '06', title: 'Composition', desc: 'Remotion / HyperFrames / FFmpeg stitch into final MP4.' },
  { step: '07', title: 'Verification', desc: 'Scene fidelity, consistency, and quality audit before delivery.' },
];

const comparisonRows = [
  { feature: 'Local Rendering', closed: 'Limited', open: 'Unlimited', icon: <HardDrive className="w-4 h-4" /> },
  { feature: 'Pipeline Transparency', closed: 'Opaque', open: 'Full YAML Manifests', icon: <Workflow className="w-4 h-4" /> },
  { feature: 'Cost Control', closed: 'Surprise Bills', open: 'Approval Gates', icon: <CreditCard className="w-4 h-4" /> },
  { feature: 'Revision History', closed: 'None', open: 'JSON Checkpoints', icon: <Lock className="w-4 h-4" /> },
  { feature: 'Provider Choice', closed: 'Locked In', open: '47+ Auto-Routed', icon: <Gauge className="w-4 h-4" /> },
];

const codeLines = [
  { prompt: '$', cmd: 'git clone https://github.com/KeshavCracks/video-production-buddy.git', delay: 0 },
  { prompt: '$', cmd: 'cd video-production-buddy', delay: 100 },
  { prompt: '$', cmd: 'python3 -m venv .venv && source .venv/bin/activate', delay: 200 },
  { prompt: '$', cmd: 'make setup', delay: 300 },
  { prompt: '>', cmd: 'Installing Python dependencies...', delay: 400, output: true },
  { prompt: '>', cmd: 'Installing Remotion composer...', delay: 500, output: true },
  { prompt: '>', cmd: 'Installing free offline TTS (Piper)...', delay: 600, output: true },
  { prompt: '$', cmd: 'make demo', delay: 700 },
  { prompt: '>', cmd: 'Rendering zero-key demo suite...', delay: 800, output: true },
  { prompt: '>', cmd: 'Done! Output: projects/demos/renders/demo.mp4', delay: 900, output: true },
];

function TerminalBlock() {
  const [copied, setCopied] = useState(false);
  const copyCmd = () => {
    const text = codeLines.filter(l => !l.output).map(l => `${l.prompt} ${l.cmd}`).join('\n');
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="terminal w-full max-w-3xl mx-auto mt-12">
      <div className="terminal-header">
        <div className="terminal-dot" style={{ background: '#ef4444' }} />
        <div className="terminal-dot" style={{ background: '#f59e0b' }} />
        <div className="terminal-dot" style={{ background: '#10b981' }} />
        <span className="font-mono text-[10px] text-neutral-500 ml-2 tracking-widest uppercase">bash — zsh</span>
        <button onClick={copyCmd} className="ml-auto flex items-center gap-1.5 text-[10px] font-mono text-neutral-500 hover:text-emerald-400 transition-colors tracking-wider uppercase">
          {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
          {copied ? 'COPIED' : 'COPY'}
        </button>
      </div>
      <div className="terminal-body">
        {codeLines.map((line, i) => (
          <div key={i} className="flex items-start gap-2">
            <span className={line.output ? 'text-neutral-600' : 'text-emerald-500'}>{line.prompt}</span>
            <span className={line.output ? 'text-neutral-400' : 'text-neutral-200'}>{line.cmd}</span>
          </div>
        ))}
        <div className="flex items-center gap-2 mt-4">
          <span className="text-emerald-500">$</span>
          <span className="w-2 h-4 bg-emerald-500/60 animate-pulse" />
        </div>
      </div>
    </div>
  );
}

export default function Home() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <main className="relative overflow-x-hidden bg-[#0a0a0a] min-h-screen">
      {/* Navigation */}
      <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${scrolled ? 'bg-[#0a0a0a]/80 backdrop-blur-xl border-b border-white/[0.03]' : 'bg-transparent'}`}>
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded border border-emerald-500/30 bg-emerald-500/10 flex items-center justify-center">
              <Film className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="flex flex-col">
              <span className="font-mono text-[11px] tracking-[0.2em] text-emerald-400 font-medium leading-none">AI VIDEO FORGE</span>
              <span className="font-mono text-[9px] tracking-[0.15em] text-neutral-600 leading-none mt-0.5">AGENTIC STUDIO</span>
            </div>
          </div>
          <div className="hidden md:flex items-center gap-8">
            {['Features', 'Pipeline', 'Install', 'Stack'].map((item) => (
              <a key={item} href={`#${item.toLowerCase()}`} className="font-mono text-[10px] tracking-[0.15em] uppercase text-neutral-500 hover:text-emerald-400 transition-colors duration-300">
                {item}
              </a>
            ))}
          </div>
          <a href="https://github.com/KeshavCracks/video-production-buddy" target="_blank" rel="noopener noreferrer" className="btn-tech flex items-center gap-2">
            <Github className="w-3.5 h-3.5" />
            <span className="font-mono text-[10px] tracking-wider">GITHUB</span>
          </a>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative min-h-screen flex flex-col items-center justify-center pt-24 pb-32 overflow-hidden grid-bg">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-emerald-500/5 blur-[150px] rounded-full pointer-events-none" />
        <div className="absolute bottom-0 right-0 w-[500px] h-[500px] bg-emerald-500/3 blur-[120px] rounded-full pointer-events-none" />

        <div className="relative z-10 max-w-7xl mx-auto px-6 text-center w-full">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded border border-emerald-500/20 bg-emerald-500/5 mb-8">
            <Radio className="w-3 h-3 text-emerald-400 animate-pulse" />
            <span className="font-mono text-[10px] tracking-[0.2em] uppercase text-emerald-400">AGPLv3 — Open Source</span>
          </div>

          <h1 className="font-display text-5xl sm:text-7xl lg:text-[7.5rem] font-bold tracking-[-0.04em] mb-6 leading-[0.95] text-white">
            Own Your
            <br />
            <span className="gradient-text text-glow">Video Pipeline</span>
          </h1>

          <p className="text-lg sm:text-xl text-neutral-400 max-w-2xl mx-auto mb-10 leading-relaxed font-light tracking-tight">
            The open-source AI video studio where your assistant is the producer.
            No black boxes. No surprise bills. Just production-grade output you control.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <a href="#install" className="btn-tech btn-tech-primary flex items-center gap-2 group">
              <Rocket className="w-4 h-4" />
              <span>Get Started</span>
              <ChevronRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
            </a>
            <a href="https://github.com/KeshavCracks/video-production-buddy" target="_blank" rel="noopener noreferrer" className="btn-tech flex items-center gap-2">
              <Github className="w-4 h-4" />
              <span>View Source</span>
            </a>
          </div>

          <TerminalBlock />
        </div>
      </section>

      <div className="section-divider" />

      {/* Stats Row */}
      <section className="py-20 relative">
        <div className="max-w-6xl mx-auto px-6">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-white/[0.03] rounded-lg overflow-hidden border border-white/[0.03]">
            {[
              { label: 'STARS', value: '150+', icon: <Star className="w-4 h-4 text-emerald-400" /> },
              { label: 'PIPELINES', value: '11', icon: <Layers className="w-4 h-4 text-emerald-400" /> },
              { label: 'TOOLS', value: '47', icon: <Wand2 className="w-4 h-4 text-emerald-400" /> },
              { label: 'SKILLS', value: '124', icon: <Sparkles className="w-4 h-4 text-emerald-400" /> },
            ].map((stat) => (
              <div key={stat.label} className="bg-[#0a0a0a] p-8 flex flex-col items-center gap-3 hover:bg-[#111] transition-colors">
                <div className="flex items-center gap-2">
                  {stat.icon}
                  <span className="font-display text-3xl font-bold text-white">{stat.value}</span>
                </div>
                <span className="font-mono text-[10px] tracking-[0.2em] text-neutral-500 uppercase">{stat.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="section-divider" />

      {/* Comparison Table */}
      <section className="py-24 relative">
        <div className="max-w-5xl mx-auto px-6">
          <div className="text-center mb-16">
            <span className="label-mono mb-4 block">COMPARISON</span>
            <h2 className="font-display text-4xl sm:text-5xl font-bold tracking-tight text-white">
              Why Open-Source <span className="gradient-text">Wins</span>
            </h2>
          </div>
          <div className="border border-white/[0.03] rounded-lg overflow-hidden">
            <div className="grid grid-cols-3 gap-4 p-5 border-b border-white/[0.03] bg-white/[0.01]">
              <div className="font-mono text-[10px] tracking-[0.15em] text-neutral-500 uppercase">Feature</div>
              <div className="font-mono text-[10px] tracking-[0.15em] text-neutral-500 uppercase text-center">Closed Platforms</div>
              <div className="font-mono text-[10px] tracking-[0.15em] text-emerald-400 uppercase text-center">AI Video Forge</div>
            </div>
            {comparisonRows.map((item, i) => (
              <div key={item.feature} className={`grid grid-cols-3 gap-4 p-5 items-center hover:bg-white/[0.02] transition-colors ${i !== comparisonRows.length - 1 ? 'border-b border-white/[0.03]' : ''}`}>
                <div className="flex items-center gap-2 text-neutral-300 text-sm">
                  {item.icon}
                  {item.feature}
                </div>
                <div className="text-center text-neutral-600 text-sm font-mono">{item.closed}</div>
                <div className="text-center text-emerald-400 text-sm font-medium font-mono">{item.open}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="section-divider" />

      {/* Features */}
      <section id="features" className="py-24 relative">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <span className="label-mono mb-4 block">CAPABILITIES</span>
            <h2 className="font-display text-4xl sm:text-5xl font-bold tracking-tight text-white">
              Built for <span className="gradient-text">Control</span>
            </h2>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {features.map((f) => (
              <div key={f.title} className="relative group p-8 bg-[#111] border border-white/[0.03] rounded-lg hover:border-emerald-500/20 transition-all duration-500 hover:bg-[#141414]">
                <span className="font-mono text-[9px] tracking-[0.2em] text-emerald-500/60 uppercase absolute top-4 right-4">{f.label}</span>
                <div className="mb-6 p-3 w-fit rounded bg-emerald-500/5 border border-emerald-500/10 text-emerald-400">
                  {f.icon}
                </div>
                <h3 className="font-display text-xl font-semibold mb-3 text-white tracking-tight">{f.title}</h3>
                <p className="text-sm text-neutral-400 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="section-divider" />

      {/* Pipeline */}
      <section id="pipeline" className="py-24 relative">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <span className="label-mono mb-4 block">WORKFLOW</span>
            <h2 className="font-display text-4xl sm:text-5xl font-bold tracking-tight text-white">
              The <span className="gradient-text">Seven-Stage</span> Pipeline
            </h2>
          </div>
          <div className="relative max-w-3xl mx-auto">
            <div className="absolute left-[19px] sm:left-[23px] top-4 bottom-4 w-px timeline-line" />
            <div className="space-y-6">
              {pipelineSteps.map((s) => (
                <div key={s.step} className="relative pl-14 sm:pl-16">
                  <div className="absolute left-0 top-0 w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-[#0a0a0a] border border-emerald-500/30 flex items-center justify-center shadow-[0_0_15px_rgba(16,185,129,0.1)]">
                    <span className="font-mono text-xs font-bold text-emerald-400">{s.step}</span>
                  </div>
                  <div className="p-6 bg-[#111] border border-white/[0.03] rounded-lg hover:border-emerald-500/10 transition-all">
                    <h3 className="font-display text-lg font-semibold mb-2 text-white tracking-tight">{s.title}</h3>
                    <p className="text-sm text-neutral-400">{s.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <div className="section-divider" />

      {/* Install / Code Section */}
      <section id="install" className="py-24 relative grid-bg-faint">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <span className="label-mono mb-4 block">INSTALLATION</span>
            <h2 className="font-display text-4xl sm:text-5xl font-bold tracking-tight text-white">
              Get Running in <span className="gradient-text">5 Minutes</span>
            </h2>
            <p className="text-neutral-400 mt-4 max-w-xl mx-auto">Zero API keys required. The demo renders entirely offline with Remotion, FFmpeg, and local TTS.</p>
          </div>
          <div className="grid lg:grid-cols-2 gap-8 max-w-5xl mx-auto">
            <div className="terminal">
              <div className="terminal-header">
                <div className="terminal-dot" style={{ background: '#ef4444' }} />
                <div className="terminal-dot" style={{ background: '#f59e0b' }} />
                <div className="terminal-dot" style={{ background: '#10b981' }} />
                <span className="font-mono text-[10px] text-neutral-500 ml-2 tracking-widest uppercase">bash</span>
              </div>
              <div className="terminal-body">
                <div className="flex items-start gap-2"><span className="text-emerald-500">$</span><span className="text-neutral-200">git clone https://github.com/KeshavCracks/video-production-buddy.git</span></div>
                <div className="flex items-start gap-2 mt-1"><span className="text-emerald-500">$</span><span className="text-neutral-200">cd video-production-buddy</span></div>
                <div className="flex items-start gap-2 mt-1"><span className="text-emerald-500">$</span><span className="text-neutral-200">python3 -m venv .venv && source .venv/bin/activate</span></div>
                <div className="flex items-start gap-2 mt-1"><span className="text-emerald-500">$</span><span className="text-neutral-200">make setup</span></div>
                <div className="mt-2 text-neutral-600 text-xs">Installing Python dependencies...</div>
                <div className="text-neutral-600 text-xs">Installing Remotion composer...</div>
                <div className="text-neutral-600 text-xs">Installing free offline TTS (Piper)...</div>
                <div className="flex items-start gap-2 mt-2"><span className="text-emerald-500">$</span><span className="text-neutral-200">make demo</span></div>
                <div className="mt-2 text-emerald-500/60 text-xs">Done! Output: projects/demos/renders/demo.mp4</div>
              </div>
            </div>
            <div className="flex flex-col gap-4">
              {[
                { title: 'Python 3.10+', desc: 'Core runtime, tool registry, provider routing', status: 'REQUIRED' },
                { title: 'Node.js 22+', desc: 'Remotion composition, HyperFrames rendering', status: 'REQUIRED' },
                { title: 'FFmpeg', desc: 'Video encoding, stitching, post-production', status: 'REQUIRED' },
                { title: 'Make', desc: 'Build automation and task runner', status: 'REQUIRED' },
                { title: 'NVIDIA GPU', desc: 'Local diffusion models (optional, for AI generation)', status: 'OPTIONAL' },
              ].map((req) => (
                <div key={req.title} className="flex items-start gap-4 p-5 bg-[#111] border border-white/[0.03] rounded-lg hover:border-white/[0.06] transition-colors">
                  <div className="mt-0.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500/40" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-white">{req.title}</span>
                      <span className={`font-mono text-[9px] tracking-[0.15em] px-2 py-0.5 rounded ${req.status === 'REQUIRED' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-neutral-500/10 text-neutral-500 border border-white/5'}`}>
                        {req.status}
                      </span>
                    </div>
                    <p className="text-xs text-neutral-500">{req.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <div className="section-divider" />

      {/* Use Cases */}
      <section id="usecases" className="py-24 relative">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <span className="label-mono mb-4 block">USE CASES</span>
            <h2 className="font-display text-4xl sm:text-5xl font-bold tracking-tight text-white">
              Built for <span className="gradient-text">Every Story</span>
            </h2>
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            {useCases.map((uc) => (
              <div key={uc.title} className="relative p-8 bg-[#111] border border-white/[0.03] rounded-lg hover:border-emerald-500/15 transition-all duration-500 group">
                <span className="corner-badge">{uc.corner}</span>
                <h3 className="font-display text-xl font-semibold mb-3 text-white tracking-tight group-hover:text-emerald-400 transition-colors">{uc.title}</h3>
                <p className="text-sm text-neutral-400 mb-6 leading-relaxed">{uc.desc}</p>
                <div className="flex flex-wrap gap-2">
                  {uc.tags.map((tag) => (
                    <span key={tag} className="font-mono text-[9px] tracking-[0.15em] px-2.5 py-1 bg-white/[0.03] border border-white/[0.05] rounded text-neutral-400">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="section-divider" />

      {/* Tech Stack */}
      <section id="stack" className="py-24 relative">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <span className="label-mono mb-4 block">TECHNOLOGY</span>
            <h2 className="font-display text-4xl sm:text-5xl font-bold tracking-tight text-white">
              Powered by <span className="gradient-text">Best-in-Class</span>
            </h2>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {techStack.map((t) => (
              <div key={t.name} className="flex flex-col items-center gap-3 p-5 bg-[#111] border border-white/[0.03] rounded-lg hover:border-emerald-500/15 hover:bg-[#141414] transition-all duration-300 text-center">
                <div className="p-2.5 rounded bg-emerald-500/5 border border-emerald-500/10 text-emerald-400">
                  {t.icon}
                </div>
                <div>
                  <div className="font-display text-sm font-medium text-white">{t.name}</div>
                  <div className="font-mono text-[9px] tracking-[0.15em] text-neutral-500 mt-1">{t.category}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="section-divider" />

      {/* CTA */}
      <section className="py-24 relative">
        <div className="max-w-4xl mx-auto px-6">
          <div className="relative p-10 sm:p-16 text-center border border-emerald-500/10 rounded-2xl overflow-hidden bg-[#0a0a0a] glow-emerald">
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_rgba(16,185,129,0.08),transparent_70%)]" />
            <div className="relative z-10">
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded border border-emerald-500/20 bg-emerald-500/5 mb-6">
                <GitFork className="w-3 h-3 text-emerald-400" />
                <span className="font-mono text-[10px] tracking-[0.2em] uppercase text-emerald-400">AGPLv3 — Free Forever</span>
              </div>
              <h2 className="font-display text-3xl sm:text-5xl font-bold mb-4 tracking-tight text-white">
                Own Your <span className="gradient-text">Pipeline</span>
              </h2>
              <p className="text-neutral-400 max-w-lg mx-auto mb-10 leading-relaxed">
                No subscriptions, no black boxes, no vendor lock-in. Clone the repo, run the demo in 5 minutes, and start producing.
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <a href="https://github.com/KeshavCracks/video-production-buddy" target="_blank" rel="noopener noreferrer" className="btn-tech btn-tech-primary flex items-center gap-2 group">
                  <Github className="w-4 h-4" />
                  <span>Fork on GitHub</span>
                  <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                </a>
                <a href="https://github.com/KeshavCracks/video-production-buddy/blob/main/HOSTING.md" target="_blank" rel="noopener noreferrer" className="btn-tech flex items-center gap-2">
                  <Rocket className="w-4 h-4" />
                  <span>Hosting Guide</span>
                </a>
              </div>
              <div className="mt-10 flex flex-wrap items-center justify-center gap-6">
                {['Zero-Key Demo', 'AGPLv3 Licensed', 'Community Driven'].map((item) => (
                  <div key={item} className="flex items-center gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500/60" />
                    <span className="font-mono text-[10px] tracking-[0.15em] text-neutral-500 uppercase">{item}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/[0.03] py-12 bg-[#0a0a0a]">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <div className="w-6 h-6 rounded border border-emerald-500/30 bg-emerald-500/10 flex items-center justify-center">
              <Film className="w-3 h-3 text-emerald-400" />
            </div>
            <div className="flex flex-col">
              <span className="font-mono text-[10px] tracking-[0.2em] text-emerald-400 font-medium leading-none">AI VIDEO FORGE</span>
              <span className="font-mono text-[8px] tracking-[0.15em] text-neutral-600 leading-none mt-0.5">AGENTIC STUDIO</span>
            </div>
          </div>
          <div className="flex items-center gap-6">
            {['GitHub', 'Docs', 'License'].map((item) => (
              <a key={item} href={`https://github.com/KeshavCracks/video-production-buddy${item === 'Docs' ? '/blob/main/HOSTING.md' : item === 'License' ? '/blob/main/LICENSE' : ''}`} target="_blank" rel="noopener noreferrer" className="font-mono text-[10px] tracking-[0.15em] uppercase text-neutral-500 hover:text-emerald-400 transition-colors">
                {item}
              </a>
            ))}
          </div>
          <div className="font-mono text-[9px] tracking-[0.1em] text-neutral-700">
            Open-source community distribution. AGPLv3.
          </div>
        </div>
      </footer>
    </main>
  );
}
