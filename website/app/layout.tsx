import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Video Production Buddy — Open-Source AI Video Studio',
  description: 'Plan, approve, generate, compose, and verify videos with an AI-powered production pipeline. The open-source alternative to black-box video generation.',
  keywords: 'AI video, open source video, Remotion, video production, generative AI, video editing, FFmpeg',
  openGraph: {
    title: 'Video Production Buddy — Open-Source AI Video Studio',
    description: 'The first open-source, agent-first AI video production system.',
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
      <body className="antialiased min-h-screen bg-dark-900 text-white">
        {children}
      </body>
    </html>
  );
}
