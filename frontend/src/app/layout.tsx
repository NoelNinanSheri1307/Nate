import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Nate — Conversational AI Assistant",
  description: "Real-time Voice-to-Voice AI Assistant built with Faster-Whisper, Gemini 2.5, and Piper TTS.",
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
