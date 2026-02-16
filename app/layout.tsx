import Script from "next/script";
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { SiteFooter } from "@/components/site/site-footer";
import { SiteNav } from "@/components/site/site-nav";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "Find Sherpas",
    template: "%s | Find Sherpas",
  },
  description:
    "On-site search optimization: UX audits, relevance tuning, and search analytics design for faster discovery and higher conversion.",
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "https://findsherpas.com"),
  openGraph: {
    type: "website",
    title: "Find Sherpas",
    description:
      "On-site search optimization: UX audits, relevance tuning, and search analytics design.",
    siteName: "Find Sherpas",
  },
  twitter: {
    card: "summary_large_image",
    title: "Find Sherpas",
    description:
      "On-site search optimization: UX audits, relevance tuning, and search analytics design.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased text-base md:text-lg leading-relaxed`}>
        <Script
          strategy="afterInteractive"
          src="https://www.googletagmanager.com/gtag/js?id=G-M8D3D607D7"
        />
        <Script id="google-analytics" strategy="afterInteractive">
          {`
            window.dataLayer = window.dataLayer || [];
            function gtag(){dataLayer.push(arguments);}
            gtag('js', new Date());

            gtag('config', 'G-M8D3D607D7');
          `}
        </Script>
        <div className="min-h-dvh bg-background">
          <SiteNav />
          <main className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
            {children}
          </main>
          <SiteFooter />
        </div>
      </body>
    </html>
  );
}
