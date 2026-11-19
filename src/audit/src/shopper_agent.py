"""AI shopper prototype: Claude drives a real browser to complete shopping tasks on a site.

Instead of probing the engine with isolated queries, a shopper agent gets a goal ("waterproof
women's walking boots under £120"), searches, scrolls, refines and opens products like a
customer, and stops when it has found something it would buy — or gives up. A separate judge
call then rates the session from the final screenshots and the action log.

This is a PROTOTYPE for measuring step counts and token cost per task. It is not wired into the
audit pipeline.

Guardrails: the agent can only search, click visible elements, scroll and go back. It never
types into forms, and clicks on cart / checkout / account / login / newsletter elements or
off-site links are refused before they happen.

Run (from src/audit/)::

    .venv312/bin/python -m src.shopper_agent --driver claude-haiku-5-5 --judge claude-sonnet-5-5
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional
from urllib.parse import quote_plus, urlparse

from pydantic import BaseModel, Field

from src.llm_compat import get_client

logger = logging.getLogger(__name__)

# $ per million tokens: input, output, cache read, cache write (5-minute TTL = 1.25x input).
PRICES = {
    "claude-opus-5-5": (4.00, 20.00, 0.20, 5.00),
    "claude-sonnet-5-5": (2.00, 10.00, 0.20, 2.50),
    "claude-haiku-5-5": (0.10, 0.50, 0.01, 0.125),
    "claude-sonnet-4-6": (3.00, 15.00, 0.30, 3.75),
}

MAX_STEPS = 12
VIEWPORT = {"width": 1280, "height": 800}
SCREENSHOT_WIDTH = 1024          # ~870 image tokens at 1024x640
MAX_ELEMENTS = 45

# Phrases only: product tiles legitimately contain words like "bag" ("Sleeping Bag").
_BLOCKED_TEXT = re.compile(
    r"\b(add to (?:bag|basket|cart|wishlist)|my bag|view bag|basket|cart|checkout|check out|sign in|"
    r"log ?in|log ?out|register|my account|newsletter|subscribe|wishlist|buy now|pay now)\b|^\s*bag\s*(\(\d+\))?\s*$",
    re.I)
_BLOCKED_URL = re.compile(r"/(?:cart|basket|checkout|account|login|signin|register|wishlist)\b", re.I)


@dataclass
class Task:
    id: str
    goal: str


DEFAULT_SITE = "https://www.cotswoldoutdoor.com/lister.html?q={}"
DEFAULT_TASKS = [
    Task("boots", "Find waterproof walking boots for a woman, under £120."),
    Task("tent", "You're going camping for a weekend with two kids. Find a tent that sleeps four people."),
    Task("gift", "Find a present for a friend who just started trail running. Budget: under £50."),
]


# ---------------------------------------------------------------------------
# Tools the driver can call
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "search",
        "description": "Type a query into the site's search and load the results page.",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}},
                         "required": ["query"], "additionalProperties": False},
    },
    {
        "name": "click",
        "description": "Click a visible element by its [ref] number from the element list "
                       "(product tiles, filters, sort options, 'load more').",
        "input_schema": {"type": "object", "properties": {"ref": {"type": "integer"}},
                         "required": ["ref"], "additionalProperties": False},
    },
    {
        "name": "scroll",
        "description": "Scroll the page one screen down or up.",
        "input_schema": {"type": "object", "properties": {"direction": {"type": "string", "enum": ["down", "up"]}},
                         "required": ["direction"], "additionalProperties": False},
    },
    {
        "name": "go_back",
        "description": "Go back to the previous page.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "finish",
        "description": "End the session: either you found a product you would buy, or you gave up.",
        "input_schema": {
            "type": "object",
            "properties": {
                "outcome": {"type": "string", "enum": ["found", "gave_up"]},
                "product_title": {"type": "string"},
                "product_url": {"type": "string"},
                "reason": {"type": "string"},
            },
            "required": ["outcome", "reason"],
            "additionalProperties": False,
        },
    },
]

DRIVER_SYSTEM = """You are a realistic online shopper on a retailer's website. You have a shopping goal. Use the site the way a normal customer would: search, look at the results, refine your search wording if results are poor, use visible filters or sorting when they help, open a product page to check details (price, type) when needed.

