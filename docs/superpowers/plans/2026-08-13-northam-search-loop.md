# NORTHAM Search-Loop Video Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a 14-second looping animation of a fictional retailer returning wrong search results, and place it in the Find Sherpas homepage hero.

**Architecture:** A standalone Remotion project at `~/Documents/Directories/northam-video` renders three files (`search-loop.mp4`, `search-loop.webm`, `poster.jpg`) and copies them into the site's `public/video/`. The site gains one presentational component and one hero edit. All animation logic lives in pure functions in `src/timing.ts`; only `SearchLoop.tsx` touches Remotion hooks, which keeps every component testable with plain React rendering.

**Tech Stack:** Remotion 4, React 19, TypeScript, Vitest + @testing-library/react, sharp (image processing), Pexels API (stock photography), Next.js 16 + Tailwind v4 (site side).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-08-13-northam-search-loop-design.md`. Read it before Task 1.
- Composition is exactly 1920×1080, 30fps, 420 frames. Frame ranges in Task 2 are authoritative.
- **No Remotion hooks in any component except `SearchLoop.tsx`.** Every other component receives what it needs as props. This is what makes them testable.
- **NORTHAM must not share visual DNA with Find Sherpas.** No `signal-teal` (`oklch(0.50 0.14 200)`), no Geist. NORTHAM uses DM Serif Display (wordmark) and Karla (UI).
- **No in-frame annotation during the failure beat.** No arrows, no highlighted match tokens, no captions inside the video.
- Size budget: webm ≤ 2MB, mp4 ≤ 3MB. If exceeded, drop to 24fps before dropping resolution.
- Every stock image needs a recorded license in `public/products/CREDITS.md`. An image without one does not ship.
- The exact query string, used everywhere: `black dress for winter wedding`
- Currency in all prices: `€`
- The site repo (`find-sherpas`) is a git repo; the video repo is a new, separate one. Commit to whichever repo the task's files live in.

**Deviation from the spec, deliberate:** the spec places assets at `src/assets/`. Remotion's `staticFile()` resolves against the project's `public/` directory, so assets go to `public/products/` instead. Everything else follows the spec.

**Prerequisite before Task 3:** a free Pexels API key from https://www.pexels.com/api/, exported as `PEXELS_API_KEY`. Tasks 1–2 do not need it.

**Paths:**
- Video repo: `~/Documents/Directories/northam-video` (written below as `$VIDEO`)
- Site repo: `/Users/michalpekarcik/Cursor/FInd Sherpas/find-sherpas` (written below as `$SITE`)

---

### Task 1: Scaffold the video project and render a blank frame

**Files:**
- Create: `$VIDEO/package.json`
- Create: `$VIDEO/tsconfig.json`
- Create: `$VIDEO/remotion.config.ts`
- Create: `$VIDEO/vitest.config.ts`
- Create: `$VIDEO/.gitignore`
- Create: `$VIDEO/src/index.ts`
- Create: `$VIDEO/src/Root.tsx`
- Create: `$VIDEO/src/SearchLoop.tsx`

**Interfaces:**
- Consumes: nothing.
- Produces: a Remotion composition registered under the id `SearchLoop`, 1920×1080, 30fps, 420 frames. Later tasks fill in its contents.

- [ ] **Step 1: Create the directory and initialise git**

```bash
mkdir -p ~/Documents/Directories/northam-video/src
cd ~/Documents/Directories/northam-video
git init
```

- [ ] **Step 2: Write `package.json`**

```json
{
  "name": "northam-video",
  "version": "1.0.0",
  "private": true,
  "description": "Remotion source for the NORTHAM search-failure animation on findsherpas.com",
  "scripts": {
    "preview": "remotion studio",
    "test": "vitest run",
    "render:mp4": "remotion render SearchLoop out/search-loop.mp4 --codec h264 --crf 20",
    "render:webm": "remotion render SearchLoop out/search-loop.webm --codec vp9 --crf 32",
    "render:poster": "remotion still SearchLoop out/poster.jpg --frame 200 --image-format jpeg --jpeg-quality 90",
    "render": "npm run render:mp4 && npm run render:webm && npm run render:poster && npm run check:size",
    "check:size": "tsx scripts/check-size.ts",
    "fetch:assets": "tsx scripts/fetch-assets.ts",
    "contact-sheet": "tsx scripts/contact-sheet.ts",
    "sync": "tsx scripts/sync-to-site.ts"
  },
  "dependencies": {
    "@remotion/cli": "^4.0.0",
    "@remotion/google-fonts": "^4.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "remotion": "^4.0.0"
  },
  "devDependencies": {
    "@testing-library/react": "^16.1.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.3.4",
    "jsdom": "^25.0.1",
    "sharp": "^0.33.5",
    "tsx": "^4.21.0",
    "typescript": "^5.7.0",
    "vitest": "^3.2.4"
  }
}
```

- [ ] **Step 3: Write `tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "noEmit": true
  },
  "include": ["src", "scripts", "remotion.config.ts", "vitest.config.ts"]
}
```

- [ ] **Step 4: Write `remotion.config.ts`**

```ts
import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
Config.setConcurrency(4);
```

- [ ] **Step 5: Write `vitest.config.ts`**

```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    environment: "jsdom",
  },
});
```

- [ ] **Step 6: Write `.gitignore`**

```
node_modules/
out/
.DS_Store
```

Note: `public/products/` is NOT ignored. The stock photos are committed — they are the asset of record.

- [ ] **Step 7: Write the placeholder composition**

`src/SearchLoop.tsx`:

```tsx
import { AbsoluteFill } from "remotion";

export const SearchLoop: React.FC = () => {
  return <AbsoluteFill style={{ backgroundColor: "#ffffff" }} />;
};
```

`src/Root.tsx`:

```tsx
import { Composition } from "remotion";
import { SearchLoop } from "./SearchLoop";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="SearchLoop"
      component={SearchLoop}
      durationInFrames={420}
      fps={30}
      width={1920}
      height={1080}
    />
  );
};
```

`src/index.ts`:

```ts
import { registerRoot } from "remotion";
import { RemotionRoot } from "./Root";

