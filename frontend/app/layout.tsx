import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Smart Buyer AI | Potential Customer Detection",
  description: "Smart Buyer AI: A Knowledge Base Intelligent Potential Customer Detection System for raw sheep wool, duck down and cashmere.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
