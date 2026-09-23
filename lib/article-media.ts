import { Extension, Node, mergeAttributes } from "@tiptap/core";

export const ArticleLineSpacing = Extension.create({
  name: "articleLineSpacing",
  addGlobalAttributes() {
    return [{
      types: ["paragraph", "heading"],
      attributes: {
        lineHeight: {
          default: null,
          parseHTML: element => element.style.lineHeight || null,
          renderHTML: attributes => attributes.lineHeight ? { style: `line-height: ${attributes.lineHeight}` } : {},
        },
      },
    }];
  },
});

export const ArticleVideo = Node.create({
  name: "articleVideo",
  group: "block",
  atom: true,
  draggable: true,
  addAttributes() {
    return { src: { default: null, parseHTML: element => element.getAttribute("src") } };
  },
  parseHTML() { return [{ tag: "video[src]" }]; },
  renderHTML({ HTMLAttributes }) {
    return ["video", mergeAttributes(HTMLAttributes, { controls: "controls", playsinline: "playsinline" })];
  },
});

export const ArticleAudio = Node.create({
  name: "articleAudio",
  group: "block",
  atom: true,
  draggable: true,
  addAttributes() {
    return { src: { default: null, parseHTML: element => element.getAttribute("src") } };
  },
  parseHTML() { return [{ tag: "audio[src]" }]; },
  renderHTML({ HTMLAttributes }) {
    return ["audio", mergeAttributes(HTMLAttributes, { controls: "controls" })];
  },
});

export const VimeoEmbed = Node.create({
  name: "vimeoEmbed",
  group: "block",
  atom: true,
  draggable: true,
  addAttributes() {
    return { src: { default: null, parseHTML: element => element.getAttribute("src") } };
  },
  parseHTML() { return [{ tag: 'iframe[data-type="vimeo"]' }]; },
  renderHTML({ HTMLAttributes }) {
    return ["iframe", mergeAttributes(HTMLAttributes, {
      "data-type": "vimeo",
      title: "Vimeo video",
      allow: "autoplay; fullscreen; picture-in-picture",
      allowfullscreen: "true",
      loading: "lazy",
    })];
  },
});
