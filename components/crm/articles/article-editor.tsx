"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Image from "@tiptap/extension-image";
import { ArrowLeft, Bold, Italic, Link2, List, ListOrdered, Quote, Heading2, Heading3, ImagePlus, Undo2, Redo2 } from "lucide-react";
import { toast } from "sonner";
import { hanken } from "@/lib/site-font";
import type { Article } from "@/lib/articles";
import { Button } from "@/components/crm/ui/button";
import { Input } from "@/components/crm/ui/input";
import { Textarea } from "@/components/crm/ui/textarea";

export function ArticleEditor({ article }: { article?: Article }) {
  const router = useRouter();
  const [title, setTitle] = useState(article?.title ?? "");
  const [slug, setSlug] = useState(article?.slug ?? "");
  const [excerpt, setExcerpt] = useState(article?.excerpt ?? "");
  const [body, setBody] = useState(article?.body_html ?? "");
  const [tab, setTab] = useState<"write" | "preview">("write");
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const editor = useEditor({
    extensions: [StarterKit.configure({ link: { openOnClick: false, autolink: true } }), Image],
    content: article?.body_html ?? "",
    immediatelyRender: false,
    onUpdate: ({ editor }) => { setBody(editor.getHTML()); setDirty(true); },
  });

  function setTitleAndSlug(value: string) {
    setTitle(value);
    if (!article?.published_at && (!slug || slug === title.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""))) {
      setSlug(value.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""));
    }
    setDirty(true);
  }

  async function save(publish: boolean) {
    setSaving(true);
    try {
      const response = await fetch(article ? `/api/crm/articles/${article.id}` : "/api/crm/articles", {
        method: article ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, slug, excerpt, body_html: body, publish }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error ?? "Could not save article.");
      setDirty(false);
      toast.success(publish ? "Article published." : "Draft saved.");
      if (!article) router.replace(`/crm/articles/${data.id}`);
      router.refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not save article.");
    } finally {
      setSaving(false);
    }
  }

  function addLink() {
    const previous = editor?.getAttributes("link").href ?? "";
    const url = window.prompt("Link URL", previous);
    if (url === null || !editor) return;
    if (!url) editor.chain().focus().unsetLink().run();
    else if (/^https?:\/\//i.test(url) || /^mailto:/i.test(url)) editor.chain().focus().setLink({ href: url }).run();
    else toast.error("Use a full https:// URL or mailto: address.");
  }

  function addImage() {
    const url = window.prompt("Image URL (https://)");
    if (!url || !editor) return;
    if (!/^https:\/\//i.test(url)) return toast.error("Use a full https:// image URL.");
    const alt = window.prompt("Image description") ?? "";
    editor.chain().focus().setImage({ src: url, alt }).run();
  }

  const toolbar = [
    { label: "Bold", icon: Bold, active: editor?.isActive("bold"), action: () => editor?.chain().focus().toggleBold().run() },
    { label: "Italic", icon: Italic, active: editor?.isActive("italic"), action: () => editor?.chain().focus().toggleItalic().run() },
    { label: "Heading 2", icon: Heading2, active: editor?.isActive("heading", { level: 2 }), action: () => editor?.chain().focus().toggleHeading({ level: 2 }).run() },
    { label: "Heading 3", icon: Heading3, active: editor?.isActive("heading", { level: 3 }), action: () => editor?.chain().focus().toggleHeading({ level: 3 }).run() },
    { label: "Bullet list", icon: List, active: editor?.isActive("bulletList"), action: () => editor?.chain().focus().toggleBulletList().run() },
    { label: "Numbered list", icon: ListOrdered, active: editor?.isActive("orderedList"), action: () => editor?.chain().focus().toggleOrderedList().run() },
    { label: "Quote", icon: Quote, active: editor?.isActive("blockquote"), action: () => editor?.chain().focus().toggleBlockquote().run() },
    { label: "Link", icon: Link2, active: editor?.isActive("link"), action: addLink },
    { label: "Image", icon: ImagePlus, active: false, action: addImage },
    { label: "Undo", icon: Undo2, active: false, action: () => editor?.chain().focus().undo().run() },
    { label: "Redo", icon: Redo2, active: false, action: () => editor?.chain().focus().redo().run() },
  ];

  return <div className="space-y-6">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div><Link href="/crm/articles" className="mb-2 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft size={15} /> Articles</Link><h1 className="text-2xl font-bold">{article ? "Edit article" : "New article"}</h1></div>
      <div className="flex items-center gap-2">
        {article?.published_at && <a href={`/blog/${article.slug}`} target="_blank" rel="noopener noreferrer" className="text-sm underline underline-offset-2">View live</a>}
        <Button variant="outline" disabled={saving} onClick={() => save(false)}>{saving ? "Saving…" : "Save draft"}</Button>
        <Button disabled={saving} onClick={() => save(true)}>{saving ? "Publishing…" : "Publish"}</Button>
      </div>
    </div>
    <div className="rounded-xl border bg-card p-5 space-y-4">
      <label className="block text-sm font-medium">Title<Input className="mt-1" value={title} onChange={e => setTitleAndSlug(e.target.value)} placeholder="Article title" /></label>
      <label className="block text-sm font-medium">URL slug<Input className="mt-1" value={slug} onChange={e => { setSlug(e.target.value); setDirty(true); }} disabled={Boolean(article?.published_at)} placeholder="article-title" /></label>
      <label className="block text-sm font-medium">Summary<Textarea className="mt-1" value={excerpt} onChange={e => { setExcerpt(e.target.value); setDirty(true); }} placeholder="A short introduction shown on the articles page" rows={3} /></label>
      {article?.published_at && dirty && <p className="text-xs text-muted-foreground">Your changes are unpublished until you click Publish.</p>}
    </div>
    <div className="overflow-hidden rounded-xl border bg-card">
      <div className="flex items-center gap-1 border-b p-2">
        <button type="button" onClick={() => setTab("write")} className={`rounded-md px-3 py-1.5 text-sm ${tab === "write" ? "bg-accent font-medium" : "text-muted-foreground"}`}>Write</button>
        <button type="button" onClick={() => setTab("preview")} className={`rounded-md px-3 py-1.5 text-sm ${tab === "preview" ? "bg-accent font-medium" : "text-muted-foreground"}`}>Preview</button>
      </div>
      {tab === "write" ? <>
        <div className="flex flex-wrap gap-1 border-b p-2">{toolbar.map(item => <button key={item.label} type="button" title={item.label} aria-label={item.label} aria-pressed={Boolean(item.active)} onClick={item.action} className={`rounded-md p-2 hover:bg-accent ${item.active ? "bg-accent text-primary" : "text-muted-foreground"}`}><item.icon size={17} /></button>)}</div>
        <div className={`fs-site ${hanken.variable} article-editor-canvas`}><article className="fs-article"><EditorContent editor={editor} /></article></div>
      </> : <div className={`fs-site ${hanken.variable}`}><article className="fs-article">
        <div className="max-w-3xl"><div className="flex flex-wrap gap-x-2 text-xs text-muted-foreground"><time>{new Date(article?.published_at ?? Date.now()).toLocaleDateString("en-GB", { year: "numeric", month: "short", day: "numeric" })}</time><span>·</span><span>By Michal Pekarcik</span></div><h1 className="mt-3 text-balance text-4xl font-semibold tracking-tight">{title || "Untitled article"}</h1><p className="mt-4 text-lg text-muted-foreground">{excerpt}</p></div>
        <div className="mt-10 max-w-3xl fs-article-body" dangerouslySetInnerHTML={{ __html: body }} />
      </article></div>}
    </div>
  </div>;
}
