import { describe, expect, it } from "vitest";
import { cleanArticleHtml } from "./article-html";

describe("article HTML", () => {
  it("keeps rich formatting and supported media", () => {
    const html = cleanArticleHtml('<p style="text-align: center"><span style="color: #ff0000; font-size: 20px">Text</span></p><table><tbody><tr><th>Heading</th><td>Cell</td></tr></tbody></table><video src="https://example.com/movie.mp4" controls="controls"></video><audio src="https://example.com/audio.mp3" controls="controls"></audio><div data-youtube-video=""><iframe src="https://www.youtube-nocookie.com/embed/abc" title="Video"></iframe></div>');
    expect(html).toContain("text-align:center");
    expect(html).toContain("color:#ff0000");
    expect(html).toContain("<table>");
    expect(html).toContain("<video");
    expect(html).toContain("<audio");
    expect(html).toContain("youtube-nocookie.com/embed/abc");
    expect(html).toContain("data-youtube-video");
  });

  it("removes scripts, event handlers, and untrusted embeds", () => {
    const html = cleanArticleHtml('<script>alert(1)</script><img src="javascript:alert(1)" onerror="alert(1)"><iframe src="https://evil.example/embed" onload="alert(1)"></iframe><span style="position: fixed; color: expression(alert(1))">Text</span>');
    expect(html).not.toContain("<script");
    expect(html).not.toContain("onerror");
    expect(html).not.toContain("<iframe");
    expect(html).not.toContain("position");
    expect(html).not.toContain("expression");
  });
});
