import Link from "next/link";
import { Plus } from "lucide-react";
import { hasUnpublishedChanges, listArticles } from "@/lib/articles";
import { buttonVariants } from "@/components/crm/ui/button";

export default async function ArticlesPage() {
  const articles = await listArticles();
  return <div className="space-y-6">
    <div className="flex items-center justify-between">
      <div><h1 className="text-2xl font-bold">Articles</h1><p className="text-sm text-muted-foreground">Write, revisit, and publish articles.</p></div>
      <Link href="/crm/articles/new" className={buttonVariants()}><Plus className="mr-2 h-4 w-4" />New article</Link>
    </div>
    <div className="overflow-hidden rounded-xl border bg-card">
      {articles.length ? articles.map((article) => <Link key={article.id} href={`/crm/articles/${article.id}`} className="flex items-center justify-between gap-4 border-b p-4 last:border-b-0 hover:bg-muted/50">
        <div><div className="font-medium">{article.title || "Untitled article"}</div><div className="mt-1 text-sm text-muted-foreground">/blog/{article.slug} · Updated {new Date(article.updated_at).toLocaleDateString("en-GB")}</div></div>
        <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${article.published_at && !hasUnpublishedChanges(article) ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>{hasUnpublishedChanges(article) ? "Unpublished changes" : article.published_at ? "Published" : "Draft"}</span>
      </Link>) : <p className="p-8 text-sm text-muted-foreground">No articles yet. Create your first draft.</p>}
    </div>
  </div>;
}
