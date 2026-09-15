import { chromium } from "playwright";
import { writeFile } from "node:fs/promises";

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
const origin = process.env.FS_ORIGIN ?? "http://127.0.0.1:3000";
const results = { pages: [], interactions: [], errors: [], overflow: [] };
page.on("pageerror", error => results.errors.push(error.message));
const routes = ["/", "/approach", "/expertise", "/about", "/contact", "/blog", "/blog/algolia-best-practices", "/blog/faceted-search-best-practices", "/frameworks/query-interpretation", "/frameworks/search-failure-modes", "/search-check", "/case-studies"];
const overflow = async (label) => {
  const items = await page.evaluate(() => [...document.querySelectorAll("body *")].filter(el => {
    const r = el.getBoundingClientRect(), style = getComputedStyle(el);
    return r.width && (r.right > innerWidth + 1 || r.left < -1) && style.position !== "absolute" && style.position !== "fixed" && !el.closest("pre, table");
  }).map(el => ({ tag: el.tagName, class: el.className?.baseVal ?? el.className, text: el.textContent?.slice(0, 65) })).slice(0, 12));
  if (items.length) results.overflow.push({ label, items });
};
for (const viewport of [{width:1440,height:1100},{width:390,height:844}]) {
  await page.setViewportSize(viewport);
  const device = viewport.width === 1440 ? "desktop" : "mobile";
  for (const route of routes) {
    const response = await page.goto(origin + route);
    await page.evaluate(() => document.fonts.ready);
    const slug = route === "/" ? "home" : route.slice(1).replaceAll("/", "-");
    results.pages.push({ route, device, status: response.status(), h1: await page.locator("h1").count(), title: await page.title() });
    await overflow(device + route);
    if (!process.env.FS_CHECKS_ONLY) await page.screenshot({path: ".impeccable/screenshots/" + device + "-" + slug + ".png", fullPage: true});
    if (!process.env.FS_CHECKS_ONLY && (route === "/" || ["/approach","/expertise","/about","/contact"].includes(route))) {
      await page.screenshot({path: ".impeccable/screenshots/" + device + "-" + slug + "-viewport.png"});
    }
    if (!process.env.FS_CHECKS_ONLY && route === "/") {
      for (const [i, selector] of ["#what-we-do", ".fs-engagement", ".fs-demo-section", ".fs-expertise-section", ".fs-experience", ".fs-contact-band"].entries()) {
        await page.locator(selector).screenshot({path: ".impeccable/screenshots/" + device + "-home-section-" + i + ".png"});
      }
    }
  }
}
for (const width of [320, 390, 768, 1024, 1280, 1440]) {
  await page.setViewportSize({width,height:1000});
  await page.goto(origin);
  for (const language of ["English", "Deutsch", "Français", "Nederlands"]) {
    await page.getByRole("button", {name:language,exact:true}).click();
    await overflow(width + "-" + language);
    results.interactions.push({name: width + "-" + language, pressed: await page.getByRole("button", {name:language,exact:true}).getAttribute("aria-pressed")});
  }
}
await page.setViewportSize({width:390,height:844});
await page.getByRole("button", {name:"Open menu",exact:true}).click();
results.interactions.push({name:"menu open focus", active:await page.evaluate(()=>document.activeElement?.getAttribute("aria-label"))});
await page.keyboard.press("Shift+Tab");
results.interactions.push({name:"menu focus trap", active:await page.evaluate(()=>document.activeElement?.textContent)});
await page.keyboard.press("Escape");
results.interactions.push({name:"menu escape", closed:await page.getByRole("dialog").count() === 0, focus:await page.getByRole("button",{name:"Open menu",exact:true}).evaluate(el=>el===document.activeElement)});
await page.getByRole("button", {name:"Open menu",exact:true}).click();
await page.getByRole("navigation", {name:"Mobile navigation"}).getByRole("link", {name:"Approach"}).click();
await page.waitForURL("**/approach");
results.interactions.push({name:"mobile navigation", url:page.url(), overflow:await page.evaluate(()=>document.body.style.overflow)});
await page.goto(origin);
for (const title of ["A typo","A local expression","A product type","An occasion"]) {
  await page.getByRole("button",{name:title,exact:true}).click();
  await page.getByRole("button",{name:"Play example: "+title,exact:true}).click();
  await page.waitForFunction(()=>document.querySelector("video")?.readyState >= 1);
  const source=await page.locator("video source").first().getAttribute("src");
  const response=await page.request.get(origin+source);
  results.interactions.push({name:"scenario "+title,source,status:response.status()});
}
await page.goto(origin+"/contact");
await writeFile(".impeccable/verification.json",JSON.stringify(results,null,2));
await page.getByLabel("Name",{exact:true}).fill("Test visitor");
await page.getByLabel("Email",{exact:true}).fill("visitor@example.test");
await page.getByLabel("What would you like to improve?").fill("Test enquiry. This submission is intercepted and never delivered.");
let submission = 0;
await page.route("**/api/contact", async route => {
  submission += 1;
  await new Promise(resolve=>setTimeout(resolve,500));
  await route.fulfill({status:submission === 1 ? 503 : 200,contentType:"application/json",body:JSON.stringify(submission === 1 ? {error:"Test unavailable. Please email us directly."} : {ok:true,delivery:"email",id:"mocked"})});
});
await page.getByRole("button",{name:"Send message",exact:true}).click();
results.interactions.push({name:"form loading",disabled:await page.getByRole("button",{name:"Sending…"}).isDisabled()});
await page.locator(".fs-form-error").waitFor();
results.interactions.push({name:"form error retains message",value:await page.getByLabel("What would you like to improve?").inputValue(),focused:await page.locator(".fs-form-error").evaluate(el=>el===document.activeElement)});
await page.getByRole("button",{name:"Send message",exact:true}).click();
await page.locator(".fs-form-status").waitFor();
results.interactions.push({name:"form success",text:await page.locator(".fs-form-status").textContent()});
await page.goto(origin+"/book-a-call");
results.interactions.push({name:"old contact redirect",url:page.url()});
const sitemap=await (await page.request.get(origin+"/sitemap.xml")).text();
results.interactions.push({name:"sitemap",newRoutes:["/approach","/expertise","/contact"].every(route=>sitemap.includes(route)),noDrafts:!sitemap.includes("/case-studies")});
await writeFile(".impeccable/verification.json",JSON.stringify(results,null,2));
console.log(JSON.stringify(results,null,2));
await browser.close();
