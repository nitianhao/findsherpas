import type { Metadata } from "next";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { listBlogPosts } from "@/lib/content";

export const metadata: Metadata = {
  title: "Blog",
  description:
    "Articles about on-site search UX, relevance, and analytics—written for humans and search engines.",
};

export default async function BlogIndexPage() {
  const posts = await listBlogPosts();

  return (
    <div className="py-10">
      <h1 className="text-3xl font-semibold tracking-tight">Blog</h1>
      <p className="mt-3 max-w-2xl text-muted-foreground">
        Articles on on-site search UX, relevance, and analytics.
      </p>

      <div className="mt-10 grid gap-6 md:grid-cols-2">
        {posts.map((post) => (
          <Card key={post.slug} className="overflow-hidden">
            <CardHeader>
              <div className="flex items-center justify-between gap-4">
                <CardTitle className="text-lg">
                  <Link href={`/blog/${post.slug}`} className="hover:underline">
                    {post.frontmatter.title}
                  </Link>
                </CardTitle>
                {post.frontmatter.featured ? <Badge>Featured</Badge> : null}
              </div>
              <div className="text-xs text-muted-foreground">
                {new Date(post.frontmatter.date).toLocaleDateString(undefined, {
                  year: "numeric",
                  month: "short",
                  day: "numeric",
                })}
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                {post.frontmatter.excerpt}
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                {(post.frontmatter.tags ?? []).slice(0, 4).map((tag) => (
                  <Badge key={tag} variant="secondary">
                    {tag}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