Rules:
- Each turn you see a screenshot of the current viewport, the URL, and a numbered list of clickable elements. Act with exactly one tool call per turn.
- Prefer the search box (the `search` tool) over browsing menus — this session evaluates the site's search.
- Stop with `finish(outcome="found")` as soon as you are on (or looking at) a product that satisfies the goal. Give its title and URL.
- Stop with `finish(outcome="gave_up")` if, like a real customer, you would leave: after a few honest attempts the site does not show suitable products.
- Never add to basket, sign in, or check out. Never leave the site.
- Be efficient: a real shopper spends a few minutes, not an hour."""


class SessionVerdict(BaseModel):
    """Judge output. Field order = generation order: observations before the verdict."""

    observations: str = Field(description="INTERNAL: what happened, step by step, and why the outcome is (in)correct.")
    goal_met: bool = Field(description="True only if the chosen product genuinely satisfies every part of the goal.")
    searches_needed: int = Field(description="How many searches the shopper typed before reaching a suitable product (0 if never).")
    first_search_worked: bool = Field(description="Did the shopper's FIRST search already show a suitable product on page 1?")
    friction: list[str] = Field(description="Concrete moments where the site's search made the shopper work harder or fail.")
    client_summary: str = Field(description="2-3 plain sentences for the retailer. No scores, no AI/model wording.")
    severity: Literal["CRITICAL", "MODERATE", "MINOR", "PASS"]


JUDGE_SYSTEM = """You review a recorded shopping session on a retailer's site to assess its SEARCH experience. You get the shopper's goal, the log of actions with the page URL and what was visible, and the last screenshots.

