import { NextRequest, NextResponse } from "next/server";
import { getArticle, saveArticle } from "@/lib/articles";
import { articleSchema } from "@/app/api/crm/articles/route";

export async function GET(_request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const article = await getArticle((await params).id);
  return article ? NextResponse.json(article) : NextResponse.json({ error: "Article not found." }, { status: 404 });
}

export async function PUT(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const parsed = articleSchema.safeParse(await request.json());
  if (!parsed.success) return NextResponse.json({ error: "Invalid article data." }, { status: 400 });
  try {
    const article = await saveArticle(parsed.data, (await params).id, parsed.data.publish);
    return NextResponse.json(article);
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : "Could not save article." }, { status: 400 });
  }
}
