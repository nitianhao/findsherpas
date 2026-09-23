import sanitizeHtml from "sanitize-html";

export function cleanArticleHtml(value: string) {
  return sanitizeHtml(value, {
    allowedTags: [
      "p", "h2", "h3", "h4", "h5", "h6", "strong", "em", "s", "u", "sub", "sup",
      "span", "mark", "ul", "ol", "li", "blockquote", "a", "img", "br", "hr", "pre", "code",
      "table", "thead", "tbody", "tfoot", "tr", "th", "td", "colgroup", "col",
      "div", "label", "input", "video", "audio", "iframe",
    ],
    allowedAttributes: {
      "*": ["style"],
      a: ["href", "target", "rel", "title"],
      img: ["src", "alt", "title", "width", "height"],
      ul: ["data-type"], li: ["data-type", "data-checked"],
      input: ["type", "checked", "disabled"],
      mark: ["data-color", "style"],
      th: ["colspan", "rowspan", "colwidth", "style"],
      td: ["colspan", "rowspan", "colwidth", "style"],
      col: ["span", "style"],
      div: ["data-youtube-video"],
      video: ["src", "controls", "playsinline", "poster"],
      audio: ["src", "controls"],
      iframe: ["src", "data-type", "title", "width", "height", "allow", "allowfullscreen", "loading", "frameborder"],
    },
    allowedStyles: {
      "*": {
        "text-align": [/^(left|center|right|justify)$/],
        color: [/^#[0-9a-fA-F]{3,8}$/],
        "background-color": [/^#[0-9a-fA-F]{3,8}$/],
        "font-family": [/^(Arial|Georgia|Verdana|Tahoma|Courier New|serif|sans-serif|monospace)$/],
        "font-size": [/^(12|14|16|18|20|24|30|36)px$/],
        "line-height": [/^(1|1\.2|1\.5|2)$/],
      },
    },
    allowedSchemes: ["http", "https", "mailto"],
    allowedSchemesByTag: { img: ["https"], video: ["https"], audio: ["https"], iframe: ["https"] },
    allowedIframeHostnames: ["www.youtube-nocookie.com", "www.youtube.com", "player.vimeo.com"],
    exclusiveFilter: (frame) => ["iframe", "img", "video", "audio"].includes(frame.tag) && !frame.attribs.src,
    transformTags: {
      a: (_tag, attrs) => ({ tagName: "a", attribs: { href: attrs.href ?? "", rel: "noopener noreferrer", ...(attrs.target === "_blank" ? { target: "_blank" } : {}) } }),
      input: (_tag, attrs) => ({ tagName: "input", attribs: { type: "checkbox", disabled: "disabled", ...(attrs.checked !== undefined ? { checked: "checked" } : {}) } }),
    },
  });
}
