"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { upload } from "@vercel/blob/client";
import { EditorContent, useEditor } from "@tiptap/react";
import type { Editor } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import Image from "@tiptap/extension-image";
import { TableKit } from "@tiptap/extension-table";
import { TextStyleKit } from "@tiptap/extension-text-style";
import Highlight from "@tiptap/extension-highlight";
import TextAlign from "@tiptap/extension-text-align";
import Subscript from "@tiptap/extension-subscript";
import Superscript from "@tiptap/extension-superscript";
import TaskList from "@tiptap/extension-task-list";
import TaskItem from "@tiptap/extension-task-item";
import Youtube from "@tiptap/extension-youtube";
import FileHandler from "@tiptap/extension-file-handler";
import { ArrowLeft, Bold, Italic, Link2, List, ListOrdered, Quote, Undo2, Redo2, Underline, Strikethrough, Code2, Subscript as SubscriptIcon, Superscript as SuperscriptIcon, RemoveFormatting, AlignLeft, AlignCenter, AlignRight, AlignJustify, CheckSquare, IndentIncrease, IndentDecrease, Minus } from "lucide-react";
import { toast } from "sonner";
import { hanken } from "@/lib/site-font";
import type { Article } from "@/lib/articles";
import { ArticleAudio, ArticleLineSpacing, ArticleVideo, VimeoEmbed } from "@/lib/article-media";
import { cleanArticleHtml } from "@/lib/article-html";
import { Button } from "@/components/crm/ui/button";
import { Input } from "@/components/crm/ui/input";
import { Textarea } from "@/components/crm/ui/textarea";

type MediaKind = "image" | "video" | "audio" | "pdf";
const ACCEPTED_TYPES: Record<MediaKind, string[]> = {
  image: ["image/jpeg", "image/png", "image/webp", "image/gif", "image/avif"],
  video: ["video/mp4", "video/webm"],
  audio: ["audio/mpeg", "audio/mp4", "audio/ogg", "audio/wav"],
  pdf: ["application/pdf"],
};
const mediaKind = (file: File) => (Object.keys(ACCEPTED_TYPES) as MediaKind[]).find(kind => ACCEPTED_TYPES[kind].includes(file.type));
function httpsUrl(value: string) { try { const url = new URL(value); return url.protocol === "https:" ? url.toString() : null; } catch { return null; } }

