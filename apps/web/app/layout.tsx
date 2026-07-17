import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "WTF Does This Repo Do?",
  description: "Understand unfamiliar codebases and review changes faster.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