Severity:
- CRITICAL: the shopper gave up, or settled on a product that does not meet the goal, while the store plausibly stocks suitable products.
- MODERATE: the goal was met only after rephrasing the search or digging (filters, several pages, multiple searches).
- MINOR: met on the first search, but with friction (suitable product below the first screen, irrelevant items mixed in).
- PASS: the first search showed a suitable product near the top.
Do not blame search for catalog gaps you can see evidence of (e.g. the store clearly has no such product type)."""


# ---------------------------------------------------------------------------
# Browser
# ---------------------------------------------------------------------------

_ELEMENTS_JS = """
(maxItems) => {
  const out = [];
  let n = 0;
  document.querySelectorAll('[data-shopper-ref]').forEach(e => e.removeAttribute('data-shopper-ref'));
  const els = document.querySelectorAll('a[href], button, [role="button"], [role="option"], [role="checkbox"], select, summary');
  for (const el of els) {
    const r = el.getBoundingClientRect();
    if (r.width < 4 || r.height < 4 || r.bottom < 0 || r.top > window.innerHeight) continue;
    const style = getComputedStyle(el);
    if (style.visibility === 'hidden' || style.display === 'none') continue;
    let text = (el.innerText || el.getAttribute('aria-label') || el.getAttribute('title') || '').replace(/\\s+/g, ' ').trim();
    if (!text) { const img = el.querySelector('img[alt]'); if (img) text = img.alt.trim(); }
    if (!text) continue;
    n += 1;
    el.setAttribute('data-shopper-ref', String(n));
    out.push({ref: n, tag: el.tagName.toLowerCase(), text: text.slice(0, 80), href: el.getAttribute('href') || ''});
    if (out.length >= maxItems) break;
  }
  return out;
}
"""


class Browser:
    def __init__(self, headless: bool = True):
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        # Prefer Playwright's bundled Chromium; fall back to the locally installed Google Chrome.
        try:
            self._browser = self._pw.chromium.launch(headless=headless)
        except Exception:
            self._browser = self._pw.chromium.launch(headless=headless, channel="chrome")
        self._ctx = self._browser.new_context(viewport=VIEWPORT, locale="en-GB")
        self.page = self._ctx.new_page()
        self.elements: list[dict] = []
        self._consent_done = False

    def close(self):
        try:
            self._browser.close()
        finally:
            self._pw.stop()

    def goto(self, url: str):
        self.page.goto(url, wait_until="domcontentloaded", timeout=45000)
        self._settle()

    def _settle(self):
        try:
            self.page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        if not self._consent_done:
            self._consent_done = self._dismiss_consent()

    def _dismiss_consent(self) -> bool:
        """Decline non-essential cookies when the banner offers it; otherwise accept only to proceed."""
        for label in ("Reject all", "Reject All", "Decline", "Only necessary", "Necessary only",
                      "Accept necessary", "Accept all", "Accept All", "Accept"):
            try:
                btn = self.page.get_by_role("button", name=label, exact=False).first
                if btn.is_visible(timeout=500):
                    btn.click(timeout=2000)
                    self.page.wait_for_timeout(500)
                    return True
            except Exception:
                continue
        return False

    def observe(self) -> tuple[str, str, str, list[dict]]:
        """(url, title, screenshot base64 JPEG, elements). Retries while a navigation is in flight."""
        last: Exception | None = None
        for _ in range(4):
            try:
                self.page.wait_for_load_state("domcontentloaded", timeout=15000)
                self.elements = self.page.evaluate(_ELEMENTS_JS, MAX_ELEMENTS)
                png = self.page.screenshot(type="png")
                return self.page.url, self.page.title(), _to_jpeg_b64(png), self.elements
            except Exception as e:  # "Execution context was destroyed" mid-navigation
                last = e
                self.page.wait_for_timeout(1000)
        raise last

    def click(self, ref: int) -> str:
        el = next((e for e in self.elements if e["ref"] == ref), None)
        if el is None:
            return f"No element with ref {ref} on this screen."
        blocked = _blocked_reason(el, self.page.url)
        if blocked:
            return blocked
        loc = self.page.locator(f'[data-shopper-ref="{ref}"]').first
        try:
            loc.click(timeout=3000)
        except Exception:
            # Sticky headers / overlays intercept the pointer; a DOM click still follows the link.
            loc.evaluate("el => el.click()")
        self.page.wait_for_timeout(500)  # let a click-triggered navigation start before settling
        self._settle()
        return f"Clicked [{ref}] {el['text'][:60]}"

    def scroll(self, direction: str) -> str:
        self.page.mouse.wheel(0, 700 if direction == "down" else -700)
        self.page.wait_for_timeout(800)
        return f"Scrolled {direction}"

    def back(self) -> str:
        self.page.go_back(wait_until="domcontentloaded", timeout=30000)
        self._settle()
        return "Went back"


def _to_jpeg_b64(png: bytes) -> str:
    from PIL import Image

    img = Image.open(io.BytesIO(png)).convert("RGB")
    if img.width > SCREENSHOT_WIDTH:
        img = img.resize((SCREENSHOT_WIDTH, round(img.height * SCREENSHOT_WIDTH / img.width)))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=70)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _blocked_reason(el: dict, current_url: str) -> str | None:
    """Refuse clicks that could change account state or leave the site."""
    href = el.get("href") or ""
    if _BLOCKED_TEXT.search(el.get("text", "")):
        return f"Not allowed: '{el['text'][:40]}' is a basket/account/sign-in control."
    if href and _BLOCKED_URL.search(href):
        return f"Not allowed: link goes to {href[:60]}."
    if href.startswith("http"):
        if urlparse(href).netloc.split(":")[0].removeprefix("www.") != urlparse(current_url).netloc.removeprefix("www."):
            return "Not allowed: link leaves the site."
    return None


# ---------------------------------------------------------------------------
# Usage accounting
# ---------------------------------------------------------------------------


@dataclass
class Usage:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0

    def add(self, usage) -> None:
        self.calls += 1
        for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
            setattr(self, k, getattr(self, k) + int(getattr(usage, k, 0) or 0))

    def cost(self, model: str) -> float:
        pin, pout, pread, pwrite = PRICES.get(model, PRICES["claude-sonnet-5-5"])
        return (self.input_tokens * pin + self.output_tokens * pout + self.cache_read_input_tokens * pread
                + self.cache_creation_input_tokens * pwrite) / 1e6


@dataclass
class StepLog:
    step: int
    action: str
    args: dict
    result: str
    url: str
    input_tokens: int
    output_tokens: int
    cache_read: int
    cache_write: int
    seconds: float


@dataclass
class SessionResult:
    task: dict
    driver: str
    judge: str
    outcome: str = "max_steps"
    product_title: str = ""
    product_url: str = ""
    reason: str = ""
    steps: list[StepLog] = field(default_factory=list)
    driver_usage: Usage = field(default_factory=Usage)
    judge_usage: Usage = field(default_factory=Usage)
    verdict: Optional[dict] = None
    seconds: float = 0.0
    error: str = ""

    @property
    def cost(self) -> float:
        return self.driver_usage.cost(self.driver) + self.judge_usage.cost(self.judge)


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------


def _observation_blocks(url: str, title: str, shot_b64: str, elements: list[dict], note: str) -> list[dict]:
    lines = [f"{note}", f"URL: {url}", f"Title: {title}", "Clickable elements on screen:"]
    lines += [f"[{e['ref']}] {e['tag']}: {e['text']}" for e in elements]
    return [
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": shot_b64}},
        {"type": "text", "text": "\n".join(lines)},
    ]


def _create(client, model: str, **kwargs):
    """Driver/judge request. Sonnet/Opus 5.5 get server-side refusal fallbacks (default routing)."""
    if model in ("claude-sonnet-5-5", "claude-opus-5-5"):
        try:
            return client.beta.messages.create(
                model=model, betas=["server-side-fallback-2026-07-01"],
                extra_body={"fallbacks": "default"}, **kwargs)
        except Exception as e:  # fallbacks unavailable on this account/SDK: plain request
            if "fallback" not in str(e).lower():
                raise
    return client.beta.messages.create(model=model, **kwargs)


def run_task(task: Task, template: str, driver: str, judge: str, browser: Browser, out_dir: Path,
             client=None, max_steps: int = MAX_STEPS) -> SessionResult:
    client = client or get_client()
    res = SessionResult(task=asdict(task), driver=driver, judge=judge)
    t0 = time.time()
    shots: list[str] = []

    home = f"{urlparse(template).scheme}://{urlparse(template).netloc}/"
    browser.goto(home)
    url, title, shot, elements = browser.observe()
    shots.append(shot)
    messages: list[dict] = [{"role": "user", "content": [
        {"type": "text", "text": f"Your shopping goal: {task.goal}"},
        *_observation_blocks(url, title, shot, elements, "You are on the store's homepage."),
    ]}]

    for step in range(1, max_steps + 1):
        s0 = time.time()
        # Append-only history (thinking blocks are passed back unchanged); the growing prefix
        # is re-read from the prompt cache each step.
        resp = _create(client, driver, max_tokens=4000, system=DRIVER_SYSTEM, tools=TOOLS,
                       tool_choice={"type": "auto", "disable_parallel_tool_use": True},
                       output_config={"effort": "low"}, cache_control={"type": "ephemeral"},
                       messages=messages)
        res.driver_usage.add(resp.usage)
        messages.append({"role": "assistant", "content": resp.content})
        tool = next((b for b in resp.content if getattr(b, "type", "") == "tool_use"), None)
        if tool is None:
            res.outcome, res.reason = "no_action", "driver replied without a tool call"
            break

        name, args = tool.name, dict(tool.input or {})
        result_text = ""
        try:
            if name == "finish":
                res.outcome = args.get("outcome", "gave_up")
                res.product_title = args.get("product_title", "")
                res.product_url = args.get("product_url", "")
                res.reason = args.get("reason", "")
            elif name == "search":
                browser.goto(template.format(quote_plus(args["query"])))
                result_text = f"Searched for '{args['query']}'"
            elif name == "click":
                result_text = browser.click(int(args["ref"]))
            elif name == "scroll":
                result_text = browser.scroll(args.get("direction", "down"))
            elif name == "go_back":
                result_text = browser.back()
            else:
                result_text = f"Unknown tool {name}"
        except Exception as e:
            result_text = f"Action failed: {type(e).__name__}: {str(e)[:120]}"

        u = resp.usage
        res.steps.append(StepLog(step, name, args, result_text or res.outcome, browser.page.url,
                                 int(u.input_tokens or 0), int(u.output_tokens or 0),
                                 int(getattr(u, "cache_read_input_tokens", 0) or 0),
                                 int(getattr(u, "cache_creation_input_tokens", 0) or 0),
                                 round(time.time() - s0, 1)))
        logger.info("[%s] step %d: %s %s -> %s", task.id, step, name, args, result_text or res.outcome)
        if name == "finish":
            break

        try:
            url, title, shot, elements = browser.observe()
        except Exception as e:
            res.outcome, res.error = "error", f"observe failed: {type(e).__name__}: {str(e)[:160]}"
            break
        shots.append(shot)
        messages.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": tool.id,
             "content": _observation_blocks(url, title, shot, elements, result_text)},
        ]})

    res.seconds = round(time.time() - t0, 1)
    out_dir.mkdir(parents=True, exist_ok=True)
    for i, s in enumerate(shots[-3:], 1):
        (out_dir / f"{task.id}_{driver}_last{i}.jpg").write_bytes(base64.b64decode(s))

    res.verdict = _judge_session(task, res, shots[-3:], judge, client)
    return res


def _judge_session(task: Task, res: SessionResult, shots: list[str], judge: str, client) -> dict:
    log = "\n".join(f"{s.step}. {s.action} {json.dumps(s.args, ensure_ascii=False)} -> {s.result} ({s.url})"
                    for s in res.steps)
    content: list[dict] = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": s}}
                           for s in shots]
    content.append({"type": "text", "text": (
        f"Goal: {task.goal}\nOutcome: {res.outcome}\nChosen product: {res.product_title} {res.product_url}\n"
        f"Shopper's reason: {res.reason}\n\nAction log:\n{log}\n\nThe images are the last screens of the session, oldest first.")})
    resp = client.messages.parse(model=judge, max_tokens=4000, system=JUDGE_SYSTEM,
                                 messages=[{"role": "user", "content": content}],
                                 output_config={"effort": "medium"}, output_format=SessionVerdict)
    res.judge_usage.add(resp.usage)
    return resp.parsed_output.model_dump() if resp.parsed_output else {"error": f"stop_reason={resp.stop_reason}"}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    from dotenv import load_dotenv

    load_dotenv(override=True)
    p = argparse.ArgumentParser(description="AI shopper prototype: measure steps and token cost per task.")
    p.add_argument("--site", default=DEFAULT_SITE, help="Search URL template with {} for the query.")
    p.add_argument("--driver", action="append", help="Driver model (repeatable).")
    p.add_argument("--judge", default="claude-sonnet-5-5")
    p.add_argument("--tasks", default=",".join(t.id for t in DEFAULT_TASKS))
    p.add_argument("--max-steps", type=int, default=MAX_STEPS)
    p.add_argument("--headed", action="store_true")
    args = p.parse_args(argv)

    drivers = args.driver or ["claude-haiku-5-5"]
    tasks = [t for t in DEFAULT_TASKS if t.id in args.tasks.split(",")]
    out_dir = Path(__file__).resolve().parents[1] / "reports" / "_shopper_prototype" / datetime.now().strftime("%Y%m%d_%H%M%S")
    results: list[SessionResult] = []
    for driver in drivers:
        for task in tasks:
            browser = Browser(headless=not args.headed)
            try:
                results.append(run_task(task, args.site, driver, args.judge, browser, out_dir, max_steps=args.max_steps))
            except Exception as e:
                r = SessionResult(task=asdict(task), driver=driver, judge=args.judge, error=f"{type(e).__name__}: {e}"[:300])
                results.append(r)
                logger.exception("task %s failed", task.id)
            finally:
                browser.close()

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(json.dumps(
        [{**asdict(r), "cost_usd": round(r.cost, 4)} for r in results], indent=2, ensure_ascii=False, default=str))

    print(f"\n{'driver':<20}{'task':<7}{'outcome':<10}{'steps':>6}{'in':>8}{'cache_rd':>10}{'cache_wr':>10}{'out':>7}{'secs':>7}{'$':>8}  verdict")
    for r in results:
        d = r.driver_usage
        v = r.verdict or {}
        print(f"{r.driver:<20}{r.task['id']:<7}{(r.outcome if not r.error else 'ERROR'):<10}{len(r.steps):>6}"
              f"{d.input_tokens:>8}{d.cache_read_input_tokens:>10}{d.cache_creation_input_tokens:>10}{d.output_tokens:>7}"
              f"{r.seconds:>7}{r.cost:>8.4f}  {v.get('severity', '-')}{' | ' + r.error if r.error else ''}")
    print(f"\nSaved: {out_dir}")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    raise SystemExit(main())
