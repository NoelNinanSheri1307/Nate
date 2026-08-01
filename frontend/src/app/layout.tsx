import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Nate — Real-Time Voice AI Assistant",
  description: "A zero-latency, local-first voice-to-voice conversational AI assistant built with Faster-Whisper, Gemini 2.5, and Piper TTS.",
  openGraph: {
    title: "Nate — Real-Time Voice AI Assistant",
    description: "A zero-latency, local-first voice-to-voice conversational AI assistant built with Faster-Whisper, Gemini 2.5, and Piper TTS.",
    images: ["/logo.jpg"],
    type: "website"
  }
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-background text-primary-text">{children}</body>
    </html>
  );
}
