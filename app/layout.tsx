import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AI Video Forge — Open-Source Agentic Video Studio',
  description: 'Production-grade video pipeline. Plan, approve, generate, compose, and verify — with full transparency. No black boxes. No surprise bills.',
  keywords: 'AI video, open source video, Remotion, video production, generative AI, FFmpeg, agentic AI, video pipeline',
  openGraph: {
    title: 'AI Video Forge — Open-Source Agentic Video Studio',
    description: 'The fully transparent alternative to black-box AI video generation.',
    type: 'website',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased min-h-screen bg-[#0a0a0a] text-white selection:bg-emerald-500/30">
        {children}
      </body>
    </html>
  );
}
