import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AI Video Forge — Open-Source Agentic Video Studio',
  description: 'Plan, approve, generate, compose, and verify videos with a fully transparent, open-source AI production pipeline. No black boxes. No surprise bills.',
  keywords: 'AI video, open source video, Remotion, video production, generative AI, video editing, FFmpeg, agentic AI',
  openGraph: {
    title: 'AI Video Forge — Open-Source Agentic Video Studio',
    description: 'The fully transparent alternative to black-box AI video generation.',
    type: 'website',
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased min-h-screen bg-[#0a0a0f] text-white">
        {children}
      </body>
    </html>
  );
}
