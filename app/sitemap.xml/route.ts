import { listBlogPosts } from "@/lib/content";

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

  // Static routes plus /blog itself, which was missing entirely — this file
  // was a hand-maintained list that nobody updated when the blog section was
  // added, so every post published so far was invisible to it.
  const staticUrls = [
    "/",
    "/about",
    "/approach",
    "/expertise",
    "/contact",
    "/resources",
    "/privacy",
    "/frameworks/search-failure-modes",
    "/frameworks/query-interpretation",
    "/search-check",
    "/blog",
  ];

  const staticEntries = staticUrls.map((pathname) => {
    const loc = `${siteUrl}${pathname}`;
    return `<url><loc>${xmlEscape(loc)}</loc></url>`;
  });

  // Blog posts are sourced from the same listBlogPosts() the /blog index uses,
  // so a new post can never again go live without appearing here.
  const posts = await listBlogPosts();
  const postEntries = posts.map((post) => {
    const loc = `${siteUrl}/blog/${post.slug}`;
    const lastmod = new Date(
      post.frontmatter.updated ?? post.frontmatter.date,
    )
      .toISOString()
      .slice(0, 10);
    return `<url><loc>${xmlEscape(loc)}</loc><lastmod>${lastmod}</lastmod></url>`;
  });

  const body = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ...staticEntries,
    ...postEntries,
    "</urlset>",
  ].join("\n");

  return new Response(body, {
    headers: {
      "content-type": "application/xml; charset=utf-8",
    },
  });
}