export function ArticleEditor({ article }: { article?: Article }) {
  const router = useRouter();
  const fileInput = useRef<HTMLInputElement>(null);
  const [title, setTitle] = useState(article?.title ?? "");
  const [slug, setSlug] = useState(article?.slug ?? "");
  const [excerpt, setExcerpt] = useState(article?.excerpt ?? "");
  const [body, setBody] = useState(article?.body_html ?? "");
  const [tab, setTab] = useState<"write" | "preview">("write");
  const [saving, setSaving] = useState(false);
  const [pendingUploads, setPendingUploads] = useState(0);
  const uploading = pendingUploads > 0;
  const [uploadProgress, setUploadProgress] = useState(0);
  const [dirty, setDirty] = useState(false);
  const [, setSelectionVersion] = useState(0);

  async function uploadFile(file: File, instance: Editor, position?: number) {
    const kind = mediaKind(file);
    if (!kind) return toast.error("Use an image, MP4, WebM, MP3, M4A, OGG, WAV, or PDF file.");
    if (file.size > 100 * 1024 * 1024) return toast.error("Files must be 100 MB or smaller.");
    setPendingUploads(count => count + 1);
    setUploadProgress(0);
    try {
      const filename = file.name.replace(/[^a-zA-Z0-9._-]/g, "-").slice(-100) || "media";
      const blob = await upload(`articles/${Date.now()}-${filename}`, file, {
        access: "public", handleUploadUrl: "/api/article-media-upload", multipart: file.size > 10 * 1024 * 1024,
        onUploadProgress: progress => setUploadProgress(Math.round(progress.percentage)),
      });
      const content = kind === "image" ? { type: "image", attrs: { src: blob.url, alt: file.name.replace(/\.[^.]+$/, "") } }
        : kind === "video" ? { type: "articleVideo", attrs: { src: blob.url } }
        : kind === "audio" ? { type: "articleAudio", attrs: { src: blob.url } }
        : { type: "text", text: file.name, marks: [{ type: "link", attrs: { href: blob.url, target: "_blank" } }] };
      if (position === undefined) instance.chain().focus().insertContent(content).run();
      else instance.chain().focus().insertContentAt(position, content).run();
      toast.success("Media inserted.");
    } catch (error) { toast.error(error instanceof Error ? error.message : "Upload failed."); }
    finally { setPendingUploads(count => count - 1); setUploadProgress(0); }
  }

  const editor = useEditor({
    extensions: [
      StarterKit.configure({ heading: { levels: [2, 3, 4, 5, 6] }, link: { openOnClick: false, autolink: true } }),
      Image.configure({ allowBase64: false }), TableKit, TextStyleKit.configure({ lineHeight: false, backgroundColor: false }), ArticleLineSpacing,
      Highlight.configure({ multicolor: true }), TextAlign.configure({ types: ["heading", "paragraph"] }),
      Subscript, Superscript, TaskList, TaskItem.configure({ nested: true }), Youtube.configure({ nocookie: true, width: 720, height: 405 }),
      ArticleVideo, ArticleAudio, VimeoEmbed,
      FileHandler.configure({
        allowedMimeTypes: Object.values(ACCEPTED_TYPES).flat(), consumePasteEvent: true,
        onPaste: (instance, files) => files.forEach(file => { void uploadFile(file, instance); }),
        onDrop: (instance, files, position) => files.forEach(file => { void uploadFile(file, instance, position); }),
      }),
    ],
    content: article?.body_html ?? "",
    immediatelyRender: false,
    onUpdate: ({ editor }) => { setBody(editor.getHTML()); setDirty(true); setSelectionVersion(value => value + 1); },
    onSelectionUpdate: () => setSelectionVersion(value => value + 1),
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
    else if (httpsUrl(url) || /^mailto:[^\s@]+@[^\s@]+$/i.test(url)) editor.chain().focus().setLink({ href: url, target: "_blank" }).run();
    else toast.error("Use a full https:// URL or mailto: address.");
  }

  function addUrlMedia(kind: MediaKind | "youtube" | "vimeo") {
    const value = window.prompt(`${kind === "pdf" ? "PDF" : kind} URL (https://)`);
    if (!value) return;
    const url = value && httpsUrl(value);
    if (!url) return toast.error("Use a full https:// URL.");
    if (!editor) return;
    if (kind === "image") {
      const alt = window.prompt("Image description for accessibility") ?? "";
      editor.chain().focus().setImage({ src: url, alt }).run();
    } else if (kind === "video" || kind === "audio") {
      editor.chain().focus().insertContent({ type: kind === "video" ? "articleVideo" : "articleAudio", attrs: { src: url } }).run();
    } else if (kind === "youtube") {
      if (!["youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"].includes(new URL(url).hostname)) return toast.error("Use a YouTube video URL.");
      editor.chain().focus().setYoutubeVideo({ src: url }).run();
    } else if (kind === "vimeo") {
      const parsed = new URL(url);
      if (!["vimeo.com", "www.vimeo.com", "player.vimeo.com"].includes(parsed.hostname)) return toast.error("Use a Vimeo video URL.");
      const id = parsed.pathname.match(/(?:\/video)?\/(\d+)(?:\/|$)/)?.[1];
      if (!id) return toast.error("Use a Vimeo video URL.");
      editor.chain().focus().insertContent({ type: "vimeoEmbed", attrs: { src: `https://player.vimeo.com/video/${id}` } }).run();
    } else {
      const text = window.prompt("Link text", "Download PDF") ?? "Download PDF";
      editor.chain().focus().insertContent({ type: "text", text, marks: [{ type: "link", attrs: { href: url, target: "_blank" } }] }).run();
    }
  }

  function openUpload(kind: MediaKind) {
    if (fileInput.current) fileInput.current.accept = ACCEPTED_TYPES[kind].join(",");
    fileInput.current?.click();
  }

  function indentList(increase: boolean) {
    if (!editor) return;
    const item = editor.isActive("taskItem") ? "taskItem" : "listItem";
    if (increase) editor.chain().focus().sinkListItem(item).run();
    else editor.chain().focus().liftListItem(item).run();
  }

  const toolbar = [
    { label: "Bold", icon: Bold, active: editor?.isActive("bold"), action: () => editor?.chain().focus().toggleBold().run() },
    { label: "Italic", icon: Italic, active: editor?.isActive("italic"), action: () => editor?.chain().focus().toggleItalic().run() },
    { label: "Underline", icon: Underline, active: editor?.isActive("underline"), action: () => editor?.chain().focus().toggleUnderline().run() },
    { label: "Strikethrough", icon: Strikethrough, active: editor?.isActive("strike"), action: () => editor?.chain().focus().toggleStrike().run() },
    { label: "Inline code", icon: Code2, active: editor?.isActive("code"), action: () => editor?.chain().focus().toggleCode().run() },
    { label: "Subscript", icon: SubscriptIcon, active: editor?.isActive("subscript"), action: () => editor?.chain().focus().toggleSubscript().run() },
    { label: "Superscript", icon: SuperscriptIcon, active: editor?.isActive("superscript"), action: () => editor?.chain().focus().toggleSuperscript().run() },
    { label: "Clear formatting", icon: RemoveFormatting, active: false, action: () => editor?.chain().focus().unsetAllMarks().clearNodes().run() },
    { label: "Align left", icon: AlignLeft, active: editor?.isActive({ textAlign: "left" }), action: () => editor?.chain().focus().setTextAlign("left").run() },
    { label: "Align center", icon: AlignCenter, active: editor?.isActive({ textAlign: "center" }), action: () => editor?.chain().focus().setTextAlign("center").run() },
    { label: "Align right", icon: AlignRight, active: editor?.isActive({ textAlign: "right" }), action: () => editor?.chain().focus().setTextAlign("right").run() },
    { label: "Justify", icon: AlignJustify, active: editor?.isActive({ textAlign: "justify" }), action: () => editor?.chain().focus().setTextAlign("justify").run() },
    { label: "Bullet list", icon: List, active: editor?.isActive("bulletList"), action: () => editor?.chain().focus().toggleBulletList().run() },
    { label: "Numbered list", icon: ListOrdered, active: editor?.isActive("orderedList"), action: () => editor?.chain().focus().toggleOrderedList().run() },
    { label: "Checklist", icon: CheckSquare, active: editor?.isActive("taskList"), action: () => editor?.chain().focus().toggleTaskList().run() },
    { label: "Indent list item", icon: IndentIncrease, active: false, action: () => indentList(true) },
    { label: "Outdent list item", icon: IndentDecrease, active: false, action: () => indentList(false) },
    { label: "Quote", icon: Quote, active: editor?.isActive("blockquote"), action: () => editor?.chain().focus().toggleBlockquote().run() },
    { label: "Divider", icon: Minus, active: false, action: () => editor?.chain().focus().setHorizontalRule().run() },
    { label: "Link", icon: Link2, active: editor?.isActive("link"), action: addLink },
    { label: "Undo", icon: Undo2, active: false, action: () => editor?.chain().focus().undo().run() },
    { label: "Redo", icon: Redo2, active: false, action: () => editor?.chain().focus().redo().run() },
  ];

  return <div className="space-y-6">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div><Link href="/crm/articles" className="mb-2 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft size={15} /> Articles</Link><h1 className="text-2xl font-bold">{article ? "Edit article" : "New article"}</h1></div>
      <div className="flex items-center gap-2">
        {article?.published_at && <a href={`/blog/${article.slug}`} target="_blank" rel="noopener noreferrer" className="text-sm underline underline-offset-2">View live</a>}
        <Button variant="outline" disabled={saving || uploading} onClick={() => save(false)}>{saving ? "Saving…" : "Save draft"}</Button>
        <Button disabled={saving || uploading} onClick={() => save(true)}>{saving ? "Publishing…" : "Publish"}</Button>
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
        <div className="space-y-2 border-b p-3" aria-label="Article formatting toolbar">
          <div className="flex flex-wrap items-center gap-2">
            <select aria-label="Block style" value={editor?.isActive("heading") ? `h${editor.getAttributes("heading").level}` : editor?.isActive("codeBlock") ? "codeBlock" : "paragraph"}
              onChange={event => { const value = event.target.value; if (value === "paragraph") editor?.chain().focus().setParagraph().run(); else if (value === "codeBlock") editor?.chain().focus().setCodeBlock().run(); else editor?.chain().focus().setHeading({ level: Number(value.slice(1)) as 2 | 3 | 4 | 5 | 6 }).run(); }}
              className="h-9 rounded-md border bg-background px-2 text-sm">
              <option value="paragraph">Paragraph</option>{[2, 3, 4, 5, 6].map(level => <option key={level} value={`h${level}`}>Heading {level}</option>)}<option value="codeBlock">Code block</option>
            </select>
            <select aria-label="Font family" value={editor?.getAttributes("textStyle").fontFamily ?? ""} onChange={event => event.target.value ? editor?.chain().focus().setFontFamily(event.target.value).run() : editor?.chain().focus().unsetFontFamily().run()} className="h-9 rounded-md border bg-background px-2 text-sm">
              <option value="">Default font</option>{["Arial", "Georgia", "Verdana", "Tahoma", "Courier New"].map(font => <option key={font} value={font}>{font}</option>)}
            </select>
            <select aria-label="Font size" value={editor?.getAttributes("textStyle").fontSize ?? ""} onChange={event => event.target.value ? editor?.chain().focus().setFontSize(event.target.value).run() : editor?.chain().focus().unsetFontSize().run()} className="h-9 rounded-md border bg-background px-2 text-sm">
              <option value="">Size</option>{[12, 14, 16, 18, 20, 24, 30, 36].map(size => <option key={size} value={`${size}px`}>{size}px</option>)}
            </select>
            <select aria-label="Line spacing" value={editor?.isActive("heading") ? editor.getAttributes("heading").lineHeight ?? "" : editor?.getAttributes("paragraph").lineHeight ?? ""} onChange={event => editor?.chain().focus().updateAttributes(editor.isActive("heading") ? "heading" : "paragraph", { lineHeight: event.target.value || null }).run()} className="h-9 rounded-md border bg-background px-2 text-sm">
              <option value="">Line spacing</option>{["1", "1.2", "1.5", "2"].map(height => <option key={height} value={height}>{height}×</option>)}
            </select>
            <label className="flex items-center gap-1 rounded-md border px-2 text-xs" title="Text color">Text color <input type="color" aria-label="Text color" defaultValue="#1c272d" onChange={event => editor?.chain().focus().setColor(event.target.value).run()} className="h-8 w-7 cursor-pointer" /></label>
            <label className="flex items-center gap-1 rounded-md border px-2 text-xs" title="Highlight color">Highlight <input type="color" aria-label="Highlight color" defaultValue="#fff2a8" onChange={event => editor?.chain().focus().setHighlight({ color: event.target.value }).run()} className="h-8 w-7 cursor-pointer" /></label>
            <button type="button" className="rounded-md border px-2 py-1.5 text-xs hover:bg-accent" onClick={() => editor?.chain().focus().unsetColor().unsetHighlight().run()}>Reset colors</button>
          </div>
          <div className="flex flex-wrap gap-1">{toolbar.map(item => <button key={item.label} type="button" title={item.label} aria-label={item.label} aria-pressed={Boolean(item.active)} onMouseDown={event => event.preventDefault()} onClick={item.action} className={`rounded-md p-2 hover:bg-accent ${item.active ? "bg-accent text-primary" : "text-muted-foreground"}`}><item.icon size={17} /></button>)}</div>
          <div className="flex flex-wrap items-center gap-2 border-t pt-2 text-sm">
            <span className="mr-1 font-medium">Table</span>
            <button type="button" className="rounded-md border px-2 py-1 hover:bg-accent" onClick={() => editor?.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()}>Insert 3 × 3</button>
            {[
              ["Add row", () => editor?.chain().focus().addRowAfter().run()],
              ["Add column", () => editor?.chain().focus().addColumnAfter().run()],
              ["Remove row", () => editor?.chain().focus().deleteRow().run()],
              ["Remove column", () => editor?.chain().focus().deleteColumn().run()],
              ["Merge cells", () => editor?.chain().focus().mergeCells().run()],
              ["Split cell", () => editor?.chain().focus().splitCell().run()],
              ["Toggle header row", () => editor?.chain().focus().toggleHeaderRow().run()],
              ["Remove table", () => editor?.chain().focus().deleteTable().run()],
            ].map(([label, action]) => <button key={label as string} type="button" disabled={!editor?.isActive("table")} className="rounded-md border px-2 py-1 hover:bg-accent disabled:opacity-35" onClick={action as () => void}>{label as string}</button>)}
          </div>
          <div className="flex flex-wrap items-center gap-2 border-t pt-2 text-sm">
            <span className="mr-1 font-medium">Media</span>
            {(["image", "video", "audio", "pdf"] as MediaKind[]).map(kind => <button key={kind} type="button" disabled={uploading} className="rounded-md border px-2 py-1 hover:bg-accent disabled:opacity-35" onClick={() => openUpload(kind)}>{kind === "pdf" ? "Upload PDF" : `Upload ${kind}`}</button>)}
            <span className="text-muted-foreground">or</span>
            {(["image", "video", "audio", "pdf", "youtube", "vimeo"] as const).map(kind => <button key={kind} type="button" className="rounded-md border px-2 py-1 hover:bg-accent" onClick={() => addUrlMedia(kind)}>{kind === "pdf" ? "PDF link" : kind === "youtube" || kind === "vimeo" ? kind[0].toUpperCase() + kind.slice(1) : `${kind[0].toUpperCase() + kind.slice(1)} URL`}</button>)}
            <input ref={fileInput} type="file" className="hidden" accept={Object.values(ACCEPTED_TYPES).flat().join(",")}
              onChange={event => { const file = event.target.files?.[0]; if (file && editor) void uploadFile(file, editor); event.target.value = ""; }} />
          </div>
          {editor?.isActive("image") && <div className="flex flex-wrap items-center gap-2 border-t pt-2 text-sm">
            <span className="font-medium">Selected image</span>
            <select aria-label="Image width" className="rounded-md border bg-background px-2 py-1" value={editor.getAttributes("image").width ?? ""}
              onChange={event => editor.chain().focus().updateAttributes("image", { width: event.target.value ? Number(event.target.value) : null, height: null }).run()}>
              <option value="">Full width</option><option value="320">Small</option><option value="640">Medium</option><option value="960">Large</option>
            </select>
            <button type="button" className="rounded-md border px-2 py-1 hover:bg-accent" onClick={() => { const alt = window.prompt("Image description for accessibility", editor.getAttributes("image").alt ?? ""); if (alt !== null) editor.chain().focus().updateAttributes("image", { alt }).run(); }}>Edit description</button>
          </div>}
          {uploading && <p role="status" className="text-xs text-muted-foreground">Uploading media… {uploadProgress}%</p>}
        </div>
        <div className={`fs-site ${hanken.variable} article-editor-canvas`}><article className="fs-article"><EditorContent editor={editor} /></article></div>
      </> : <div className={`fs-site ${hanken.variable}`}><article className="fs-article">
        <div className="max-w-3xl"><div className="flex flex-wrap gap-x-2 text-xs text-muted-foreground"><time>{new Date(article?.published_at ?? Date.now()).toLocaleDateString("en-GB", { year: "numeric", month: "short", day: "numeric" })}</time><span>·</span><span>By Michal Pekarcik</span></div><h1 className="mt-3 text-balance text-4xl font-semibold tracking-tight">{title || "Untitled article"}</h1><p className="mt-4 text-lg text-muted-foreground">{excerpt}</p></div>
        <div className="mt-10 max-w-3xl fs-article-body" dangerouslySetInnerHTML={{ __html: cleanArticleHtml(body) }} />
      </article></div>}
    </div>
  </div>;
}
