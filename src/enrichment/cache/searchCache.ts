import * as fs from "fs";
import * as path from "path";
import * as crypto from "crypto";
import type { RoleSearchCompositeResult } from "../types/search";

const CACHE_DIR = path.resolve(
  __dirname, "..", "..", "..", ".cache", "enrichment", "search",
);

function extractDomain(url: string): string {
  try {
    const parsed = new URL(url.startsWith("http") ? url : `https://${url}`);
    return parsed.hostname.replace(/^www\./, "").toLowerCase();
  } catch {
    return url.toLowerCase();
  }
}

function ensureCacheDir() {
  if (!fs.existsSync(CACHE_DIR)) {
    fs.mkdirSync(CACHE_DIR, { recursive: true });
  }
}

// ---------------------------------------------------------------------------
// Composite result cache (per role, stores final merged)
// ---------------------------------------------------------------------------

function compositeKey(
  sourceFile: string,
  sheetName: string,
  rowIndex: number,
  role: string,
  websiteUrl: string,
  provider: string,
): string {
  const domain = extractDomain(websiteUrl);
  const raw = `v3|${provider}|${sourceFile}|${sheetName}|${rowIndex}|${role}|${domain}`;
  return crypto.createHash("md5").update(raw).digest("hex");
}

export function getCachedRoleSearchResult(
  sourceFile: string,
  sheetName: string,
  rowIndex: number,
  role: string,
  websiteUrl: string,
  provider = "BRAVE",
): RoleSearchCompositeResult | null {
  const key = compositeKey(sourceFile, sheetName, rowIndex, role, websiteUrl, provider);
  const filePath = path.join(CACHE_DIR, `${key}.json`);
  if (!fs.existsSync(filePath)) return null;
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf-8")) as RoleSearchCompositeResult;
  } catch {
    return null;
  }
}

export function setCachedRoleSearchResult(
  sourceFile: string,
  sheetName: string,
  rowIndex: number,
  role: string,
  websiteUrl: string,
  result: RoleSearchCompositeResult,
  provider = "BRAVE",
): void {
  ensureCacheDir();
  const key = compositeKey(sourceFile, sheetName, rowIndex, role, websiteUrl, provider);
  const filePath = path.join(CACHE_DIR, `${key}.json`);
  fs.writeFileSync(filePath, JSON.stringify(result, null, 2), "utf-8");
}

// ---------------------------------------------------------------------------
// Per-engine per-query cache
// ---------------------------------------------------------------------------

function queryKey(
  engine: string,
  query: string,
): string {
  const raw = `q|${engine}|${query}`;
  return crypto.createHash("md5").update(raw).digest("hex");
}

export function getCachedQueryResult(
  engine: string,
  query: string,
): any | null {
  const key = queryKey(engine, query);
  const filePath = path.join(CACHE_DIR, `q_${key}.json`);
  if (!fs.existsSync(filePath)) return null;
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf-8"));
  } catch {
    return null;
  }
}

export function setCachedQueryResult(
  engine: string,
  query: string,
  results: any,
): void {
  ensureCacheDir();
  const key = queryKey(engine, query);
  const filePath = path.join(CACHE_DIR, `q_${key}.json`);
  fs.writeFileSync(filePath, JSON.stringify(results, null, 2), "utf-8");
}
