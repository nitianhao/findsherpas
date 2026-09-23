import sanitizeHtml from "sanitize-html";
import { adminDb, id } from "@/lib/crm/instant-db";

export type Article = {
  id: string;
  title: string;
  slug: string;
  excerpt: string;
  body_html: string;
  published_title?: string;
  published_excerpt?: string;
  published_body_html?: string;
  published_at?: string;
  published_updated_at?: string;
  created_at: string;
  updated_at: string;
};

export type ArticleInput = Pick<Article, "title" | "slug" | "excerpt" | "body_html">;

export function hasUnpublishedChanges(article: Article) {
  return Boolean(article.published_at) && (
    article.title !== article.published_title ||
    article.excerpt !== article.published_excerpt ||
    article.body_html !== article.published_body_html
  );
}

export function normalizeSlug(value: string) {
  return value.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

export function cleanArticleHtml(value: string) {
  return sanitizeHtml(value, {
    allowedTags: ["p", "h2", "h3", "h4", "strong", "em", "s", "u", "ul", "ol", "li", "blockquote", "a", "img", "br", "hr", "pre", "code"],
    allowedAttributes: { a: ["href", "target", "rel"], img: ["src", "alt", "title"] },
    allowedSchemes: ["http", "https", "mailto"],
    allowedSchemesByTag: { img: ["http", "https"] },
    transformTags: {
      a: (_tag, attrs) => ({ tagName: "a", attribs: { href: attrs.href ?? "", rel: "noopener noreferrer", ...(attrs.target === "_blank" ? { target: "_blank" } : {}) } }),
    },
  });
}

export async function listArticles(): Promise<Article[]> {
  const data = await adminDb.query({ articles: {} });
  return [...data.articles].sort((a, b) => b.updated_at.localeCompare(a.updated_at)) as Article[];
}

export async function getArticle(id: string): Promise<Article | null> {
  const data = await adminDb.query({ articles: { $: { where: { id } } } });
  return (data.articles[0] as Article | undefined) ?? null;
}

export async function getPublishedArticleBySlug(slug: string): Promise<Article | null> {
  const data = await adminDb.query({ articles: { $: { where: { slug } } } });
  const article = data.articles[0] as Article | undefined;
  return article?.published_at ? article : null;
}

export async function listPublishedArticles(): Promise<Article[]> {
  return (await listArticles()).filter((article) => Boolean(article.published_at));
}

export async function saveArticle(input: ArticleInput, articleId?: string, publish = false): Promise<Article> {
  const title = input.title.trim();
  const excerpt = input.excerpt.trim();
  const slug = normalizeSlug(input.slug || title);
  if (!title || !slug || !excerpt) throw new Error("Title, slug, and summary are required.");
  const body_html = cleanArticleHtml(input.body_html);
  if (publish && !sanitizeHtml(body_html, { allowedTags: [], allowedAttributes: {} }).trim()) {
    throw new Error("Add article content before publishing.");
  }

  const current = articleId ? await getArticle(articleId) : null;
  if (articleId && !current) throw new Error("Article not found.");
  if (current?.published_at && current.slug !== slug) throw new Error("The slug of a published article cannot be changed.");

  const { getBlogPostSlugs } = await import("@/lib/content");
  const legacySlugs = await getBlogPostSlugs();
  if (legacySlugs.includes(slug)) throw new Error("This slug is already used by an existing article.");
  const matching = await adminDb.query({ articles: { $: { where: { slug } } } });
  if (matching.articles.some((article) => article.id !== articleId)) throw new Error("This slug is already in use.");

  const now = new Date().toISOString();
  const newId = articleId ?? id();
  await adminDb.transact(adminDb.tx.articles[newId].update({
    title, slug, excerpt, body_html,
    created_at: current?.created_at ?? now,
    updated_at: now,
    ...(publish ? {
      published_title: title,
      published_excerpt: excerpt,
      published_body_html: body_html,
      published_at: current?.published_at ?? now,
      published_updated_at: now,
    } : {}),
  }));
  return (await getArticle(newId))!;
}
