function xmlEscape(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;");
}

export async function GET() {
  const siteUrl =
    process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "") ??
    "https://findsherpas.com";

  const staticUrls = [
    "/",
    "/about",
    "/frameworks/search-failure-modes",
    "/frameworks/query-interpretation",
    "/search-check",
    "/book-a-call",
  ];

  const urls = staticUrls.map((pathname) => {
    const loc = `${siteUrl}${pathname}`;
    return `<url><loc>${xmlEscape(loc)}</loc></url>`;
  });

  const body = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ...urls,
    "</urlset>",
  ].join("\n");

  return new Response(body, {
    headers: {
      "content-type": "application/xml; charset=utf-8",
    },
  });
}

