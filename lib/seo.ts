import type { Metadata } from "next";

export const SITE_NAME = "Find Sherpas";
export const SITE_URL = "https://findsherpas.com";
export const SITE_AUTHOR = "Michal Pekarcik";
export const SITE_AUTHOR_URL = `${SITE_URL}/about`;
export const DEFAULT_SOCIAL_IMAGE = `${SITE_URL}/og-image.png`;

type PageMetadataOptions = {
  title: string;
  description: string;
  path: string;
  absoluteTitle?: boolean;
};

export function createPageMetadata({
  title,
  description,
  path,
  absoluteTitle = false,
}: PageMetadataOptions): Metadata {
  const canonical = new URL(path, `${SITE_URL}/`).toString();
  const socialTitle = absoluteTitle ? title : `${title} | ${SITE_NAME}`;

  return {
    title: absoluteTitle ? { absolute: title } : title,
    description,
    alternates: { canonical },
    openGraph: {
      type: "website",
      title: socialTitle,
      description,
      url: canonical,
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
      title: socialTitle,
      description,
      images: [DEFAULT_SOCIAL_IMAGE],
    },
  };
}

export function breadcrumbSchema(
  items: Array<{ name: string; path: string }>,
) {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: item.name,
      item: new URL(item.path, `${SITE_URL}/`).toString(),
    })),
  };
}
