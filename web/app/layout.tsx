import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Daily Context | Research, ready to listen",
  description: "A fresh, source-linked podcast briefing made for your day.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