registerRoot(RemotionRoot);
```

- [ ] **Step 8: Install and verify the composition renders**

```bash
cd ~/Documents/Directories/northam-video && npm install && npx remotion still SearchLoop out/smoke.png --frame 0
```

Expected: exits 0, `out/smoke.png` exists and is a 1920×1080 white image. If Remotion cannot find a browser, it downloads one on first run — that is expected and may take a minute.

- [ ] **Step 9: Commit**

```bash
cd ~/Documents/Directories/northam-video
git add -A
git commit -m "Scaffold Remotion project for the NORTHAM search-failure animation"
```

---

### Task 2: Timing module

All animation timing is pure functions here, so the sequence can be tested without rendering a single frame.

**Files:**
- Create: `$VIDEO/src/timing.ts`
- Test: `$VIDEO/src/timing.test.ts`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `FPS: 30`, `DURATION_FRAMES: 420`, `QUERY: string`
  - `type Phase = "typing" | "loading" | "wrong" | "resolve" | "hold"`
  - `phaseAt(frame: number): Phase`
  - `typedTextAt(frame: number): string`
  - `caretVisibleAt(frame: number): boolean`
  - `resolveProgressAt(frame: number): number` — 0 to 1
  - `cardProgressAt(index: number, frame: number, startFrame: number): number` — 0 to 1
  - `loopFadeAt(frame: number): number` — 1 = fully visible, 0 = faded out at the loop seam

- [ ] **Step 1: Write the failing test**

`src/timing.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import {
  QUERY,
  cardProgressAt,
  caretVisibleAt,
  loopFadeAt,
  phaseAt,
  resolveProgressAt,
  typedTextAt,
} from "./timing";

describe("phaseAt", () => {
  it("maps each frame range to its beat", () => {
    expect(phaseAt(0)).toBe("typing");
    expect(phaseAt(89)).toBe("typing");
    expect(phaseAt(90)).toBe("loading");
    expect(phaseAt(119)).toBe("loading");
    expect(phaseAt(120)).toBe("wrong");
    expect(phaseAt(269)).toBe("wrong");
    expect(phaseAt(270)).toBe("resolve");
    expect(phaseAt(389)).toBe("resolve");
    expect(phaseAt(390)).toBe("hold");
    expect(phaseAt(419)).toBe("hold");
  });
});

describe("typedTextAt", () => {
  it("starts empty and ends with the full query", () => {
    expect(typedTextAt(0)).toBe("");
    expect(typedTextAt(75)).toBe(QUERY);
    expect(typedTextAt(89)).toBe(QUERY);
    expect(typedTextAt(300)).toBe(QUERY);
  });

  it("reveals characters monotonically", () => {
    let previous = 0;
    for (let frame = 0; frame <= 75; frame++) {
      const length = typedTextAt(frame).length;
      expect(length).toBeGreaterThanOrEqual(previous);
      previous = length;
    }
  });

  it("always reveals a prefix of the query", () => {
    for (let frame = 0; frame <= 75; frame++) {
      expect(QUERY.startsWith(typedTextAt(frame))).toBe(true);
    }
  });

  it("does not type at a robotic constant rate", () => {
    const gaps = new Set<number>();
    let previousLength = 0;
    for (let frame = 0; frame <= 75; frame++) {
      const length = typedTextAt(frame).length;
      if (length !== previousLength) {
        gaps.add(frame);
        previousLength = length;
      }
    }
    const frames = [...gaps];
    const deltas = frames.slice(1).map((f, i) => f - frames[i]!);
    expect(new Set(deltas).size).toBeGreaterThan(1);
  });
});

describe("caretVisibleAt", () => {
  it("blinks on a fixed cycle", () => {
    expect(caretVisibleAt(0)).toBe(true);
    expect(caretVisibleAt(15)).toBe(false);
    expect(caretVisibleAt(30)).toBe(true);
  });
});

describe("resolveProgressAt", () => {
  it("is 0 before the resolve beat and 1 once the crossfade completes", () => {
    expect(resolveProgressAt(269)).toBe(0);
    expect(resolveProgressAt(270)).toBe(0);
    expect(resolveProgressAt(330)).toBe(1);
    expect(resolveProgressAt(419)).toBe(1);
  });

  it("increases monotonically through the crossfade", () => {
    let previous = -1;
    for (let frame = 270; frame <= 330; frame++) {
      const value = resolveProgressAt(frame);
      expect(value).toBeGreaterThanOrEqual(previous);
      previous = value;
    }
  });
});

describe("cardProgressAt", () => {
  it("is 0 before a card's staggered start", () => {
    expect(cardProgressAt(0, 119, 120)).toBe(0);
    expect(cardProgressAt(3, 125, 120)).toBe(0);
  });

  it("reaches 1 after the ramp", () => {
    expect(cardProgressAt(0, 140, 120)).toBe(1);
    expect(cardProgressAt(5, 200, 120)).toBe(1);
  });

  it("starts later for later cards", () => {
    expect(cardProgressAt(0, 126, 120)).toBeGreaterThan(cardProgressAt(4, 126, 120));
  });
});

