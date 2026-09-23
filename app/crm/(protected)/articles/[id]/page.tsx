import { notFound } from "next/navigation";
import { getArticle } from "@/lib/articles";
import { ArticleEditor } from "@/components/crm/articles/article-editor";

export default async function EditArticlePage({ params }: { params: Promise<{ id: string }> }) {
  const article = await getArticle((await params).id);
  if (!article) notFound();
  return <ArticleEditor article={article} />;
}
