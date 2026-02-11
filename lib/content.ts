import fs from "node:fs/promises";
import path from "node:path";

import matter from "gray-matter";

const CONTENT_DIR = path.join(process.cwd(), "content");

export type BlogFrontmatter = {
  title: string;
  excerpt: string;
  date: string; // ISO date string
  tags?: string[];
  featured?: boolean;
  seoTitle?: string;
  seoDescription?: string;
};

export type CaseStudyFrontmatter = {
  title: string;
  excerpt: string;
  date: string; // ISO date string
  tags?: string[];
  featured?: boolean;
  seoTitle?: string;
  seoDescription?: string;
  client?: string;
  industry?: string;
  problem?: string;
  approach?: string;
  outcome?: string;
  stack?: string[];
};

export type ContentKind = "blog" | "case-studies";

export type ContentItem<TFrontmatter> = {
  kind: ContentKind;
  slug: string;
  frontmatter: TFrontmatter;
  content: string;
};

export type ContentListItem<TFrontmatter> = Omit<
  ContentItem<TFrontmatter>,
  "content"
>;

function assertString(value: unknown, field: string): asserts value is string {
  if (typeof value !== "string" || value.trim().length === 0) {
    throw new Error(`Invalid frontmatter field '${field}'`);
  }
}

async function readDirSafe(dirPath: string) {
  try {
    return await fs.readdir(dirPath);
  } catch {
    return [];
  }
}

function parseMdxFile<TFrontmatter extends { title: string; excerpt: string; date: string }>(
  kind: ContentKind,
  slug: string,
  raw: string,
) {
  const { data, content } = matter(raw);
  const fm = data as Partial<TFrontmatter>;

  assertString(fm.title, "title");
  assertString(fm.excerpt, "excerpt");
  assertString(fm.date, "date");

  return {
    kind,
    slug,
    frontmatter: fm as TFrontmatter,
    content,
  };
}

async function readMdxBySlug<TFrontmatter extends { title: string; excerpt: string; date: string }>(
  kind: ContentKind,
  slug: string,
) {
  const dirPath = path.join(CONTENT_DIR, kind);
  const candidates = [`${slug}.mdx`, `${slug}.md`];

  for (const fileName of candidates) {
    const fullPath = path.join(dirPath, fileName);
    try {
      const raw = await fs.readFile(fullPath, "utf8");
      return parseMdxFile<TFrontmatter>(kind, slug, raw);
    } catch {
      // try next candidate
    }
  }

  return null;
}

async function listSlugs(kind: ContentKind) {
  const dirPath = path.join(CONTENT_DIR, kind);
  const files = await readDirSafe(dirPath);
  return files
    .filter((f) => f.endsWith(".mdx") || f.endsWith(".md"))
    .map((f) => f.replace(/\.mdx?$/, ""))
    .filter(Boolean);
}

function sortByDateDesc<T extends { frontmatter: { date: string } }>(items: T[]) {
  return [...items].sort((a, b) => {
    const aTime = new Date(a.frontmatter.date).getTime();
    const bTime = new Date(b.frontmatter.date).getTime();
    return bTime - aTime;
  });
}

export async function getBlogPostSlugs() {
  return await listSlugs("blog");
}

export async function getCaseStudySlugs() {
  return await listSlugs("case-studies");
}

export async function getBlogPostBySlug(slug: string) {
  return await readMdxBySlug<BlogFrontmatter>("blog", slug);
}

export async function getCaseStudyBySlug(slug: string) {
  return await readMdxBySlug<CaseStudyFrontmatter>("case-studies", slug);
}

export async function listBlogPosts() {
  const slugs = await getBlogPostSlugs();
  const posts = await Promise.all(slugs.map((s) => getBlogPostBySlug(s)));
  return sortByDateDesc(
    posts.filter((p): p is ContentItem<BlogFrontmatter> => p !== null),
  ).map(({ content: _content, ...rest }) => rest);
}

export async function listCaseStudies() {
  const slugs = await getCaseStudySlugs();
  const items = await Promise.all(slugs.map((s) => getCaseStudyBySlug(s)));
  return sortByDateDesc(
    items.filter((p): p is ContentItem<CaseStudyFrontmatter> => p !== null),
  ).map(({ content: _content, ...rest }) => rest);
}

