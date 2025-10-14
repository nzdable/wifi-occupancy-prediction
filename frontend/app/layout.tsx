// app/layout.tsx
import type { Metadata } from "next";
import "./globals.css";
import { Inter, Cinzel, Open_Sans, Cormorant_Garamond } from "next/font/google";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const cinzel = Cinzel({ subsets: ["latin"], variable: "--font-cinzel" });
const openSans = Open_Sans({ subsets: ["latin"], variable: "--font-open-sans" });
const garamond = Cormorant_Garamond({ subsets: ["latin"], variable: "--font-garamond" });

export const metadata: Metadata = {
  title: "ADDU Library | Sign in",
  description:
    "Find the perfect time to study with real-time occupancy data and AI-powered predictions.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html 
    lang="en"
    suppressHydrationWarning
    className={`${inter.variable} ${cinzel.variable} ${openSans.variable} ${garamond.variable}`}>
      <body className="min-h-screen bg-[#030B3A] text-white antialiased font-inter">
        {children}
      </body>
    </html>
  );
}
