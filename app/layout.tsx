import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import {
  DEFAULT_SOCIAL_IMAGE,
  SITE_AUTHOR,
  SITE_NAME,
  SITE_URL,
} from "@/lib/seo";
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
    default: SITE_NAME,
    template: `%s | ${SITE_NAME}`,
  },
  description:
    "A boutique agency for ecommerce on-site search optimization: query analysis, relevance tuning, search UX and ongoing experimentation.",
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL ?? SITE_URL,
  ),
  openGraph: {
    type: "website",
    title: SITE_NAME,
    description:
      "Ecommerce on-site search optimization. From the first fixes to the finer details of relevance, analytics and search UX.",
    siteName: SITE_NAME,
    images: [
      {
        url: DEFAULT_SOCIAL_IMAGE,
        width: 1200,
        height: 630,
        alt: `${SITE_NAME} — ecommerce search optimization`,
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: SITE_NAME,
    description:
      "Ecommerce on-site search optimization. From the first fixes to the finer details of relevance, analytics and search UX.",
    images: [DEFAULT_SOCIAL_IMAGE],
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
  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Organization",
        "@id": `${SITE_URL}/#organization`,
        name: SITE_NAME,
        url: SITE_URL,
        logo: `${SITE_URL}/icon.svg`,
        email: "michal@findsherpas.com",
        founder: {
          "@type": "Person",
          name: SITE_AUTHOR,
          url: `${SITE_URL}/about`,
        },
        areaServed: ["Europe", "United Kingdom"],
        knowsAbout: [
          "On-site search",
          "Search relevance",
          "Ranking",
          "Query understanding",
          "Algolia",
          "Elasticsearch",
          "Luigi's Box",
          "Constructor",
        ],
      },
      {
        "@type": "WebSite",
        "@id": `${SITE_URL}/#website`,
        url: SITE_URL,
        name: SITE_NAME,
        publisher: { "@id": `${SITE_URL}/#organization` },
        inLanguage: "en",
      },
      {
        "@type": "Service",
        "@id": `${SITE_URL}/#service`,
        name: "Ecommerce on-site search optimization",
        description:
          "Search audits and ongoing optimization covering query analysis, relevance, search UX and experimentation.",
        provider: { "@id": `${SITE_URL}/#organization` },
        areaServed: ["Europe", "United Kingdom"],
        serviceType: [
          "Ecommerce site search audit",
          "Ongoing search optimization",
          "Search relevance consulting",
          "Query interpretation analysis",
          "Search UX optimization",
        ],
      },
    ],
  };

  return (
    <html lang="en">
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} font-sans antialiased text-base md:text-lg leading-relaxed`}
      >
        <template
          dangerouslySetInnerHTML={{
            __html:
              "<!-- PUBLIC SITE DIRECTION — THESIS: Customer language reveals the decisions behind search; refuse generic agency card grids. OWN-WORLD: Deep ink, soft white, humanist typography, restrained blue-grey meaning highlights, bracket mark and flat controls. STORY: Understand the service, explore a query, see how work begins and continues, discuss your search. FIRST VIEWPORT: 53/47 split; large headline and explicit offer left, annotated multilingual query right, primary action below the offer. FORM: Language reference, candidate 4, seed c85c00a9; composition-a.png. Scope: public marketing routes, not CRM. FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, and DESIGN.md -->",
          }}
        />
        {children}
      </body>
    </html>
  );
}
