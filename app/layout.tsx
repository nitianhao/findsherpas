import Script from "next/script";
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

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
    "Internal search audits for ecommerce teams: diagnose ranking, query interpretation, relevance, and search UX issues across your on-site search experience.",
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "https://findsherpas.com"),
  openGraph: {
    type: "website",
    title: "Find Sherpas",
    description:
      "Internal search audits for ecommerce teams: diagnose ranking, query interpretation, relevance, and search UX issues.",
    siteName: "Find Sherpas",
    images: [{ url: "/og-image.png", width: 1200, height: 630 }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Find Sherpas",
    description:
      "Internal search audits for ecommerce teams: diagnose ranking, query interpretation, relevance, and search UX issues.",
    images: ["/og-image.png"],
  },
  icons: {
    icon: [
      { url: "/icon.svg", type: "image/svg+xml" },
      { url: "/favicon-32x32.png", sizes: "32x32", type: "image/png" },
      { url: "/favicon-16x16.png", sizes: "16x16", type: "image/png" },
    ],
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
        {children}
      </body>
    </html>
  );
}