describe("loopFadeAt", () => {
  it("is fully visible mid-sequence and fades out at the very end", () => {
    expect(loopFadeAt(200)).toBe(1);
    expect(loopFadeAt(405)).toBe(1);
    expect(loopFadeAt(419)).toBeLessThan(0.2);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd ~/Documents/Directories/northam-video && npx vitest run src/timing.test.ts
```

Expected: FAIL — `Failed to resolve import "./timing"`.

- [ ] **Step 3: Write the implementation**

`src/timing.ts`:

```ts
export const FPS = 30;
export const DURATION_FRAMES = 420;
export const QUERY = "black dress for winter wedding";

const TYPING_END = 75;
const CARET_CYCLE = 30;
const RESOLVE_START = 270;
const RESOLVE_END = 330;
const CARD_STAGGER = 4;
const CARD_RAMP = 12;
const LOOP_FADE_START = 408;

export type Phase = "typing" | "loading" | "wrong" | "resolve" | "hold";

export function phaseAt(frame: number): Phase {
  if (frame < 90) return "typing";
  if (frame < 120) return "loading";
  if (frame < 270) return "wrong";
  if (frame < 390) return "resolve";
  return "hold";
}

/**
 * Frame on which each character appears. Jittered with a seeded generator so
 * the typing has human unevenness while staying identical on every render.
 */
function buildRevealFrames(text: string, endFrame: number): number[] {
  let seed = 20260813;
  const random = () => {
    seed = (seed * 1103515245 + 12345) % 2147483648;
    return seed / 2147483648;
  };

  const weights = [...text].map((character) => {
    // Spaces sit at word boundaries, where real typists pause slightly longer.
    const base = character === " " ? 1.8 : 1;
    return base + random() * 0.9;
  });

  const total = weights.reduce((sum, weight) => sum + weight, 0);
  let elapsed = 0;
  return weights.map((weight) => {
    elapsed += weight;
    return Math.round((elapsed / total) * endFrame);
  });
}

const REVEAL_FRAMES = buildRevealFrames(QUERY, TYPING_END);

export function typedTextAt(frame: number): string {
  let count = 0;
  while (count < REVEAL_FRAMES.length && REVEAL_FRAMES[count]! <= frame) {
    count++;
  }
  return QUERY.slice(0, count);
}

export function caretVisibleAt(frame: number): boolean {
  return frame % CARET_CYCLE < CARET_CYCLE / 2;
}

function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}

function easeInOut(t: number): number {
  return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
}

export function resolveProgressAt(frame: number): number {
  if (frame <= RESOLVE_START) return 0;
  if (frame >= RESOLVE_END) return 1;
  return easeInOut((frame - RESOLVE_START) / (RESOLVE_END - RESOLVE_START));
}

export function cardProgressAt(index: number, frame: number, startFrame: number): number {
  const begin = startFrame + index * CARD_STAGGER;
  return easeInOut(clamp01((frame - begin) / CARD_RAMP));
}

export function loopFadeAt(frame: number): number {
  if (frame < LOOP_FADE_START) return 1;
  return clamp01(1 - (frame - LOOP_FADE_START) / (DURATION_FRAMES - LOOP_FADE_START));
}
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd ~/Documents/Directories/northam-video && npx vitest run src/timing.test.ts
```

Expected: PASS, 11 tests.

If the "does not type at a robotic constant rate" test fails, the jitter collapsed — check that `buildRevealFrames` is not rounding every gap to the same integer.

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/Directories/northam-video
git add src/timing.ts src/timing.test.ts
git commit -m "Add timing module driving the search-loop sequence"
```

---

### Task 3: Product data and stock photography

Two result sets and twelve real photographs. This is the task that decides whether the video looks like a store or a mockup, so it ends with a human visual gate.

**Files:**
- Create: `$VIDEO/src/data/products.ts`
- Test: `$VIDEO/src/data/products.test.ts`
- Create: `$VIDEO/scripts/fetch-assets.ts`
- Create: `$VIDEO/scripts/contact-sheet.ts`
- Create: `$VIDEO/public/products/*.jpg` (generated)
- Create: `$VIDEO/public/products/CREDITS.md` (generated)

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `type Product = { id: string; name: string; price: string; query: string; photoId?: number }`
  - `WRONG_RESULTS: Product[]` — 6 items
  - `CORRECT_RESULTS: Product[]` — 6 items
  - Image files at `public/products/<id>.jpg`, each 800×1000, loaded in components via `staticFile("products/<id>.jpg")`

- [ ] **Step 1: Write the failing test**

`src/data/products.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { CORRECT_RESULTS, WRONG_RESULTS } from "./products";

const ALL = [...WRONG_RESULTS, ...CORRECT_RESULTS];

describe("product data", () => {
  it("has six products in each result set", () => {
    expect(WRONG_RESULTS).toHaveLength(6);
    expect(CORRECT_RESULTS).toHaveLength(6);
  });

  it("gives every product a unique id usable as a filename", () => {
    const ids = ALL.map((product) => product.id);
    expect(new Set(ids).size).toBe(ids.length);
    for (const id of ids) {
      expect(id).toMatch(/^[a-z0-9-]+$/);
    }
  });

  it("prices everything in euros", () => {
    for (const product of ALL) {
      expect(product.price).toMatch(/^€\d+$/);
    }
  });

  it("makes the failure self-evident: no wrong result is an occasion dress", () => {
    for (const product of WRONG_RESULTS) {
      expect(product.name.toLowerCase()).not.toMatch(/\bgown\b|midi dress|occasion/);
    }
    expect(WRONG_RESULTS.some((p) => /vase/i.test(p.name))).toBe(true);
    expect(WRONG_RESULTS.some((p) => /leggings/i.test(p.name))).toBe(true);
    expect(WRONG_RESULTS.filter((p) => /sundress/i.test(p.name))).toHaveLength(2);
  });

  it("makes every correct result a black dress", () => {
    for (const product of CORRECT_RESULTS) {
      expect(product.name.toLowerCase()).toMatch(/dress|gown/);
    }
  });

  it("gives every product a search query for asset fetching", () => {
    for (const product of ALL) {
      expect(product.query.length).toBeGreaterThan(3);
    }
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd ~/Documents/Directories/northam-video && npx vitest run src/data/products.test.ts
```

Expected: FAIL — cannot resolve `./products`.

- [ ] **Step 3: Write the product data**

`src/data/products.ts`:

```ts
export type Product = {
  /** Also the image filename: public/products/<id>.jpg */
  id: string;
  name: string;
  price: string;
  /** Pexels search term used by scripts/fetch-assets.ts */
  query: string;
  /** Set this to pin a specific Pexels photo after reviewing the contact sheet. */
  photoId?: number;
};

/** What NORTHAM's search actually returns for "black dress for winter wedding". */
export const WRONG_RESULTS: Product[] = [
  { id: "marbella-sundress", name: "Marbella Floral Sundress", price: "€69", query: "floral summer sundress on white background" },
  { id: "ravello-sundress", name: "Ravello Printed Sundress", price: "€75", query: "printed summer dress product photo white background" },
  { id: "kestrel-leggings", name: "Kestrel High-Rise Leggings", price: "€45", query: "black leggings product photo white background" },
  { id: "kestrel-seamless", name: "Kestrel Seamless Leggings", price: "€49", query: "grey leggings activewear product photo white background" },
  { id: "otto-vase", name: "Otto Ceramic Bud Vase", price: "€28", query: "ceramic vase product photo white background" },
  { id: "lund-shorts", name: "Lund Linen Shorts", price: "€55", query: "linen shorts product photo white background" },
];

/** What the customer was asking for. */
export const CORRECT_RESULTS: Product[] = [
  { id: "astrid-satin", name: "Astrid Satin Midi Dress", price: "€149", query: "black satin midi dress product photo" },
  { id: "vale-column", name: "Vale Crepe Column Dress", price: "€179", query: "black evening dress product photo white background" },
  { id: "norrland-wrap", name: "Norrland Velvet Wrap Dress", price: "€195", query: "black velvet dress product photo" },
  { id: "sigrid-gown", name: "Sigrid Pleated Gown", price: "€229", query: "black formal gown product photo" },
  { id: "halla-midi", name: "Halla Long-Sleeve Midi Dress", price: "€165", query: "black long sleeve dress product photo" },
  { id: "bergen-shift", name: "Bergen Tailored Shift Dress", price: "€139", query: "black shift dress product photo white background" },
];
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd ~/Documents/Directories/northam-video && npx vitest run src/data/products.test.ts
```

Expected: PASS, 6 tests.

- [ ] **Step 5: Write the asset fetch script**

`scripts/fetch-assets.ts`:

```ts
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import sharp from "sharp";
import { CORRECT_RESULTS, WRONG_RESULTS, type Product } from "../src/data/products";

const OUT_DIR = path.join(process.cwd(), "public", "products");
const API_KEY = process.env.PEXELS_API_KEY;

type PexelsPhoto = {
  id: number;
  url: string;
  photographer: string;
  photographer_url: string;
  src: { original: string; large2x: string };
};

async function pexels(url: string): Promise<unknown> {
  const response = await fetch(url, { headers: { Authorization: API_KEY! } });
  if (!response.ok) {
    throw new Error(`Pexels ${response.status} ${response.statusText} for ${url}`);
  }
  return response.json();
}

async function pickPhoto(product: Product): Promise<PexelsPhoto> {
  if (product.photoId) {
    return (await pexels(`https://api.pexels.com/v1/photos/${product.photoId}`)) as PexelsPhoto;
  }
  const query = encodeURIComponent(product.query);
  const result = (await pexels(
    `https://api.pexels.com/v1/search?query=${query}&orientation=portrait&per_page=1`,
  )) as { photos: PexelsPhoto[] };
  const photo = result.photos[0];
  if (!photo) throw new Error(`No Pexels result for "${product.query}" (${product.id})`);
  return photo;
}

async function main() {
  if (!API_KEY) {
    throw new Error("PEXELS_API_KEY is not set. Get a free key at https://www.pexels.com/api/");
  }

  await mkdir(OUT_DIR, { recursive: true });
  const products = [...WRONG_RESULTS, ...CORRECT_RESULTS];
  const credits: string[] = [
    "# Product photography credits",
    "",
    "All images sourced from Pexels under the Pexels License",
    "(https://www.pexels.com/license/): free to use, modification permitted,",
    "no attribution required. Attribution recorded here anyway.",
    "",
    "| File | Product | Photographer | Source |",
    "| --- | --- | --- | --- |",
  ];

  for (const product of products) {
    const photo = await pickPhoto(product);
    const response = await fetch(photo.src.large2x);
    if (!response.ok) throw new Error(`Download failed for ${product.id}`);
    const buffer = Buffer.from(await response.arrayBuffer());

    // 4:5 portrait, flattened onto white so the grid reads as one catalogue.
    await sharp(buffer)
      .resize(800, 1000, { fit: "cover", position: "attention" })
      .flatten({ background: "#ffffff" })
      .jpeg({ quality: 88 })
      .toFile(path.join(OUT_DIR, `${product.id}.jpg`));

    credits.push(
      `| ${product.id}.jpg | ${product.name} | [${photo.photographer}](${photo.photographer_url}) | [${photo.id}](${photo.url}) |`,
    );
    console.log(`${product.id} <- pexels ${photo.id} (${photo.photographer})`);
  }

  await writeFile(path.join(OUT_DIR, "CREDITS.md"), `${credits.join("\n")}\n`);
  console.log(`\nWrote ${products.length} images and CREDITS.md to ${OUT_DIR}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
```

- [ ] **Step 6: Write the contact-sheet script**

This exists so the images can be judged as a set, in one glance, rather than opened one by one.

`scripts/contact-sheet.ts`:

```ts
import path from "node:path";
import sharp from "sharp";
import { CORRECT_RESULTS, WRONG_RESULTS } from "../src/data/products";

const DIR = path.join(process.cwd(), "public", "products");
const CELL_WIDTH = 320;
const CELL_HEIGHT = 400;

async function main() {
  const rows = [WRONG_RESULTS, CORRECT_RESULTS];
  const composites = [];

  for (const [rowIndex, row] of rows.entries()) {
    for (const [columnIndex, product] of row.entries()) {
      const buffer = await sharp(path.join(DIR, `${product.id}.jpg`))
        .resize(CELL_WIDTH, CELL_HEIGHT, { fit: "cover" })
        .toBuffer();
      composites.push({
        input: buffer,
        left: columnIndex * CELL_WIDTH,
        top: rowIndex * CELL_HEIGHT,
      });
    }
  }

  const output = path.join(process.cwd(), "out", "contact-sheet.jpg");
  await sharp({
    create: {
      width: CELL_WIDTH * 6,
      height: CELL_HEIGHT * 2,
      channels: 3,
      background: "#ffffff",
    },
  })
    .composite(composites)
    .jpeg({ quality: 85 })
    .toFile(output);

  console.log(`Contact sheet: ${output}`);
  console.log("Top row = wrong results, bottom row = correct results.");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
```

- [ ] **Step 7: Fetch the assets**

```bash
cd ~/Documents/Directories/northam-video && mkdir -p out && npm run fetch:assets && npm run contact-sheet
```

Expected: 12 lines of `<id> <- pexels <number>`, then a contact sheet path. If any slot errors with "No Pexels result", broaden that product's `query` in `src/data/products.ts` and re-run.

- [ ] **Step 8: Visual gate — review the contact sheet with the user**

Open `out/contact-sheet.jpg` and show it to the user. **Stop and wait for approval.** This is the checkpoint that the previous implementation failed.

Judge it as a shopper would, not as a developer:
- Do the twelve images look like one catalogue, or twelve unrelated photos? Mismatched backgrounds and lighting are the single biggest tell.
- Is every bottom-row garment unmistakably a black dress?
- Is the vase obviously a vase and the leggings obviously leggings, at thumbnail size?

For any rejected slot: search Pexels manually, put the photo's numeric id into that product's `photoId` field, re-run Step 7. Repeat until the user approves the set.

- [ ] **Step 9: Commit**

```bash
cd ~/Documents/Directories/northam-video
git add src/data scripts/fetch-assets.ts scripts/contact-sheet.ts public/products
git commit -m "Add product data and licensed stock photography for both result sets"
```

---

### Task 4: Product card and grid

**Files:**
- Create: `$VIDEO/src/theme.ts`
- Create: `$VIDEO/src/components/ProductCard.tsx`
- Create: `$VIDEO/src/components/ProductGrid.tsx`
- Test: `$VIDEO/src/components/ProductGrid.test.tsx`

**Interfaces:**
- Consumes: `Product` from `src/data/products.ts`.
- Produces:
  - `NORTHAM` theme object from `src/theme.ts` with keys `ink`, `muted`, `line`, `canvas`, `wash`, `accent`, `serif`, `sans`
  - `ProductCard: React.FC<{ product: Product; progress: number }>`
  - `ProductGrid: React.FC<{ products: Product[]; progress: number[]; opacity?: number }>`

- [ ] **Step 1: Write the theme**

NORTHAM's identity, deliberately unlike Find Sherpas: warm near-black instead of pure ink, a muted clay accent instead of teal, serif wordmark.

`src/theme.ts`:

```ts
export const NORTHAM = {
  canvas: "#ffffff",
  wash: "#f6f4f1",
  ink: "#1c1a17",
  muted: "#7a736b",
  line: "#e4e0da",
  accent: "#8c5a3c",
  serif: "DM Serif Display",
  sans: "Karla",
} as const;
```

- [ ] **Step 2: Write the failing test**

`src/components/ProductGrid.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { WRONG_RESULTS } from "../data/products";
import { ProductGrid } from "./ProductGrid";

// Remotion's staticFile() needs no bundler shim in jsdom — it returns a path string.
const fullProgress = [1, 1, 1, 1, 1, 1];

describe("ProductGrid", () => {
  it("renders a card per product with its name and price", () => {
    render(<ProductGrid products={WRONG_RESULTS} progress={fullProgress} />);
    expect(screen.getByText("Otto Ceramic Bud Vase")).toBeDefined();
    expect(screen.getByText("€28")).toBeDefined();
    expect(screen.getAllByRole("img")).toHaveLength(6);
  });

  it("hides cards whose progress is zero", () => {
    const { container } = render(
      <ProductGrid products={WRONG_RESULTS} progress={[1, 0, 0, 0, 0, 0]} />,
    );
    const cards = container.querySelectorAll("[data-card]");
    expect((cards[0] as HTMLElement).style.opacity).toBe("1");
    expect((cards[1] as HTMLElement).style.opacity).toBe("0");
  });

  it("applies grid-level opacity for crossfading between result sets", () => {
    const { container } = render(
      <ProductGrid products={WRONG_RESULTS} progress={fullProgress} opacity={0.25} />,
    );
    expect((container.firstChild as HTMLElement).style.opacity).toBe("0.25");
  });
});
```

- [ ] **Step 3: Run the test to verify it fails**

```bash
cd ~/Documents/Directories/northam-video && npx vitest run src/components/ProductGrid.test.tsx
```

Expected: FAIL — cannot resolve `./ProductGrid`.

- [ ] **Step 4: Write the components**

`src/components/ProductCard.tsx`:

```tsx
import { staticFile } from "remotion";
import type { Product } from "../data/products";
import { NORTHAM } from "../theme";

export const ProductCard: React.FC<{ product: Product; progress: number }> = ({
  product,
  progress,
}) => {
  return (
    <div
      data-card
      style={{
        opacity: progress,
        transform: `translateY(${(1 - progress) * 18}px)`,
        display: "flex",
        flexDirection: "column",
        gap: 12,
      }}
    >
      <div
        style={{
          aspectRatio: "4 / 5",
          overflow: "hidden",
          backgroundColor: NORTHAM.wash,
          borderRadius: 2,
        }}
      >
        <img
          src={staticFile(`products/${product.id}.jpg`)}
          alt={product.name}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <span
          style={{
            fontFamily: NORTHAM.sans,
            fontSize: 20,
            color: NORTHAM.ink,
            letterSpacing: "0.01em",
          }}
        >
          {product.name}
        </span>
        <span style={{ fontFamily: NORTHAM.sans, fontSize: 20, color: NORTHAM.muted }}>
          {product.price}
        </span>
      </div>
    </div>
  );
};
```

`src/components/ProductGrid.tsx`:

```tsx
import type { Product } from "../data/products";
import { ProductCard } from "./ProductCard";

export const ProductGrid: React.FC<{
  products: Product[];
  progress: number[];
  opacity?: number;
}> = ({ products, progress, opacity = 1 }) => {
  return (
    <div
      style={{
        opacity,
        display: "grid",
        gridTemplateColumns: "repeat(6, 1fr)",
        gap: 28,
      }}
    >
      {products.map((product, index) => (
        <ProductCard key={product.id} product={product} progress={progress[index] ?? 1} />
      ))}
    </div>
  );
};
```

- [ ] **Step 5: Run the test to verify it passes**

```bash
cd ~/Documents/Directories/northam-video && npx vitest run src/components/ProductGrid.test.tsx
```

Expected: PASS, 3 tests.

If `staticFile()` throws in jsdom because no Remotion render context exists, add this mock at the top of the test file rather than changing the component:

```tsx
import { vi } from "vitest";

vi.mock("remotion", () => ({ staticFile: (p: string) => `/${p}` }));
```

- [ ] **Step 6: Commit**

```bash
cd ~/Documents/Directories/northam-video
git add src/theme.ts src/components
git commit -m "Add NORTHAM theme, product card, and results grid"
```

---

### Task 5: Storefront chrome, search bar, and results header

The PLP furniture that makes it read as a real retailer rather than a prototype.

**Files:**
- Create: `$VIDEO/src/components/Storefront.tsx`
- Create: `$VIDEO/src/components/SearchBar.tsx`
- Create: `$VIDEO/src/components/ResultsHeader.tsx`
- Test: `$VIDEO/src/components/SearchBar.test.tsx`
- Test: `$VIDEO/src/components/ResultsHeader.test.tsx`

**Interfaces:**
- Consumes: `NORTHAM` from `src/theme.ts`.
- Produces:
  - `Storefront: React.FC<{ children: React.ReactNode }>`
  - `SearchBar: React.FC<{ text: string; caretVisible: boolean }>`
  - `ResultsHeader: React.FC<{ count: number; visible: boolean }>`

- [ ] **Step 1: Write the failing tests**

`src/components/SearchBar.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SearchBar } from "./SearchBar";

describe("SearchBar", () => {
  it("renders the typed text so far", () => {
    render(<SearchBar text="black dre" caretVisible={true} />);
    expect(screen.getByText("black dre")).toBeDefined();
  });

  it("shows a placeholder only while nothing is typed", () => {
    const { rerender } = render(<SearchBar text="" caretVisible={true} />);
    expect(screen.getByText("Search NORTHAM")).toBeDefined();
    rerender(<SearchBar text="b" caretVisible={true} />);
    expect(screen.queryByText("Search NORTHAM")).toBeNull();
  });

  it("toggles the caret", () => {
    const { container, rerender } = render(<SearchBar text="b" caretVisible={true} />);
    expect((container.querySelector("[data-caret]") as HTMLElement).style.opacity).toBe("1");
    rerender(<SearchBar text="b" caretVisible={false} />);
    expect((container.querySelector("[data-caret]") as HTMLElement).style.opacity).toBe("0");
  });
});
```

`src/components/ResultsHeader.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ResultsHeader } from "./ResultsHeader";

describe("ResultsHeader", () => {
  it("formats the result count with a thousands separator", () => {
    render(<ResultsHeader count={1284} visible={true} />);
    expect(screen.getByText("1,284 results")).toBeDefined();
  });

  it("renders the filter and sort furniture a real PLP has", () => {
    render(<ResultsHeader count={1284} visible={true} />);
    expect(screen.getByText("Sort: Relevance")).toBeDefined();
    expect(screen.getByText("Size")).toBeDefined();
    expect(screen.getByText("Colour")).toBeDefined();
  });

  it("is hidden before a search has run", () => {
    const { container } = render(<ResultsHeader count={1284} visible={false} />);
    expect((container.firstChild as HTMLElement).style.opacity).toBe("0");
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd ~/Documents/Directories/northam-video && npx vitest run src/components/SearchBar.test.tsx src/components/ResultsHeader.test.tsx
```

Expected: FAIL — both modules unresolved.

- [ ] **Step 3: Write the components**

`src/components/SearchBar.tsx`:

```tsx
import { NORTHAM } from "../theme";

export const SearchBar: React.FC<{ text: string; caretVisible: boolean }> = ({
  text,
  caretVisible,
}) => {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 16,
        border: `1px solid ${NORTHAM.line}`,
        borderRadius: 2,
        padding: "20px 24px",
        backgroundColor: NORTHAM.canvas,
        width: 720,
      }}
    >
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={NORTHAM.muted} strokeWidth="1.6">
        <circle cx="11" cy="11" r="7" />
        <line x1="16.5" y1="16.5" x2="21" y2="21" />
      </svg>
      <div style={{ display: "flex", alignItems: "center", fontFamily: NORTHAM.sans, fontSize: 24 }}>
        {text.length === 0 ? (
          <span style={{ color: NORTHAM.muted }}>Search NORTHAM</span>
        ) : (
          <span style={{ color: NORTHAM.ink }}>{text}</span>
        )}
        <span
          data-caret
          style={{
            opacity: caretVisible ? 1 : 0,
            display: "inline-block",
            width: 2,
            height: 26,
            marginLeft: 2,
            backgroundColor: NORTHAM.ink,
          }}
        />
      </div>
    </div>
  );
};
```

`src/components/ResultsHeader.tsx`:

```tsx
import { NORTHAM } from "../theme";

const CHIPS = ["Size", "Colour", "Price", "Fabric"];

export const ResultsHeader: React.FC<{ count: number; visible: boolean }> = ({
  count,
  visible,
}) => {
  return (
    <div
      style={{
        opacity: visible ? 1 : 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        borderBottom: `1px solid ${NORTHAM.line}`,
        paddingBottom: 20,
        fontFamily: NORTHAM.sans,
        fontSize: 19,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        <span style={{ color: NORTHAM.muted, marginRight: 10 }}>
          {count.toLocaleString("en-US")} results
        </span>
        {CHIPS.map((chip) => (
          <span
            key={chip}
            style={{
              border: `1px solid ${NORTHAM.line}`,
              borderRadius: 999,
              padding: "8px 18px",
              color: NORTHAM.ink,
            }}
          >
            {chip}
          </span>
        ))}
      </div>
      <span style={{ color: NORTHAM.ink }}>Sort: Relevance</span>
    </div>
  );
};
```

`src/components/Storefront.tsx`:

```tsx
import { NORTHAM } from "../theme";

const NAV = ["Women", "Men", "Home", "Sale"];

export const Storefront: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        backgroundColor: NORTHAM.canvas,
        display: "flex",
        flexDirection: "column",
      }}
    >
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "36px 72px 28px",
          borderBottom: `1px solid ${NORTHAM.line}`,
        }}
      >
        <span
          style={{
            fontFamily: NORTHAM.serif,
            fontSize: 34,
            letterSpacing: "0.18em",
            color: NORTHAM.ink,
          }}
        >
          NORTHAM
        </span>
        <nav style={{ display: "flex", gap: 42, fontFamily: NORTHAM.sans, fontSize: 20 }}>
          {NAV.map((item) => (
            <span key={item} style={{ color: item === "Sale" ? NORTHAM.accent : NORTHAM.ink }}>
              {item}
            </span>
          ))}
        </nav>
      </header>
      <div style={{ flex: 1, padding: "44px 72px", display: "flex", flexDirection: "column", gap: 36 }}>
        {children}
      </div>
    </div>
  );
};
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd ~/Documents/Directories/northam-video && npx vitest run
```

Expected: PASS, all suites (timing, products, ProductGrid, SearchBar, ResultsHeader).

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/Directories/northam-video
git add src/components
git commit -m "Add storefront chrome, search bar, and PLP results header"
```

---

### Task 6: Assemble the sequence

**Files:**
- Modify: `$VIDEO/src/SearchLoop.tsx` (replaces the Task 1 placeholder entirely)
- Modify: `$VIDEO/src/Root.tsx` (font loading)

**Interfaces:**
- Consumes: everything from Tasks 2–5.
- Produces: the finished composition.

- [ ] **Step 1: Load the fonts in `Root.tsx`**

```tsx
import { Composition } from "remotion";
import { loadFont as loadKarla } from "@remotion/google-fonts/Karla";
import { loadFont as loadSerif } from "@remotion/google-fonts/DMSerifDisplay";
import { SearchLoop } from "./SearchLoop";

loadKarla();
loadSerif();

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="SearchLoop"
      component={SearchLoop}
      durationInFrames={420}
      fps={30}
      width={1920}
      height={1080}
    />
  );
};
```

- [ ] **Step 2: Write the composition**

`src/SearchLoop.tsx`:

```tsx
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { ProductGrid } from "./components/ProductGrid";
import { ResultsHeader } from "./components/ResultsHeader";
import { SearchBar } from "./components/SearchBar";
import { Storefront } from "./components/Storefront";
import { CORRECT_RESULTS, WRONG_RESULTS } from "./data/products";
import { NORTHAM } from "./theme";
import {
  cardProgressAt,
  caretVisibleAt,
  loopFadeAt,
  phaseAt,
  resolveProgressAt,
  typedTextAt,
} from "./timing";

const WRONG_GRID_START = 120;
const CORRECT_GRID_START = 300;

const LoadingGrid: React.FC = () => (
  <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 28 }}>
    {Array.from({ length: 6 }).map((_, index) => (
      <div key={index} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ aspectRatio: "4 / 5", backgroundColor: NORTHAM.wash, borderRadius: 2 }} />
        <div style={{ height: 16, width: "70%", backgroundColor: NORTHAM.wash }} />
        <div style={{ height: 16, width: "30%", backgroundColor: NORTHAM.wash }} />
      </div>
    ))}
  </div>
);

