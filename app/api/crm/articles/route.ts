import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { listArticles, saveArticle } from "@/lib/articles";

export const articleSchema = z.object({
  title: z.string().max(200),
  slug: z.string().max(200),
  excerpt: z.string().max(500),
  body_html: z.string().max(500_000),
  publish: z.boolean().default(false),
});

export async function GET() {
  return NextResponse.json(await listArticles());
}

export async function POST(request: NextRequest) {
  const parsed = articleSchema.safeParse(await request.json());
  if (!parsed.success) return NextResponse.json({ error: "Invalid article data." }, { status: 400 });
  try {
    const article = await saveArticle(parsed.data, undefined, parsed.data.publish);
    return NextResponse.json(article, { status: 201 });
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : "Could not save article." }, { status: 400 });
  }
}