export const SearchLoop: React.FC = () => {
  const frame = useCurrentFrame();
  const phase = phaseAt(frame);
  const resolve = resolveProgressAt(frame);

  const wrongProgress = WRONG_RESULTS.map((_, index) =>
    cardProgressAt(index, frame, WRONG_GRID_START),
  );
  const correctProgress = CORRECT_RESULTS.map((_, index) =>
    cardProgressAt(index, frame, CORRECT_GRID_START),
  );

  return (
    <AbsoluteFill style={{ backgroundColor: NORTHAM.canvas, opacity: loopFadeAt(frame) }}>
      <Storefront>
        <SearchBar text={typedTextAt(frame)} caretVisible={caretVisibleAt(frame)} />
        <ResultsHeader count={1284} visible={phase !== "typing"} />

        {phase === "loading" ? (
          <LoadingGrid />
        ) : phase === "typing" ? null : (
          <div style={{ display: "grid" }}>
            {/* Both grids occupy the same cell so the swap is a crossfade, not a jump. */}
            <div style={{ gridArea: "1 / 1" }}>
              <ProductGrid
                products={WRONG_RESULTS}
                progress={wrongProgress}
                opacity={1 - resolve}
              />
            </div>
            <div style={{ gridArea: "1 / 1" }}>
              <ProductGrid
                products={CORRECT_RESULTS}
                progress={correctProgress}
                opacity={resolve}
              />
            </div>
          </div>
        )}
      </Storefront>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 3: Verify all unit tests still pass**

```bash
cd ~/Documents/Directories/northam-video && npx vitest run
```

Expected: PASS, all suites.

- [ ] **Step 4: Render the six key frames**

```bash
cd ~/Documents/Directories/northam-video && mkdir -p out/frames && for f in 40 100 160 200 300 415; do npx remotion still SearchLoop out/frames/frame-$f.png --frame $f; done && ls -la out/frames
```

Expected: six PNGs.

- [ ] **Step 5: Visual gate — review the frames with the user**

Show all six. **Stop and wait for approval.**

What each frame must show:

| Frame | Must show |
| --- | --- |
| 40 | Mid-typing, partial query, caret, no results |
| 100 | Loading skeletons |
| 160 | Wrong results, some cards still staggering in |
| 200 | All six wrong results — this is the poster frame, it must be the most damning one |
| 300 | Mid-crossfade between the two sets |
| 415 | Corrected grid, fading toward the loop seam |

Check specifically: no teal anywhere, no Geist, nothing that reads as Find Sherpas' own UI. Product names legible. No annotation on the failure.

- [ ] **Step 6: Commit**

```bash
cd ~/Documents/Directories/northam-video
git add src/SearchLoop.tsx src/Root.tsx
git commit -m "Assemble the 14-second search-failure sequence"
```

---

### Task 7: Render, size check, and sync to the site

**Files:**
- Create: `$VIDEO/scripts/check-size.ts`
- Create: `$VIDEO/scripts/sync-to-site.ts`
- Create: `$VIDEO/README.md`
- Create: `$SITE/public/video/{search-loop.webm,search-loop.mp4,poster.jpg}` (generated)

**Interfaces:**
- Consumes: the composition from Task 6.
- Produces: three files in the site's `public/video/`.

- [ ] **Step 1: Write the size check**

`scripts/check-size.ts`:

```ts
import { statSync } from "node:fs";
import path from "node:path";

const BUDGETS: Record<string, number> = {
  "search-loop.webm": 2 * 1024 * 1024,
  "search-loop.mp4": 3 * 1024 * 1024,
  "poster.jpg": 400 * 1024,
};

let failed = false;

for (const [file, budget] of Object.entries(BUDGETS)) {
  const size = statSync(path.join(process.cwd(), "out", file)).size;
  const status = size <= budget ? "ok" : "OVER BUDGET";
  console.log(
    `${file.padEnd(20)} ${(size / 1024 / 1024).toFixed(2)} MB / ${(budget / 1024 / 1024).toFixed(2)} MB  ${status}`,
  );
  if (size > budget) failed = true;
}

if (failed) {
  console.error("\nOver budget. Drop the composition to 24fps before reducing resolution.");
  process.exit(1);
}
```

- [ ] **Step 2: Write the sync script**

`scripts/sync-to-site.ts`:

```ts
import { copyFileSync, mkdirSync } from "node:fs";
import os from "node:os";
import path from "node:path";

const DEFAULT_SITE_PUBLIC = path.join(
  os.homedir(),
  "Cursor",
  "FInd Sherpas",
  "find-sherpas",
  "public",
);

const target = path.join(process.env.SITE_PUBLIC_DIR ?? DEFAULT_SITE_PUBLIC, "video");
mkdirSync(target, { recursive: true });

for (const file of ["search-loop.webm", "search-loop.mp4", "poster.jpg"]) {
  const from = path.join(process.cwd(), "out", file);
  copyFileSync(from, path.join(target, file));
  console.log(`${file} -> ${target}`);
}
```

- [ ] **Step 3: Render everything**

```bash
cd ~/Documents/Directories/northam-video && npm run render
```

Expected: three renders complete, then the size table with every row `ok`. The full render takes several minutes.

Then confirm the spec's no-audio requirement — the composition contains no `<Audio>`, so the output should carry no audio stream at all, not a silent one:

```bash
cd ~/Documents/Directories/northam-video && npx remotion ffprobe out/search-loop.mp4 2>&1 | grep -i "Stream #"
```

Expected: exactly one line, `Video:`. If an `Audio:` stream appears, re-render with `--muted`.

If a row is OVER BUDGET: set `fps` to 24 and `durationInFrames` to 336 in `Root.tsx`, divide every frame constant in `src/timing.ts` by 1.25, update `timing.test.ts` expectations to match, and re-render. Do not reduce resolution first.

- [ ] **Step 4: Sync to the site**

```bash
cd ~/Documents/Directories/northam-video && npm run sync && ls -la "/Users/michalpekarcik/Cursor/FInd Sherpas/find-sherpas/public/video"
```

Expected: three files present.

- [ ] **Step 5: Write the README**

`README.md`:

```markdown
# northam-video

Remotion source for the search-failure animation in the findsherpas.com homepage hero.

NORTHAM is a fictional retailer. The animation shows a customer searching
`black dress for winter wedding`, receiving sundresses, leggings and a ceramic vase,
and then the correct black occasion dresses.

Design spec lives in the site repo:
`find-sherpas/docs/superpowers/specs/2026-08-13-northam-search-loop-design.md`

## Commands

    npm run preview        # Remotion Studio, for iterating on timing
    npm test               # unit tests for timing, data, and components
    npm run fetch:assets   # re-download product photography (needs PEXELS_API_KEY)
    npm run contact-sheet  # review all 12 product images as one sheet
    npm run render         # render mp4 + webm + poster, then check size budgets
    npm run sync           # copy the three outputs into the site's public/video/

`npm run sync` writes to `SITE_PUBLIC_DIR`, defaulting to
`~/Cursor/FInd Sherpas/find-sherpas/public`.

## Structure

Timing lives only in `src/timing.ts` — pure functions, unit tested. Only
`src/SearchLoop.tsx` uses Remotion hooks; every other component takes props,
which is what makes them testable outside a render.

Product photography is committed under `public/products/`, with licensing
recorded in `public/products/CREDITS.md`.
```

- [ ] **Step 6: Commit both repos**

```bash
cd ~/Documents/Directories/northam-video
git add scripts/check-size.ts scripts/sync-to-site.ts README.md
git commit -m "Add render size budget check, site sync script, and README"
```

```bash
cd "/Users/michalpekarcik/Cursor/FInd Sherpas/find-sherpas"
git add public/video
git commit -m "Add rendered NORTHAM search-loop video assets"
```

---

### Task 8: Site component

**Files:**
- Create: `$SITE/components/site/search-loop-video.tsx`

**Interfaces:**
- Consumes: `/video/search-loop.webm`, `/video/search-loop.mp4`, `/video/poster.jpg`; `cn` from `@/lib/utils`.
- Produces: `SearchLoopVideo: React.FC<{ className?: string }>`

**On testing:** the site's Vitest setup runs in a `node` environment and only collects `src/**` and `lib/**`, so there is no DOM test stack here. This component is presentational with no logic worth a unit test — the reduced-motion behaviour is pure CSS. Adding jsdom and Testing Library to the site repo for one static component is not worth the dependency. It is verified in the browser in Task 9 instead. Do not add a test stack.

- [ ] **Step 1: Write the component**

```tsx
import { cn } from "@/lib/utils";

const ARIA_LABEL =
  "Search on a fictional store: the query 'black dress for winter wedding' returns sundresses, " +
  "leggings and a ceramic vase, before resolving to the correct black occasion dresses.";

export function SearchLoopVideo({ className }: { className?: string }) {
  return (
    <figure className={cn("w-full", className)}>
      <div className="relative aspect-video w-full overflow-hidden rounded-xl border border-border/60 bg-muted">
        {/* Reduced motion: CSS-only swap, so there is no flash of video before JS runs. */}
        <img
          src="/video/poster.jpg"
          alt={ARIA_LABEL}
          className="absolute inset-0 hidden h-full w-full object-cover motion-reduce:block"
        />
        <video
          className="h-full w-full object-cover motion-reduce:hidden"
          autoPlay
          muted
          loop
          playsInline
          preload="metadata"
          poster="/video/poster.jpg"
          aria-label={ARIA_LABEL}
        >
          <source src="/video/search-loop.webm" type="video/webm" />
          <source src="/video/search-loop.mp4" type="video/mp4" />
        </video>
      </div>
      <figcaption className="mt-3 text-sm text-muted-foreground">
        A failure pattern we find in real audits, shown on a fictional retailer.
      </figcaption>
    </figure>
  );
}
```

- [ ] **Step 2: Verify it type-checks and lints**

```bash
cd "/Users/michalpekarcik/Cursor/FInd Sherpas/find-sherpas" && npx tsc --noEmit && npx eslint components/site/search-loop-video.tsx
```

Expected: both exit 0.

- [ ] **Step 3: Commit**

```bash
cd "/Users/michalpekarcik/Cursor/FInd Sherpas/find-sherpas"
git add components/site/search-loop-video.tsx
git commit -m "Add search-loop video component"
```

---

### Task 9: Hero integration and browser verification

**Files:**
- Modify: `$SITE/app/(site)/page.tsx` (hero section, roughly lines 28–60)
- Create: `$SITE/.claude/launch.json` (only if absent)

**Interfaces:**
- Consumes: `SearchLoopVideo` from Task 8.
- Produces: the finished homepage hero.

- [ ] **Step 1: Add the import**

At the top of `app/(site)/page.tsx`, alongside the existing `HomeSidebar` import:

```tsx
import { SearchLoopVideo } from "@/components/site/search-loop-video";
```

- [ ] **Step 2: Remove the mono line the video replaces**

Delete exactly this block from the hero:

```tsx
            <p className="mt-6 font-mono text-sm text-foreground/70">
              &ldquo;black running shoes&rdquo;{" "}
              <span className="text-muted-foreground/40">&rarr;</span> bestseller
              ranked #14, weak match ranked #1
            </p>
```

- [ ] **Step 3: Place the video below the CTAs**

The hero copy sits in a `max-w-3xl` wrapper, but the video needs the full 1120px column. Add it as a sibling of that wrapper, still inside `<section id="hero">`, immediately after the closing `</div>` of the `max-w-3xl` block:

```tsx
          <div className="mx-auto mt-14 max-w-[1120px]">
            <SearchLoopVideo />
          </div>
```

- [ ] **Step 4: Create the launch config if it does not exist**

`.claude/launch.json`:

```json
{
  "version": "0.0.1",
  "configurations": [
    {
      "name": "find-sherpas",
      "runtimeExecutable": "npm",
      "runtimeArgs": ["run", "dev"],
      "port": 3000
    }
  ]
}
```

- [ ] **Step 5: Start the preview and verify**

Start the `find-sherpas` dev server via the preview tooling (not Bash), then check, in order:

1. Console is clean — no 404s, no media errors.
2. Network: `/video/search-loop.webm` returns 200 with `content-type: video/webm`.
3. Screenshot at 1280×800: the video sits full-width below the CTAs, is playing, and the product names are legible at that rendered size. **This is the check the spec calls out — legibility on the page, not in Remotion Studio.**
4. Resize to 375×812: the video scales, does not overflow horizontally, and the caption still reads.
5. Emulate `prefers-reduced-motion: reduce` and reload: the poster shows and the video element is hidden.

Fix anything that fails by editing source, then re-check from item 1.

- [ ] **Step 6: Show the user the finished hero**

Screenshot the hero at desktop width and share it. **Stop and wait for approval** before the final commit.

- [ ] **Step 7: Commit**

```bash
cd "/Users/michalpekarcik/Cursor/FInd Sherpas/find-sherpas"
git add "app/(site)/page.tsx" .claude/launch.json
git commit -m "Show the NORTHAM search failure in the homepage hero"
```

---

## Done when

- `npm test` passes in the video repo.
- `npm run render` produces three files, all within budget.
- The homepage hero plays the loop, the poster shows under reduced motion, and nothing overflows on mobile.
- `public/products/CREDITS.md` records a license for all twelve images.
- Both repos are committed.
